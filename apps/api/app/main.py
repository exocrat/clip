"""ASGI entry point and process-resource composition for the CLIP API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.contracts.health import CONTRACT_VERSION, HEALTH_ROUTE, HealthResponse
from app.core.config import Settings, load_settings
from app.core.database import PoolFactory, PoolLifecycle, create_async_connection_pool
from app.core.errors import install_error_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging

configure_logging()


def create_app(
    settings: Settings,
    *,
    pool_factory: PoolFactory = create_async_connection_pool,
) -> FastAPI:
    """Compose the health-only API and manage an optional database pool.

    The DSN is passed only to the pool factory and is never logged or exposed.
    Missing database configuration leaves the liveness-only skeleton usable;
    configured pools start lazily and are closed with the ASGI lifespan.
    """

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        pool: PoolLifecycle | None = None
        if settings.database_dsn is not None:
            pool = pool_factory(settings.database_dsn.get_secret_value())
            try:
                await pool.open(wait=False)
            except BaseException:
                await pool.close()
                raise
        application.state.database_pool = pool
        try:
            yield
        finally:
            application.state.database_pool = None
            if pool is not None:
                await pool.close()

    # Keep the initial HTTP surface limited to process health. Database pool
    # availability does not change /health's liveness-only meaning.
    application = FastAPI(
        title="CLIP API",
        version=CONTRACT_VERSION,
        debug=settings.debug,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    install_error_handlers(application)
    application.add_middleware(RequestLoggingMiddleware)

    @application.get(**HEALTH_ROUTE)
    async def health() -> HealthResponse:
        """Report process liveness without inspecting dependencies or state."""
        return HealthResponse(status="ok")

    return application


# Validate before serving requests; invalid settings must fail startup.
settings = load_settings()
app = create_app(settings)
