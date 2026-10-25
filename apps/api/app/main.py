"""ASGI entry point for the minimal CLIP API foundation."""

from collections.abc import AsyncIterator
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
from app.core.auth import require_caller
from app.core.config import load_settings
from app.core.errors import install_error_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging
import app.domains.conversations.public as conversations_public
from app.domains.listings.routes import router as listings_router
from app.domains.listings.integrations import PublicListingsIdentity
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.search_runtime import search_runtime, finish_search_cleanup
from app.domains.listings.s3_storage import S3ListingsImageStorage
from app.domains.search.wanted_routes import router as wanted_router
from app.domains.search.wanted_store import PostgresWantedStore
from app.domains.search.saved_routes import router as saved_router
from app.domains.search.saved_store import PostgresSavedStore

# Validate before serving requests; invalid settings must fail startup.
settings = load_settings()
configure_logging()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Open the configured PostgreSQL pool and close it during app shutdown."""
    application.state.search_runtime = None
    application.state.wanted_store = None
    application.state.saved_store = None
    if settings.database_url is None:
        application.state.listings_store = None
        application.state.listings_identity = None
        application.state.listings_conversations = None
        application.state.listings_image_storage = None
        yield
        return

    pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] = AsyncConnectionPool(
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
            if settings.isolated_listings_test_caller:
                from app.domains.listings.isolated_test import (
                    IsolatedListingsTestIdentity,
                )

                application.state.listings_identity = IsolatedListingsTestIdentity()
            else:
                application.state.listings_identity = PublicListingsIdentity()
            application.state.listings_image_storage = (
                S3ListingsImageStorage(
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
app.add_middleware(RequestLoggingMiddleware)


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

    @app.get("/api/demo-info", include_in_schema=False)
    async def demo_info() -> dict[str, str | bool]:
        """Label the unauthenticated isolated deployment as synthetic demo data."""
        return {"mode": "isolated-listings-demo", "synthetic_data_only": True}

    web_root = Path("/app/web")
    if not (web_root / "index.html").is_file():
        raise RuntimeError("The isolated web app build is missing")
    app.mount("/assets", StaticFiles(directory=web_root / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def web_index() -> FileResponse:
        """Serve the built Listings UI from the same ECS task as its API."""
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
