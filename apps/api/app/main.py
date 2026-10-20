"""ASGI entry point for the minimal CLIP API foundation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.contracts.health import CONTRACT_VERSION, HEALTH_ROUTE, HealthResponse
from app.core.config import load_settings
from app.core.errors import install_error_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.domains.conversations import public as conversations_public
from app.domains.listings.routes import router as listings_router
from app.domains.listings.integrations import PublicListingsIdentity
from app.domains.listings.postgres_store import PostgresListingsStore

# Validate before serving requests; invalid settings must fail startup.
settings = load_settings()
configure_logging()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Open the configured PostgreSQL pool and close it during app shutdown."""
    if settings.database_url is None:
        application.state.listings_store = None
        application.state.listings_identity = None
        application.state.listings_conversations = None
        yield
        return

    pool: AsyncConnectionPool[dict[str, Any]] = AsyncConnectionPool(
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
    except Exception:
        await pool.close()
        raise RuntimeError(
            "Configured Listings database is unavailable; connection details are redacted."
        ) from None

    application.state.listings_store = PostgresListingsStore(pool)
    application.state.listings_identity = PublicListingsIdentity()
    # These are reviewed declaration-only calls today. ListingsService maps
    # their NotImplementedError to a safe 503 until Conversations is wired.
    application.state.listings_conversations = conversations_public
    try:
        yield
    finally:
        await pool.close()


# Health and the implemented Listings lifecycle routes are mounted here.
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
app.include_router(listings_router)


@app.get(**HEALTH_ROUTE)
async def health() -> HealthResponse:
    """Report that this API process responds, without inspecting dependencies.

    This is a liveness signal only: it does not claim database, provider, or
    deployment readiness. It exposes no configuration or private state.
    """
    return HealthResponse(status="ok")
