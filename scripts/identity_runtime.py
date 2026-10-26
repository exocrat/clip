"""Explicit real local/test Identity startup; never the default or cloud entry point.

Running --check or --serve reads approved SSM parameters and validates the Identity
DB role. These are live operations requiring separate operator authorization.
Import/help performs no bootstrap. No migrations, provisioning or initial mail send
occurs. Actual auth requests under --serve can write state and dispatch real mail.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from fastapi import FastAPI
import uvicorn

from app.application import create_app
from app.core.config import ConfigurationError, load_settings
from app.core.logging import configure_logging
from app.domains.identity.http import BrowserPolicy
from app.domains.identity.runtime_configuration import prepare_local_identity


def prepare_application() -> FastAPI:
    """Compose existing real bindings and Listings on the registered loopback origin.

    Require the separate Listings DSN before any secret lookup. Identity retains
    its fixed SSM references and restricted login; no credential is copied between
    domains. Real Identity DB/TLS/key/grant checks and mail snapshot validation run
    here, but the Listings pool opens only during the normal ASGI lifespan.
    The insecure-cookie exception is constrained to loopback browser/peer traffic.
    """
    settings = load_settings()
    if settings.database_url is None or settings.debug:
        raise ConfigurationError("Explicit safe shared local runtime required")
    policy = BrowserPolicy(("http://localhost:5173",), development=True)
    identity = prepare_local_identity(settings, policy)
    return create_app(settings, identity=identity)


def main(argv: list[str] | None = None) -> int:
    """Require an explicit approved-bootstrap opt-in and contain private failures.

    The opt-in is an accidental-start guard, not authorization by itself. --check
    validates real Identity startup without opening a listener or sending mail.
    --serve binds only127.0.0.1:8000 with controlled logs, no reload/workers/remote
    exposure. Stop via Ctrl+C so the app closes its own Listings pool.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--serve", action="store_true")
    parser.add_argument("--approved-bootstrap", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        application = prepare_application()
        if args.check:
            print(
                "Identity startup checks passed; no listener/send; Listings pool not checked"
            )
            return 0
        configure_logging()
        server = uvicorn.Server(
            uvicorn.Config(
                application,
                host="127.0.0.1",
                port=8000,
                access_log=False,
                log_config=None,
                proxy_headers=False,
                workers=1,
            )
        )
        server.run()
        if not server.started:
            raise ConfigurationError("Local runtime did not start")
        return 0
    except Exception, SystemExit:
        # Provider, DSN and startup errors may contain private material. Never
        # include raw text, exception chains, Settings or dependency reprs.
        print(
            "Identity runtime failed; review approved configuration and safe checks",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
