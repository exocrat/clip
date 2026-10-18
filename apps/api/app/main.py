"""ASGI entry point for the minimal CLIP API foundation."""

from fastapi import FastAPI

from app.contracts.health import HEALTH_ROUTE, HealthResponse
from app.core.config import load_settings
from app.core.errors import install_error_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging

# Validate before serving requests; invalid settings must fail startup.
settings = load_settings()
configure_logging()

# Keep the initial HTTP surface limited to process health. Contract/schema
# export remains offline; no marketplace operation is implemented here.
app = FastAPI(
    title="CLIP API",
    debug=settings.debug,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
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
