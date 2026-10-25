"""Default ASGI entry point and compatibility lifecycle for explicit local probes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from app.application import application_lifespan, create_app
from app.core.config import load_settings
from app.core.logging import configure_logging
from app.domains.listings.s3_storage import S3ListingsImageStorage

settings = load_settings()
configure_logging()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Preserve accepted probe/test hooks without duplicating composition logic.

    Explicit local probes historically replace main.settings/pool/storage handles
    before entering main.lifespan. Normal default startup uses the same lifecycle;
    configured create_app instances retain their own independent settings.
    """
    async with application_lifespan(
        application,
        settings,
        pool_factory=AsyncConnectionPool,
        storage_factory=S3ListingsImageStorage,
    ):
        yield


app = create_app(settings)
app.router.lifespan_context = lifespan
