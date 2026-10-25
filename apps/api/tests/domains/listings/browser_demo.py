"""Loopback-only Listings browser harness with real PostgreSQL and synthetic inputs.

This test-package entry point is deliberately separate from app.main. It never
uses an ambient database URL, real Identity or object storage. Container data is
retained on shutdown; --resume reopens only the recorded, labelled container.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "apps/api"))
sys.path.insert(0, str(ROOT))

from fastapi import Depends, FastAPI, Request  # noqa: E402
from psycopg import AsyncConnection  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from psycopg_pool import AsyncConnectionPool  # noqa: E402
import uvicorn  # noqa: E402

from app.contracts.domain_types import ConfirmedImage, SessionView  # noqa: E402
from app.core.auth import CallerContext, require_caller  # noqa: E402
from app.core.config import Settings, load_settings  # noqa: E402
from app.core.errors import ERRORS, error_response, install_error_handlers  # noqa: E402
from app.domains.listings.embedding_bootstrap import EmbeddingBootstrap  # noqa: E402
from app.domains.listings.postgres_store import PostgresListingsStore  # noqa: E402
from app.domains.listings.search_access import ListingsSearchAccess  # noqa: E402
from app.domains.listings.routes import router  # noqa: E402
from app.domains.search.saved_routes import router as saved_router  # noqa: E402
from app.domains.search.saved_store import PostgresSavedStore  # noqa: E402
from app.domains.search.wanted_routes import router as wanted_router  # noqa: E402
from app.domains.search.wanted_store import PostgresWantedStore  # noqa: E402
from app.domains.listings.search_runtime import (
    SearchRuntime,
    search_runtime,
)  # noqa: E402

OWNER_ID = UUID("10000000-0000-4000-8000-000000000001")
POSTGRES_IMAGE = "postgres:18.6-bookworm"
DBMATE_IMAGE = "ghcr.io/amacneil/dbmate:2.36.0"
DATABASE = "clip_listings_browser"
DB_USER = "clip_browser"
LABEL = "clip.listings-browser"


class SyntheticIdentity:
    """Approve only this harness's fixed synthetic seller, never arbitrary IDs."""

    async def account_is_eligible(self, user_id: UUID) -> bool:
        return user_id == OWNER_ID

    async def eligible(self, user_id: UUID) -> bool:
        """Use the same fixed synthetic account for Search's eligibility boundary."""
        return await self.account_is_eligible(user_id)


def require_demo_settings(settings: Settings) -> None:
    """Reject production/local/default startup and caller-selected databases."""
    if (
        settings.environment != "test"
        or not settings.development_auth
        or settings.database_url is not None
    ):
        raise RuntimeError(
            "Use explicit test/development-auth settings and no CLIP_DATABASE_URL."
        )


async def prepare_hybrid_demo(search: SearchRuntime) -> None:
    """Prepare existing rows and activate the real pinned pipeline in this DB only."""
    if search.pool is None or search.dispatcher is None:
        raise RuntimeError("The local Hybrid helper or worker is unavailable.")
    async with search.pool.connection() as connection:
        target = await connection.execute(
            "SELECT current_database() AS name, inet_server_addr() IS NULL AS socket"
        )
        if await target.fetchone() != {"name": DATABASE, "socket": True}:
            raise RuntimeError("Hybrid setup refused a non-demo database.")
        bootstrap = EmbeddingBootstrap(connection)
        await bootstrap.prepare()
        while await bootstrap.queue(1000) == 1000:
            pass
        deadline = asyncio.get_running_loop().time() + 300
        while True:
            coverage = await bootstrap.status()
            if coverage.failed:
                raise RuntimeError("Local Hybrid vector generation failed.")
            if coverage.complete:
                await bootstrap.activate()
                return
            if asyncio.get_running_loop().time() >= deadline:
                raise RuntimeError(
                    "Local Hybrid setup did not finish within five minutes."
                )
            await asyncio.sleep(0.25)


