"""Explicit loopback synthetic browser harness; never a deployment/app factory.

Own disposable SQL/keys and a fixed synthetic-only in-memory mailbox. No SES,
Microsoft network call, credential input or retained database is used. Both this
script and tests are excluded from the production API image. Ctrl+C/timeout
removes only the temporary container; no background scheduler is enabled.
"""

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
import re
import secrets
import sys
from tempfile import TemporaryDirectory
from threading import Timer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))

import uvicorn
from app.core.errors import ERRORS, PublicError
from app.domains.identity.http import BrowserPolicy, create_identity_app
from app.domains.identity.microsoft import MicrosoftKeys, MicrosoftTokenValidator
from app.domains.identity.sessions import IdentitySessions
from app.domains.identity.temporary_crypto import TemporaryKeys
from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_identity_database,
)

SYNTHETIC_EMAIL = "preview@example.invalid"


class PreviewMailbox:
    """Transient synthetic-only code, never write body/recipient/OTP to a log/file."""

    def __init__(self):
        self.code = None

    def send(self, recipient, subject, body):
        """Accept only the documented reserved example address; no provider calls."""
        if recipient != SYNTHETIC_EMAIL:
            raise PublicError(ERRORS[503])
        match = re.search(r"Use ([0-9]{6}) to", body)
        if match is None:
            raise PublicError(ERRORS[503])
        self.code = match.group(1)


def unavailable_metadata(url):
    """Preview never contacts Microsoft; real token/provider check stays pending."""
    raise PublicError(ERRORS[503])


def preview_app(connect):
    """Compose real cookie/OTP/SQL routes with explicit local-only dependencies."""
    clock = lambda: datetime.now(UTC)
    keys = TemporaryKeys(
        "synthetic-ui-v1", *(secrets.token_bytes(32) for _ in range(3))
    )
    sessions = IdentitySessions(connect, keys, clock)
    mailbox = PreviewMailbox()
    app = create_identity_app(
        sessions,
        BrowserPolicy(
            ("http://localhost:5173", "http://127.0.0.1:5173"), development=True
        ),
        mailbox,
        MicrosoftTokenValidator(MicrosoftKeys(unavailable_metadata)),
        clock,
    )

    @app.get("/__identity_preview__/mail")
    def mail():
        """Test mailbox only; fixed synthetic recipient, no arbitrary identity lookup.

        Existing middleware requires a loopback peer/host and approved Origin.
        No such route exists in the actual application or production image.
        """
        return {"code": mailbox.code}

    return app


def main():
    """Refuse implicit/production use and bind one fixed loopback-only test port."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-preview", action="store_true", required=True)
    parser.add_argument("--seconds", type=int, default=1800)
    args = parser.parse_args()
    if os.environ.get("CLIP_ENVIRONMENT") != "test" or not 60 <= args.seconds <= 3600:
        print(
            "Preview requires explicit test environment and 60–3600 second cap.",
            file=sys.stderr,
        )
        return 1
    try:
        with TemporaryDirectory(prefix="clip-identity-ui-") as directory:
            with disposable_identity_database(Path(directory)) as connect:
                server = uvicorn.Server(
                    uvicorn.Config(
                        preview_app(connect),
                        host="127.0.0.1",
                        port=8001,
                        access_log=False,
                        log_config=None,
                    )
                )
                timer = Timer(
                    args.seconds, lambda: setattr(server, "should_exit", True)
                )
                timer.daemon = True
                timer.start()
                try:
                    print(
                        "Synthetic preview API ready on loopback:8001; no live providers.",
                        flush=True,
                    )
                    server.run()
                finally:
                    timer.cancel()
        return 0
    except Exception:
        print(
            "Preview failed; local configuration/port checks require review. Details withheld.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
