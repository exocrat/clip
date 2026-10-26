"""Reusable ASGI composition for Identity, Listings, Search and Wanted/Saved."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.contracts.health import CONTRACT_VERSION, HEALTH_ROUTE, HealthResponse
from app.contracts.domain_types import CsrfToken
from app.core.auth import require_caller
from app.core.config import ConfigurationError, Settings, load_settings
from app.core.errors import install_error_handlers
from app.core.logging import RequestLoggingMiddleware
import app.domains.conversations.public as conversations_public
from app.domains.listings.routes import router as listings_router
from app.domains.listings.integrations import PublicListingsIdentity
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.search_access import ListingsSearchAccess
from app.domains.listings.search_runtime import search_runtime, finish_search_cleanup
from app.domains.listings.s3_storage import S3ListingsImageStorage
from app.domains.search.wanted_routes import router as wanted_router
from app.domains.search.wanted_store import PostgresWantedStore
from app.domains.search.saved_routes import router as saved_router
from app.domains.search.saved_store import PostgresSavedStore

from app.domains.identity.http import IdentityHttpDependencies, install_identity_http


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

    pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] = pool_factory(
        conninfo=settings.database_url.get_secret_value(),
        kwargs={"row_factory": dict_row},
        min_size=1,
        max_size=10,
        timeout=5,
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
        async with search_runtime(settings) as search:
            application.state.search_runtime = search
            application.state.wanted_store = PostgresWantedStore(pool)
            application.state.saved_store = PostgresSavedStore(pool)
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
                if settings.storage_provider == "s3"
                else None
            )
            # These are reviewed declaration-only calls today. ListingsService maps
            # their NotImplementedError to a safe 503 until Conversations is wired.
            application.state.listings_conversations = conversations_public
            yield
    finally:
        await finish_search_cleanup(pool.close())


def create_app(
    settings: Settings | None = None,
    *,
    identity: IdentityHttpDependencies | None = None,
) -> FastAPI:
    """Compose the API with optional explicit real Identity bindings.

    Keep Listings lifespan/state/routes and health in one app. No caller, key,
    provider or DB is invented from missing configuration. Default and production
    startup stay Identity-unbound; only the explicit real test runtime can enable
    sessions. The isolated demo caller never coexists with Identity issuance. Each
    app closes its own configured Listings pool.
    """
    settings = settings if settings is not None else load_settings()
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
        async with application_lifespan(application, settings):
            yield

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

    install_error_handlers(app)
    if identity is not None:
        install_identity_http(
            app,
            identity,
            path_prefix="/api" if settings.serve_web_app else "",
        )
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

    @app.get(**HEALTH_ROUTE)
    async def health() -> HealthResponse:
        """Report that this API process responds, without inspecting dependencies.

        This is a liveness signal only: it does not claim database, provider, or
        deployment readiness. It exposes no configuration or private state.
        """
        return HealthResponse(status="ok")

    if settings.serve_web_app:
        # Give the same-origin hosted UI its explicit /api path. The local Vite
        # proxy keeps its existing prefix rewrite against the unprefixed API.
        app.include_router(listings_router, prefix="/api")
        app.include_router(wanted_router, prefix="/api")
        app.include_router(saved_router, prefix="/api")

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

    if settings.isolated_listings_test_caller:
        from app.domains.listings.isolated_test import isolated_test_caller

        # The fixed test identity is injected server-side; request claims are ignored.
        app.dependency_overrides[require_caller] = isolated_test_caller

    return app