def create_demo_app(
    conninfo: str,
    settings: Settings,
    *,
    image_ui_preview: bool = False,
    hybrid_search: bool = False,
) -> FastAPI:
    """Bind the real store only to the launcher-owned database and fake caller.

    The launcher, not HTTP input, chooses this connection. The ordinary API app
    never imports this module or installs its dependency overrides/routes.
    """
    require_demo_settings(settings)
    runtime_settings = settings
    if hybrid_search:
        values = settings.model_dump(mode="python")
        values.update(
            database_url=conninfo,
            hybrid_search_enabled=True,
            hybrid_worker_enabled=True,
            hybrid_search_interpreter=ROOT / ".tools/semantic/venv/bin/python",
            hybrid_search_model_dir=ROOT / ".tools/semantic/model",
        )
        runtime_settings = Settings.model_validate(values)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] = (
            AsyncConnectionPool(conninfo, kwargs={"row_factory": dict_row}, open=False)
        )
        await pool.open()
        try:
            await pool.wait(timeout=10)
            async with pool.connection() as connection:
                result = await connection.execute(
                    "SELECT current_database() AS name, inet_server_addr() IS NULL AS socket"
                )
                if await result.fetchone() != {"name": DATABASE, "socket": True}:
                    raise RuntimeError(
                        "Expected the isolated Unix-socket browser database"
                    )
                await connection.execute(
                    """
                    INSERT INTO identity.users (id, account_class, status, display_name)
                    VALUES (%s, 'regular', 'active', 'Synthetic Listings browser seller')
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (OWNER_ID,),
                )
            application.state.demo_pool = pool
            synthetic_identity = SyntheticIdentity()
            application.state.listings_identity = synthetic_identity
            # Browse has its own Identity boundary; use the same fixed local seller.
            application.state.listings_browse_identity = synthetic_identity
            application.state.listings_conversations = None
            async with search_runtime(runtime_settings) as search:
                if hybrid_search and search.state != "ready":
                    raise RuntimeError("The local Hybrid helper could not start.")
                application.state.search_runtime = search
                application.state.listings_store = PostgresListingsStore(
                    pool,
                    settings.sensitive_purchase_threshold_paise,
                    hybrid_helper=search.helper,
                    hybrid_pool=search.pool,
                )
                # Only Identity is synthetic: every Listings operation and both
                # Search stores read/write this same launcher-owned database.
                application.state.listings_public = ListingsSearchAccess(
                    pool,
                    application.state.listings_store,
                    settings.sensitive_purchase_threshold_paise,
                    synthetic_identity,
                )
                application.state.search_identity = synthetic_identity
                application.state.wanted_store = PostgresWantedStore(pool)
                application.state.saved_store = PostgresSavedStore(pool)
                if hybrid_search:
                    await prepare_hybrid_demo(search)
                yield
        finally:
            await pool.close()

    application = FastAPI(
        lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )
    install_error_handlers(application)
    if image_ui_preview:
        from apps.api.tests.domains.listings.browser_image_preview import (
            install_image_preview,
        )

        # Register the browser's exact SPA paths before the API's dynamic
        # /listings/{listing_id} path so names such as /listings/new reach React.
        install_image_preview(application, settings, ROOT / "apps/web/dist")
        prefix = "/api"
    else:
        prefix = ""
    from apps.api.tests.domains.identity.browser_csrf_fixtures import install_demo_csrf

    install_demo_csrf(application, prefix)
    for feature_router in (router, wanted_router, saved_router):
        application.include_router(feature_router, prefix=prefix)

    @application.middleware("http")
    async def local_requests_only(request: Request, call_next):
        """Deny remote peers/hosts and cross-origin browser writes in this test app."""
        origin = request.headers.get("origin")
        allowed_origins = {"http://127.0.0.1:5173", "http://localhost:5173"}
        if image_ui_preview:
            allowed_origins.add("http://127.0.0.1:5174")
        if (
            request.client is None
            or request.client.host not in {"127.0.0.1", "::1"}
            or request.url.hostname not in {"127.0.0.1", "localhost"}
            or (origin is not None and origin not in allowed_origins)
            or (request.method not in {"GET", "HEAD"} and origin not in allowed_origins)
        ):
            return error_response(request, ERRORS[403])
        return await call_next(request)

    async def synthetic_caller() -> CallerContext:
        """Install trusted fixed test identity without reading a header/body ID."""
        return CallerContext(
            OWNER_ID, "regular", datetime.now(UTC) + timedelta(hours=1)
        )

    application.dependency_overrides[require_caller] = synthetic_caller

    @application.get(prefix + "/me", response_model=SessionView)
    async def synthetic_session() -> SessionView:
        """Expose only the existing session shape for the fixed local test actor."""
        caller = await synthetic_caller()
        return SessionView(
            user_id=caller.user_id,
            account_class="regular",
            valid_until=caller.valid_until,
            display_name="Synthetic Listings/Search browser user",
        )

    @application.post("/__listings_demo/image", response_model=ConfirmedImage)
    async def prepare_image(
        request: Request, caller: CallerContext = Depends(require_caller)
    ) -> ConfirmedImage:
        """Insert synthetic confirmation metadata; no object/photo is uploaded."""
        upload_id = uuid4()
        now = datetime.now(UTC)
        async with request.app.state.demo_pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO listings.image_uploads (
                    id, owner_id, object_key, operation_id, state, created_at, expires_at,
                    confirmed_at, confirmed_media_type, confirmed_size_bytes
                ) VALUES (%s, %s, %s, %s, 'confirmed', %s, %s, %s, 'image/jpeg', 2048)
                """,
                (
                    upload_id,
                    caller.user_id,
                    f"synthetic/browser/{upload_id}",
                    upload_id,
                    now,
                    now + timedelta(hours=24),
                    now,
                ),
            )
        return ConfirmedImage(
            upload_id=upload_id, media_type="image/jpeg", size_bytes=2048
        )

    return application


