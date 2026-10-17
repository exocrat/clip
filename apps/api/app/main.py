"""ASGI entry point for the minimal CLIP API foundation."""

from fastapi import FastAPI

from app.core.config import load_settings

# Validate before serving requests; invalid settings must fail startup.
settings = load_settings()

# Keep the initial HTTP surface limited to process health. Contract/schema
# publishing is later foundation work, not an implemented marketplace API.
app = FastAPI(
    title="CLIP API",
    debug=settings.debug,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Report that this API process responds, without inspecting dependencies.

    This is a liveness signal only: it does not claim database, provider, or
    deployment readiness. It exposes no configuration or private state.
    """
    return {"status": "ok"}
