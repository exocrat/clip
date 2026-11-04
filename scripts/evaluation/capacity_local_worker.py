"""Private UDS app worker for capacity_local.py; never a deployment entry point.

The parent owns its isolated container/socket/config. Authentication uses actual
session SQL and bounded real pools. Only provider login/mail are inert, outside
measurement. Fixed local transport adaptation does not test public TLS/ALB.
"""

import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, "/app/apps/api")
from fastapi.responses import JSONResponse
from pydantic import SecretStr
import uvicorn
from app.application import create_app
from app.core.config import Settings, IDENTITY_TEST_BROWSER_ORIGINS
from app.domains.identity.http import (
    BrowserPolicy,
    IdentityHttpDependencies,
    IdentityReadDependencies,
)
from app.domains.identity.microsoft import MicrosoftKeys, MicrosoftTokenValidator
from app.domains.identity.runtime_database import (
    IdentityConnectionPool,
    validate_database,
)
from app.domains.identity.sessions import IdentitySessions
from app.domains.identity.temporary_crypto import TemporaryKeys


class NoMail:
    """External account setup is excluded; an accidental send must fail locally."""

    def send(self, *args):
        raise RuntimeError("Local capacity mail is disabled")


def main():
    config = json.loads(Path("/run/clip-capacity/runtime.json").read_text())
    kind, number = sys.argv[1:]
    readonly = kind == "lambda"
    keys = TemporaryKeys(
        "capacity", *(bytes.fromhex(value) for value in config["keys"])
    )
    pool = IdentityConnectionPool(
        SecretStr(config["identity_dsn"]),
        "test",
        max_size=1 if readonly else 4,
        retain_idle=not readonly,
    )
    validate_database(pool, keys)
    sessions = IdentitySessions(pool, keys, lambda: datetime.now(UTC))
    policy = BrowserPolicy(IDENTITY_TEST_BROWSER_ORIGINS)
    settings = Settings(
        environment="test",
        database_url=SecretStr(config["marketplace_dsn"]),
        database_dsn=None if readonly else SecretStr(config["conversations_dsn"]),
        storage_provider="disabled",
        serve_web_app=False,
        debug=False,
        hybrid_search_enabled=True,
        hybrid_worker_enabled=not readonly,
        hybrid_search_interpreter=Path("/opt/semantic/venv/bin/python"),
        hybrid_search_model_dir=Path("/opt/semantic/model"),
        identity_runtime_enabled=True,
        identity_provider="microsoft",
        email_provider="dual",
        identity_browser_origins=policy.origins,
        ses_test_recipients=("capacity-fixture@example.com",),
        notification_worker_enabled=not readonly,
    )
    if readonly:
        inner = create_app(
            settings,
            listings_read_only=True,
            identity_reads=IdentityReadDependencies(
                sessions, policy, close=pool.close, request_scope=pool.invocation
            ),
        )
    else:

        def disabled_provider(url):
            raise RuntimeError("External provider disabled in local capacity worker")

        inner = create_app(
            settings,
            identity=IdentityHttpDependencies(
                sessions,
                policy,
                NoMail(),
                MicrosoftTokenValidator(MicrosoftKeys(disabled_provider)),
                lambda: datetime.now(UTC),
                close=pool.close,
            ),
        )
    original = inner.state
    serial = asyncio.Semaphore(1)
    serial_metrics = {
        "completed": 0,
        "active": 0,
        "service_ms": 0.0,
        "max_service_ms": 0.0,
    }

    async def dispatch(scope, receive, send):
        """UDS-only transport plus content-free instrumentation, outside product code."""
        if scope["type"] == "http":
            scope = dict(scope, scheme="https", client=("127.0.0.1", 10000))
            if scope["path"] == "/__capacity_metrics":
                store = getattr(original, "listings_store", None)
                search = getattr(original, "search_runtime", None)
                value = {
                    "identity_pool": pool._pool.get_stats(),
                    "serial": dict(serial_metrics),
                }
                if store is not None:
                    value["listings_pool"] = store._pool.get_stats()
                    value["hybrid_waiting"] = store._hybrid_waiting
                    value["cached_generations"] = len(
                        store._hybrid_vectors.snapshot(
                            store._hybrid_helper.spec.pipeline_id
                        )
                    )
                if search is not None and search.pool is not None:
                    value["hybrid_pool"] = search.pool.get_stats()
                    value["model_windows"] = search.helper.windows_started
                await JSONResponse(value)(scope, receive, send)
                return
            if readonly:
                async with serial:
                    started = time.monotonic()
                    serial_metrics["active"] += 1
                    try:
                        await inner(scope, receive, send)
                    finally:
                        elapsed = (time.monotonic() - started) * 1000
                        serial_metrics["active"] -= 1
                        serial_metrics["completed"] += 1
                        serial_metrics["service_ms"] += elapsed
                        serial_metrics["max_service_ms"] = max(
                            serial_metrics["max_service_ms"], elapsed
                        )
                return
        await inner(scope, receive, send)

    uvicorn.run(
        dispatch,
        uds=f"/run/clip-capacity/{kind}-{number}.sock",
        log_level="warning",
        access_log=False,
        lifespan="on",
    )


if __name__ == "__main__":
    main()