def run_tool(arguments: list[str], *, extra: dict[str, str] | None = None) -> str:
    """Bound tool execution; do not echo commands, credentials or raw diagnostics."""
    env = {key: os.environ[key] for key in ("HOME", "PATH") if key in os.environ}
    result = subprocess.run(
        arguments,
        cwd=ROOT,
        env=env | (extra or {}),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode:
        raise RuntimeError(
            "The isolated database tool failed; no shared database was targeted."
        )
    return result.stdout.strip()


def owned_container(session: Path, docker: list[str]) -> str:
    """Validate retained session ownership and Docker label before reuse/inspection."""
    resolved = session.resolve()
    if (
        session.is_symlink()
        or resolved.parent != Path("/tmp")
        or not resolved.name.startswith("clip-listings-browser-")
        or resolved.stat().st_uid != os.getuid()
        or resolved.stat().st_mode & 0o077
    ):
        raise RuntimeError(
            "Expected an owner-private Listings browser session under /tmp"
        )
    state_file = resolved / "session.json"
    if state_file.is_symlink():
        raise RuntimeError("Session metadata must not be a symlink")
    container = json.loads(state_file.read_text())["container"]
    if (
        not isinstance(container, str)
        or len(container) != 64
        or any(c not in "0123456789abcdef" for c in container)
    ):
        raise RuntimeError("Invalid recorded container ID")
    label = run_tool(
        docker
        + [
            "inspect",
            "--format",
            '{{index .Config.Labels "clip.listings-browser"}}',
            container,
        ]
    )
    if label != str(resolved):
        raise RuntimeError("The container does not belong to this browser session")
    return container


def main() -> None:
    """Create/resume an isolated retained container, migrate it, and serve loopback."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--isolated-listings-browser", action="store_true", required=True
    )
    parser.add_argument(
        "--image-ui-preview",
        action="store_true",
        help="Serve the built UI and temporary local image storage on loopback 5174",
    )
    parser.add_argument(
        "--hybrid-search",
        action="store_true",
        help="Enable the real local Hybrid helper, worker, and isolated DB bootstrap",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--resume", type=Path)
    action.add_argument("--inspect", type=Path)
    args = parser.parse_args()
    settings = load_settings()
    require_demo_settings(settings)
    port = 5174 if args.image_ui_preview else 8000

    def stop_requested(signum, frame):
        """Turn terminal/termination signals into cleanup, including Uvicorn replay."""
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, stop_requested)
    signal.signal(signal.SIGTERM, stop_requested)
    context = run_tool(["docker", "context", "show"])
    endpoint = json.loads(run_tool(["docker", "context", "inspect", context]))[0][
        "Endpoints"
    ]["docker"]["Host"]
    if not endpoint.startswith("unix://"):
        raise RuntimeError("A local Unix-socket Docker context is required")
    docker = ["docker", "--context", context]
    if args.inspect:
        container = owned_container(args.inspect, docker)
        print(
            run_tool(
                docker
                + [
                    "exec",
                    "--env",
                    "PGOPTIONS=-c default_transaction_read_only=on",
                    container,
                    "psql",
                    "-X",
                    "-U",
                    DB_USER,
                    "-d",
                    DATABASE,
                    "-c",
                    "SELECT id, title, asking_price_paise, availability, proof_available FROM listings.sale_listings ORDER BY created_at, id",
                ]
            )
        )
        return
    with socket.socket() as listener:
        # Match Uvicorn's restart behavior when prior connections are in TIME_WAIT.
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", port))
    session = (
        args.resume.resolve()
        if args.resume
        else Path(tempfile.mkdtemp(prefix="clip-listings-browser-", dir="/tmp"))
    )
    socket_directory = session / "pgsocket"
    container = None
    try:
        if args.resume:
            container = owned_container(args.resume, docker)
            run_tool(docker + ["start", container])
        else:
            socket_directory.mkdir(mode=0o777)
            socket_directory.chmod(0o777)
            container = run_tool(
                docker
                + [
                    "run",
                    "--detach",
                    "--network",
                    "none",
                    "--stop-timeout",
                    "5",
                    "--label",
                    f"{LABEL}={session}",
                    "--mount",
                    f"type=bind,src={socket_directory},dst=/tmp/clip-pg-socket",
                    "--env",
                    "POSTGRES_PASSWORD",
                    "--env",
                    f"POSTGRES_USER={DB_USER}",
                    "--env",
                    f"POSTGRES_DB={DATABASE}",
                    POSTGRES_IMAGE,
                    "postgres",
                    "-c",
                    "timezone=UTC",
                    "-c",
                    "unix_socket_directories=/var/run/postgresql,/tmp/clip-pg-socket",
                ],
                extra={"POSTGRES_PASSWORD": secrets.token_hex(24)},
            )
            (session / "session.json").write_text(json.dumps({"container": container}))
        for attempt in range(60):
            ready = subprocess.run(
                docker
                # Bootstrap uses sockets only and restarts once. TCP readiness
                # identifies the final server rather than that transient phase.
                + [
                    "exec",
                    container,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    DB_USER,
                    "-d",
                    DATABASE,
                ],
                capture_output=True,
                timeout=10,
            )
            if ready.returncode == 0:
                break
            if attempt == 59:
                raise RuntimeError("Isolated PostgreSQL startup timed out")
            time.sleep(1)
        version = run_tool(
            docker
            + [
                "exec",
                container,
                "psql",
                "-XAt",
                "-U",
                DB_USER,
                "-d",
                DATABASE,
                "-c",
                "SHOW server_version_num",
            ]
        )
        if version != "180006":
            raise RuntimeError("Expected PostgreSQL 18.6")
        run_tool(
            docker
            + [
                "run",
                "--rm",
                "--network",
                "none",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--mount",
                f"type=bind,src={socket_directory},dst=/tmp/clip-pg-socket",
                "--mount",
                f"type=bind,src={ROOT}/database/migrations,dst=/db/migrations,readonly",
                "--env",
                "DATABASE_URL",
                DBMATE_IMAGE,
                "--env-file",
                "/dev/null",
                "--migrations-dir",
                "/db/migrations",
                "--no-dump-schema",
                "migrate",
                "--strict",
            ],
            extra={
                "DATABASE_URL": f"postgres://{DB_USER}@/{DATABASE}?host=%2Ftmp%2Fclip-pg-socket&sslmode=disable"
            },
        )
        print(
            f"ISOLATED LISTINGS BROWSER: real PostgreSQL, synthetic Identity; "
            f"{'temporary local image storage' if args.image_ui_preview else 'synthetic image metadata'}. "
            f"Session: {session}",
            flush=True,
        )
        print(
            f"{'UI/API' if args.image_ui_preview else 'API'}: http://127.0.0.1:{port}; "
            "Ctrl+C stops it and its database, retaining rows for --resume.",
            flush=True,
        )
        conninfo = f"postgresql://{DB_USER}@/{DATABASE}?host={socket_directory}&sslmode=disable"
        uvicorn.run(
            create_demo_app(
                conninfo,
                settings,
                image_ui_preview=args.image_ui_preview,
                hybrid_search=args.hybrid_search,
            ),
            host="127.0.0.1",
            port=port,
            access_log=False,
            log_level="warning",
        )
    finally:
        if container is not None:
            # Finish the bounded stop even when a second terminal signal arrives.
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            run_tool(docker + ["stop", "--time", "5", container])
            print(f"Browser database stopped; retained session: {session}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
