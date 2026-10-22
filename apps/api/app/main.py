"""ASGI entry point for the minimal CLIP API foundation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
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
from app.domains.listings.s3_storage import S3ListingsImageStorage

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
    except Exception:
        await pool.close()
        raise RuntimeError(
            "Configured Listings database is unavailable or outside the isolated test target; connection details are redacted."
        ) from None

    application.state.listings_store = PostgresListingsStore(
        pool, settings.sensitive_purchase_threshold_paise
    )
    if settings.isolated_listings_test_caller:
        from app.domains.listings.isolated_test import IsolatedListingsTestIdentity

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
if settings.isolated_listings_test_caller:
    from app.domains.listings.isolated_test import isolated_test_caller

    # The fixed test identity is injected server-side; request claims are ignored.
    app.dependency_overrides[require_caller] = isolated_test_caller


@app.get(**HEALTH_ROUTE)
async def health() -> HealthResponse:
    """Report that this API process responds, without inspecting dependencies.

    This is a liveness signal only: it does not claim database, provider, or
    deployment readiness. It exposes no configuration or private state.
    """
    return HealthResponse(status="ok")
