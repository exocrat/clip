"""Default ASGI entry point and compatibility lifecycle for explicit local probes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from app.application import application_lifespan, create_app
from app.core.config import Settings, load_settings
from app.core.logging import configure_logging
from app.domains.listings.s3_storage import S3ListingsImageStorage
from app.domains.identity.runtime_configuration import prepare_hosted_test_identity
from app.overflow_runtime import create_overflow_dependencies

settings = load_settings()
configure_logging()


def create_configured_app(settings: Settings) -> FastAPI:
    """Keep normal startup unbound; prepare real Identity only by test opt-in.

    The enabled path reads fixed SecureStrings and validates the dedicated
    Identity DB role during ASGI import. Missing or invalid live configuration
    fails closed before the app serves requests. It never performs migrations or
    sends mail during startup.
    """
    overflow = create_overflow_dependencies(settings)
    try:
        identity = (
            prepare_hosted_test_identity(settings)
            if settings.identity_runtime_enabled
            else None
        )
        return create_app(settings, identity=identity, overflow=overflow)
    except BaseException:
        if overflow is not None:
            overflow.invoker.close()
        raise


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Preserve accepted probe/test hooks without duplicating composition logic.

    Explicit local probes historically replace main.settings/pool/storage handles
    before entering main.lifespan. Normal default startup uses the same lifecycle;
    configured create_app instances retain their own independent settings.
    """
    try:
        async with application_lifespan(
            application,
            settings,
            pool_factory=AsyncConnectionPool,
            storage_factory=S3ListingsImageStorage,
        ):
            yield
    finally:
        invoker = getattr(application.state, "overflow_invoker", None)
        if invoker is not None:
            application.state.overflow_counts.emit_summary()
            invoker.close()


app = create_configured_app(settings)
app.router.lifespan_context = lifespan
