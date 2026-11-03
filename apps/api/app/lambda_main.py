"""Fail-closed Lambda ASGI entry point for the approved Listings read paths.

Default startup remains unauthorized. Explicit hosted test opt-in prepares real
session bindings through fixed secret references and a database audit; it never
warms an email sender or installs login routes. Live startup remains separately gated.
"""

from fastapi import FastAPI

from app.application import create_app
from app.core.config import Settings
from app.core.logging import configure_logging
from app.domains.identity.runtime_configuration import (
    load_lambda_settings,
    prepare_hosted_test_identity_reads,
)

settings = load_lambda_settings()
configure_logging()


def create_configured_app(settings: Settings) -> FastAPI:
    """Keep default auth closed; opt-in reads two fixed secrets and audits the DB.

    Reuse real Identity sessions without email warmup or login routes. Enabling
    this startup in a deployment requires its separately approved secrets/DB plan.
    """
    identity_reads = (
        prepare_hosted_test_identity_reads(settings)
        if settings.identity_runtime_enabled
        else None
    )
    return create_app(settings, identity_reads=identity_reads, listings_read_only=True)


app: FastAPI = create_configured_app(settings)
