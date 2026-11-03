"""Reusable ASGI composition for Identity, Listings, Search and Wanted/Saved."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, AsyncNullConnectionPool

from app.contracts.health import CONTRACT_VERSION, HEALTH_ROUTE, HealthResponse
from app.contracts.domain_types import CsrfToken, SessionView
from app.core.auth import require_caller
from app.core.config import ConfigurationError, Settings, load_settings
from app.core.errors import install_error_handlers
from app.core.logging import RequestLoggingMiddleware
import app.domains.conversations.public as conversations_public
import app.domains.conversations.routes as conversations_routes
from app.domains.conversations.notifications.runtime import notification_runtime
from app.core.database import PoolFactory, create_async_connection_pool
from app.domains.listings.routes import (
    read_only_router as listings_read_only_router,
    router as listings_router,
)
from app.domains.listings.integrations import PublicListingsIdentity
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.search_access import ListingsSearchAccess
from app.domains.listings.search_runtime import search_runtime, finish_search_cleanup
from app.domains.listings.s3_storage import S3ListingsImageStorage
from app.domains.search.wanted_routes import router as wanted_router
from app.domains.search.wanted_store import PostgresWantedStore
from app.domains.search.saved_routes import router as saved_router
from app.domains.search.saved_store import PostgresSavedStore

from app.domains.identity.http import (
    IdentityHttpDependencies,
    IdentityReadDependencies,
    install_identity_http,
    install_identity_reads,
)


@asynccontextmanager
async def _marketplace_lifespan(
    application: FastAPI,
    settings: Settings,
    *,
    pool_factory: Callable[
        ..., AsyncConnectionPool[AsyncConnection[dict[str, Any]]]
    ] = AsyncConnectionPool,
    storage_factory: Callable[
        [str, str, str], S3ListingsImageStorage
    ] = S3ListingsImageStorage,
    listings_pool_max_size: int = 6,
    hybrid_pool_max_size: int = 2,
    hybrid_worker_enabled: bool | None = None,
    read_only_listings: bool = False,
) -> AsyncIterator[None]:
    """Open the configured PostgreSQL pool and close it during app shutdown."""
    application.state.search_runtime = None
    application.state.wanted_store = None
    application.state.saved_store = None
    application.state.listings_public = None
    if settings.database_url is None:
        application.state.listings_store = None
        application.state.listings_identity = None
        application.state.listings_conversations = None
        application.state.listings_image_storage = None
        yield
        return

    # Lambda freezes idle execution environments: retaining their DB connections
    # would make reserved concurrency an insufficient bound on total connections.
    # Null pools retain the concurrency/queue bounds and close unused leases.
    selected_pool_factory = (
        AsyncNullConnectionPool
        if read_only_listings and pool_factory is AsyncConnectionPool
        else pool_factory
    )
    pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] = selected_pool_factory(
        conninfo=settings.database_url.get_secret_value(),
        kwargs={"row_factory": dict_row},
        min_size=0 if read_only_listings else 1,
        max_size=listings_pool_max_size,
        timeout=5,
        max_waiting=64,
        open=False,
    )
    try:
        await pool.open()
        await pool.wait(timeout=5)
        if settings.isolated_listings_test_caller:
            from app.domains.listings.isolated_test import (
                require_isolated_test_database,
            )

            await require_isolated_test_database(pool)
    except BaseException as error:
        await finish_search_cleanup(pool.close())
        if not isinstance(error, Exception):
            raise
        raise RuntimeError(
            "Configured Listings database is unavailable or outside the isolated test target; connection details are redacted."
        ) from None

    try:
        async with search_runtime(
            settings,
            pool_max_size=hybrid_pool_max_size,
            enable_worker=hybrid_worker_enabled,
            retain_idle_connections=not read_only_listings,
        ) as search:
            application.state.search_runtime = search
            application.state.wanted_store = (
                None if read_only_listings else PostgresWantedStore(pool)
            )
            application.state.saved_store = (
                None if read_only_listings else PostgresSavedStore(pool)
            )
            application.state.listings_store = PostgresListingsStore(
                pool,
                settings.sensitive_purchase_threshold_paise,
                isolated_listing_limit=settings.isolated_listings_max_count,
                hybrid_helper=search.helper,
                hybrid_pool=search.pool,
            )
            application.state.listings_public = ListingsSearchAccess(
                pool,
                application.state.listings_store,
                settings.sensitive_purchase_threshold_paise,
            )
            if settings.isolated_listings_test_caller:
                from app.domains.listings.isolated_test import (
                    IsolatedListingsTestIdentity,
                )

                application.state.listings_identity = IsolatedListingsTestIdentity()
            else:
                application.state.listings_identity = PublicListingsIdentity()
            application.state.listings_image_storage = (
                storage_factory(
                    settings.image_bucket or "",
                    settings.image_region or "",
                    settings.image_key_prefix or "",
                )
                if settings.storage_provider == "s3" and not read_only_listings
                else None
            )
            # These are reviewed declaration-only calls today. ListingsService maps
            # their NotImplementedError to a safe 503 until Conversations is wired.
            application.state.listings_conversations = (
                None if read_only_listings else conversations_public
            )
            yield
    finally:
        await finish_search_cleanup(pool.close())


@asynccontextmanager
async def application_lifespan(
    application: FastAPI,
    settings: Settings,
    *,
    pool_factory: Callable[
        ..., AsyncConnectionPool[AsyncConnection[dict[str, Any]]]
    ] = AsyncConnectionPool,
    storage_factory: Callable[
        [str, str, str], S3ListingsImageStorage
    ] = S3ListingsImageStorage,
    conversation_pool_factory: PoolFactory = create_async_connection_pool,
    read_only_listings: bool = False,
) -> AsyncIterator[None]:
    """Own both row-format-specific pools and close them on failure or shutdown.

    Listings/Search use dictionary rows; Conversations retains its bounded tuple
    pool. Connections/sessions are never passed across domain boundaries.
    """
    pool = None
    application.state.database_pool = None
    application.state.conversations_public = None
    dsn = settings.database_dsn or settings.database_url
    try:
        if dsn is not None and not read_only_listings:
            pool = conversation_pool_factory(dsn.get_secret_value())
            await pool.open(wait=False)
            application.state.database_pool = pool
        async with _marketplace_lifespan(
            application,
            settings,
            pool_factory=pool_factory,
            storage_factory=storage_factory,
            listings_pool_max_size=1 if read_only_listings else 6,
            hybrid_pool_max_size=1 if read_only_listings else 2,
            hybrid_worker_enabled=False if read_only_listings else None,
            read_only_listings=read_only_listings,
        ):
            if not read_only_listings and isinstance(pool, AsyncConnectionPool):
                services = conversations_routes.create_public_provider(pool)
                application.state.conversations_public = services
                application.state.listings_conversations = services
            if read_only_listings:
                yield
            else:
                async with notification_runtime(
                    settings,
                    pool,
                    getattr(application.state, "identity_dependencies", None),
                ):
                    yield
    finally:
        application.state.database_pool = None
        application.state.conversations_public = None
        if pool is not None:
            await pool.close()


def create_app(
    settings: Settings | None = None,
    *,
    identity: IdentityHttpDependencies | None = None,
    identity_reads: IdentityReadDependencies | None = None,
    pool_factory: PoolFactory = create_async_connection_pool,
    listings_read_only: bool = False,
) -> FastAPI:
    """Compose the API with optional explicit real Identity bindings.

    Keep Listings lifespan/state/routes and health in one app. No caller, key,
    provider or DB is invented from missing configuration. Default and production
    startup stay Identity-unbound; only the explicit real test runtime can enable
    sessions. The isolated demo caller never coexists with Identity issuance. Each
    app closes its own configured Listings pool.
    """
    settings = settings if settings is not None else load_settings()
    if listings_read_only and identity is not None:
        raise ConfigurationError("Lambda requires session-only Identity bindings")
    if identity_reads is not None:
        if (
            not isinstance(identity_reads, IdentityReadDependencies)
            or not listings_read_only
            or identity is not None
            or settings.environment != "test"
            or not settings.identity_runtime_enabled
            or settings.development_auth
            or settings.isolated_listings_test_caller
            or identity_reads.policy.development
            or identity_reads.policy.origins != settings.identity_browser_origins
        ):
            raise ConfigurationError("Explicit safe Lambda Identity bindings required")
    if listings_read_only and settings.isolated_listings_test_caller:
        raise ConfigurationError(
            "The Lambda read-only app cannot use the isolated demo identity"
        )
    if identity is not None:
        if not isinstance(identity, IdentityHttpDependencies):
            raise ConfigurationError("Complete trusted Identity bindings required")
        if settings.database_url is None:
            raise ConfigurationError(
                "Shared Identity/Listings database configuration required"
            )
        if (
            settings.environment == "production"
            or settings.isolated_listings_test_caller
            or (settings.serve_web_app and not settings.identity_runtime_enabled)
            or settings.development_auth
        ):
            raise ConfigurationError(
                "Identity composition requires an explicit local/test app without demo authentication"
            )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Bind this app's immutable configuration to the shared owned lifecycle."""
        try:
            async with application_lifespan(
                application,
                settings,
                conversation_pool_factory=pool_factory,
                read_only_listings=listings_read_only,
            ):
                yield
        finally:
            # Workers finish before closing their shared Identity connection source.
            binding = identity if identity is not None else identity_reads
            if binding is not None and binding.close is not None:
                await asyncio.to_thread(binding.close)

    # Health, Listings lifecycle and wanted-request author/read routes are mounted here.
    # Domain storage/auth integrations remain explicitly configured dependencies.
    app = FastAPI(
        title="CLIP API",
        version=CONTRACT_VERSION,
        debug=settings.debug,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.identity_dependencies = identity
    app.state.identity_read_dependencies = identity_reads

    install_error_handlers(app)
    path_prefix = "/api" if settings.serve_web_app or listings_read_only else ""
    if identity is not None:
        install_identity_http(
            app,
            identity,
            path_prefix=path_prefix,
        )
    if identity_reads is not None:
        install_identity_reads(app, identity_reads)
    app.add_middleware(RequestLoggingMiddleware)

    if settings.isolated_listings_test_caller:
        # Existing public synthetic-only demo: never enabled alongside real
        # Identity bindings or production settings. This is not a real session.
        from fastapi import Response

        @app.get(
            ("/api" if settings.serve_web_app else "") + "/auth/csrf",
            response_model=CsrfToken,
            include_in_schema=False,
        )
        def isolated_csrf(response: Response) -> CsrfToken:
            """Support the shared browser transport only in the guarded demo profile."""
            response.headers["Cache-Control"] = "no-store"
            return CsrfToken(csrf_token="isolated-demo-csrf-" + "0" * 46)

        @app.get(
            ("/api" if settings.serve_web_app else "") + "/me",
            response_model=SessionView,
            include_in_schema=False,
        )
        def isolated_session(response: Response) -> SessionView:
            """Expose only the existing fixed demo actor, never real authentication.

            Required by the shared frontend eligibility gate. The exact isolated
            target/settings guards above still exclude normal/production runtime.
            """
            from app.domains.listings.isolated_test import isolated_test_caller

            response.headers["Cache-Control"] = "no-store"
            caller = isolated_test_caller()
            return SessionView(
                user_id=caller.user_id,
                account_class=caller.account_class,
                valid_until=caller.valid_until,
                display_name=None,
            )

    @app.get(**HEALTH_ROUTE)
    async def health() -> HealthResponse:
        """Report that this API process responds, without inspecting dependencies.

        This is a liveness signal only: it does not claim database, provider, or
        deployment readiness. It exposes no configuration or private state.
        """
        return HealthResponse(status="ok")

    if listings_read_only:
        # EXP-03's Lambda target exposes only the two reviewed read operations.
        # Authentication remains the real injected Identity dependency.
        app.include_router(listings_read_only_router, prefix="/api")
    elif settings.serve_web_app:
        # Give the same-origin hosted UI its explicit /api path. The local Vite
        # proxy keeps its existing prefix rewrite against the unprefixed API.
        app.include_router(listings_router, prefix="/api")
        app.include_router(wanted_router, prefix="/api")
        app.include_router(saved_router, prefix="/api")
        app.include_router(conversations_routes.router, prefix="/api")

        if settings.isolated_listings_test_caller:

            @app.get("/api/demo-info", include_in_schema=False)
            async def demo_info() -> dict[str, str | bool]:
                """Label only the explicitly isolated deployment as synthetic data."""
                return {"mode": "isolated-listings-demo", "synthetic_data_only": True}

        web_root = Path("/app/web")
        if not (web_root / "index.html").is_file():
            raise RuntimeError("The web app build is missing")
        app.mount("/assets", StaticFiles(directory=web_root / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        async def web_index() -> FileResponse:
            """Serve the built UI from the same process as its authenticated API."""
            return FileResponse(web_root / "index.html")

        @app.get("/{web_path:path}", include_in_schema=False)
        async def web_route(web_path: str) -> FileResponse:
            """Support browser refreshes on client routes without masking API misses."""
            if web_path == "api" or web_path.startswith("api/"):
                from fastapi import HTTPException

                raise HTTPException(status_code=404)
            return FileResponse(web_root / "index.html")

    else:
        app.include_router(listings_router)
        app.include_router(wanted_router)
        app.include_router(saved_router)
        app.include_router(conversations_routes.router)

    if settings.isolated_listings_test_caller:
        from app.domains.listings.isolated_test import isolated_test_caller

        # The fixed test identity is injected server-side; request claims are ignored.
        app.dependency_overrides[require_caller] = isolated_test_caller

    return app
