"""Explicit native Search preview: actual PostgreSQL/helper/HTTP, synthetic identity.

Never imported by normal startup. Fixed repository tools and a newly owned private
Unix-socket cluster only; no existing target/reset, downloads, cloud or real auth.
"""

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from fastapi import Depends, FastAPI, Request, Response  # noqa: E402
import httpx2 as httpx  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from psycopg_pool import AsyncConnectionPool  # noqa: E402
import uvicorn  # noqa: E402

from app.contracts.domain_types import CatalogueView  # noqa: E402
from app.core.auth import CallerContext, require_caller  # noqa: E402
from app.core.errors import (
    ERRORS,
    PublicError,
    error_response,
    install_error_handlers,
)  # noqa: E402
from app.domains.listings.browse_routes import router  # noqa: E402
from app.domains.listings.embedding_client import (
    SemanticHelper,
    HelperUnavailable,
)  # noqa: E402
from app.domains.listings.embedding_store import EmbeddingStore  # noqa: E402
from app.domains.listings.embedding_worker import EmbeddingWorker  # noqa: E402
from app.domains.listings.postgres_store import PostgresListingsStore  # noqa: E402
from apps.api.tests.domains.listings.test_embedding_postgres import (
    seed_listing,
)  # noqa: E402
from apps.api.tests.domains.search.browser_preview import (
    require_preview_settings,
)  # noqa: E402
from data.generators.preview import stable_id  # noqa: E402
from scripts.evaluation.semantic.ipc_probe import rss  # noqa: E402
from uuid import UUID  # noqa: E402

SEED = 95100
CALLER = UUID(stable_id(SEED, "user_placeholder", 1))
HEADERS = {"X-Clip-UI-Preview": "search-fixtures"}
SOURCES = (
    (
        "Campus bicycle",
        "A pedal powered bicycle for commuting around campus. Includes working brakes and lights.",
        "bicycles",
    ),
    (
        "Calculus textbook",
        "University mathematics textbook with worked exercises and solutions for calculus students.",
        "books",
    ),
    (
        "Compact refrigerator",
        "Small kitchen appliance for storing milk, vegetables and groceries at a low temperature.",
        "appliances",
    ),
)


class NativeCluster:
    """Provision only a new0700 directory; stop owned PGDATA and retain all files."""

    def __init__(self) -> None:
        self.directory = Path(
            tempfile.mkdtemp(prefix="clip-listings-test-", dir="/tmp")
        )
        self.directory.chmod(0o700)
        self.socket = self.directory / "pgsocket"
        self.socket.mkdir(mode=0o700)
        self.cluster = self.directory / "cluster"
        self.pg = ROOT / ".tools/native-db/pgsql/bin"
        self.dbmate = ROOT / ".tools/native-db/downloads/dbmate-macos-arm64"
        self.environment = {
            "PATH": f"{self.pg}:/usr/bin:/bin",
            "LC_ALL": "C",
            "TZ": "UTC",
        }
        self.started = False

    @property
    def url(self) -> str:
        """No client/ambient connection input; private path is generated here."""
        return f"postgres://clip_ci@localhost:55438/clip_test_ci?host={self.socket}&sslmode=disable"

    def command(
        self, name: str, args: list[str], log: str, *, database: bool = False
    ) -> None:
        """Run a fixed owned tool with clean environment and private failure log."""
        executable = self.dbmate if name == "dbmate" else self.pg / name
        environment = dict(self.environment)
        if database:
            environment["DATABASE_URL"] = self.url
        with (self.directory / log).open("ab") as output:
            subprocess.run(
                [str(executable), *args],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=output,
                check=True,
                timeout=60,
            )

    def start(self) -> None:
        """Migrate an empty synthetic DB; never reuse an existing database/cluster."""
        for executable, expected in (
            (self.pg / "postgres", "postgres (PostgreSQL) 18.6"),
            (self.dbmate, "dbmate version 2.36.0"),
        ):
            assert (
                subprocess.check_output(
                    [str(executable), "--version"],
                    env=self.environment,
                    text=True,
                    timeout=5,
                ).strip()
                == expected
            )
        self.command(
            "initdb",
            [
                "-D",
                str(self.cluster),
                "-U",
                "clip_native_test",
                "--encoding=UTF8",
                "--locale=C",
                "--auth-local=trust",
                "--auth-host=reject",
            ],
            "initdb.log",
        )
        # Mark ownership before start so a partial startup still gets a stop attempt.
        self.started = True
        self.command(
            "pg_ctl",
            [
                "-D",
                str(self.cluster),
                "-l",
                str(self.directory / "postgres.log"),
                "-w",
                "-o",
                f"-k {self.socket} -p 55438 -c listen_addresses='' -c shared_buffers=16MB -c max_connections=10 -c timezone=UTC",
                "start",
            ],
            "start.log",
        )
        self.command(
            "psql",
            [
                "-h",
                str(self.socket),
                "-p",
                "55438",
                "-U",
                "clip_native_test",
                "-d",
                "postgres",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                "CREATE ROLE clip_ci LOGIN",
            ],
            "role.log",
        )
        self.command(
            "createdb",
            [
                "-h",
                str(self.socket),
                "-p",
                "55438",
                "-U",
                "clip_native_test",
                "-O",
                "clip_ci",
                "clip_test_ci",
            ],
            "createdb.log",
        )
        self.command(
            "dbmate",
            [
                "--env-file",
                "/dev/null",
                "--migrations-dir",
                str(ROOT / "database/migrations"),
                "--no-dump-schema",
                "migrate",
                "--strict",
            ],
            "migrate.log",
            database=True,
        )

    def stop(self) -> None:
        """Stop only owned PGDATA; retain the directory even on test/failure exits."""
        if self.started:
            self.command(
                "pg_ctl",
                ["-D", str(self.cluster), "-m", "fast", "-w", "stop"],
                "stop.log",
            )
            self.started = False


class PreviewHelper(SemanticHelper):
    """Bound this controlled short-source session to100 encoded windows total."""

    async def encode_query(self, text: str):
        """Reserve one short query window before awaiting; concurrent calls cannot overspend."""
        reserved = getattr(self, "_reserved_windows", 0)
        if self.windows_started + reserved >= 100:
            raise HelperUnavailable("Preview inference budget exhausted")
        self._reserved_windows = reserved + 1
        try:
            return await super().encode_query(text)
        finally:
            self._reserved_windows -= 1


class PreviewIdentity:
    """Explicit trusted synthetic caller only; never infer an actor from input."""

    async def account_is_eligible(self, user_id: UUID) -> bool:
        return user_id == CALLER


def create_app(pool, helper, expires: datetime) -> FastAPI:
    """Mount the actual browse router/store; only identity is a labelled double."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    install_error_handlers(app)
    app.state.listings_store = PostgresListingsStore(pool, 500000, hybrid_helper=helper)
    app.state.listings_browse_identity = PreviewIdentity()
    app.dependency_overrides[require_caller] = lambda: CallerContext(
        CALLER, "regular", expires
    )
    app.include_router(router)

    @app.middleware("http")
    async def private_transport(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Fixed loopback/header/origin gate; production clients cannot opt in."""
        if (
            request.client is None
            or request.client.host not in {"127.0.0.1", "::1", "testclient"}
            or request.headers.get("x-clip-ui-preview") != "search-fixtures"
            or request.headers.get("origin") not in {None, "http://127.0.0.1:5173"}
        ):
            return error_response(request, ERRORS[403])
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Clip-Preview"] = "search-native-model-synthetic-identity"
        return response

    @app.get("/catalogue", response_model=CatalogueView)
    async def catalogue(
        caller: CallerContext = Depends(require_caller),
    ) -> CatalogueView:
        """Use real owned catalogue SQL after synthetic caller eligibility checks."""
        caller.require_current(datetime.now(UTC))
        if not await app.state.listings_browse_identity.account_is_eligible(
            caller.user_id
        ):
            raise PublicError(ERRORS[403])
        return await app.state.listings_store.read_catalogue()

    return app


async def bootstrap(pool, helper) -> None:
    """Create3 short synthetic listings, publish real vectors, then mark serving."""
    async with pool.connection() as connection:
        target = await (
            await connection.execute(
                "SELECT current_database() AS db, current_user AS role, inet_server_addr() IS NULL AS local"
            )
        ).fetchone()
        assert target == {"db": "clip_test_ci", "role": "clip_ci", "local": True}
        assert (
            await (
                await connection.execute(
                    "SELECT count(*) AS n FROM listings.sale_listings"
                )
            ).fetchone()
        )["n"] == 0
        for index, (title, description, category) in enumerate(SOURCES):
            async with connection.transaction():
                listing = await seed_listing(connection, SEED + index)
                await connection.execute(
                    """UPDATE listings.sale_listings SET title=%s,description=%s,
                    category_id=(SELECT id FROM listings.categories WHERE code=%s),
                    availability='available',available_from=clock_timestamp()-interval '1 day',available_until=NULL
                    WHERE id=%s""",
                    (title, description, category, listing),
                )
        store = EmbeddingStore(connection)
        await store.register(helper.spec)
        await store.set_state(helper.spec, "building")
        assert await store.queue_missing(helper.spec, 3) == 3
        worker = EmbeddingWorker(store, helper)
        for _ in SOURCES:
            assert await worker.run_one() == "published"
        assert await worker.run_one() == "idle"
        await store.set_state(helper.spec, "serving")


async def check_http(app, pool, helper, *, close_helper: bool) -> list[dict[str, Any]]:
    """Exercise real HTTP validation/auth/store/helper; report hits without invented labels."""
    results = []
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
        base_url="http://127.0.0.1",
        headers=HEADERS,
    ) as client:
        for mode in ("keyword", "hybrid"):
            for text in (
                "cycle",
                "bicyle",
                "vehicle",
                "wheeled vehicle",
                "keep food cold",
            ):
                response = await client.get(
                    "/listings",
                    params={"q": text, "search_mode": mode, "sort": "relevance"},
                )
                assert response.status_code == 200, (mode, text, response.status_code)
                titles = [item["title"] for item in response.json()["items"]]
                if text in {"cycle", "bicyle", "vehicle"}:
                    assert "Campus bicycle" in titles, (mode, text, titles)
                if mode == "hybrid" and text == "keep food cold":
                    assert "Compact refrigerator" in titles, (mode, text, titles)
                results.append(
                    {
                        "mode": mode,
                        "query": text,
                        "status": response.status_code,
                        "titles": titles,
                    }
                )
        assert (
            await client.get("/listings", params={"search_mode": "hybrid"})
        ).status_code == 200
        assert (
            await client.get("/listings", params={"sort": "relevance"})
        ).status_code == 422
        assert (
            await client.get("/listings", params={"search_mode": "unknown"})
        ).status_code == 422
        assert (
            await client.get("/listings", headers={"X-Clip-UI-Preview": "wrong"})
        ).status_code == 403
        async with pool.connection() as connection:
            store = EmbeddingStore(connection)
            await store.set_state(helper.spec, "building")
            try:
                assert (
                    await client.get(
                        "/listings", params={"q": "cycle", "search_mode": "hybrid"}
                    )
                ).status_code == 503
                assert (
                    await client.get("/listings", params={"q": "cycle"})
                ).status_code == 200
            finally:
                await store.set_state(helper.spec, "serving")
        if close_helper:
            await helper.close()
            assert (
                await client.get(
                    "/listings", params={"q": "cycle", "search_mode": "hybrid"}
                )
            ).status_code == 503
            assert (
                await client.get("/listings", params={"q": "cycle"})
            ).status_code == 200
    return results


async def complete_cleanup(cleanup: Awaitable[None]) -> None:
    """Shield owned cleanup from late task cancellation; preserve cleanup failures.

    Uvicorn can replay SIGINT as its serve context exits, cancelling the first
    shutdown await. A separate task must finish reaping/pool close/report writing.
    This never suppresses a cleanup exception or a resource-limit assertion.
    """
    task = asyncio.ensure_future(cleanup)
    while True:
        try:
            await asyncio.shield(task)
            return
        except asyncio.CancelledError:
            if task.cancelled():
                raise
            if task.done():
                task.result()
                return


async def run(cluster: NativeCluster, check_only: bool) -> None:
    """Own pool/helper/server/watchdog; stop/reap on failures, Ctrl+C or30min limit."""
    helper = PreviewHelper(
        ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
    )
    pool = AsyncConnectionPool(
        cluster.url,
        kwargs={
            "row_factory": dict_row,
            "autocommit": True,
            "options": "-c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000",
        },
        min_size=1,
        max_size=4,
        timeout=5,
        open=False,
    )
    server = None
    parent = os.getpid()
    started = time.monotonic()
    stopped = asyncio.Event()
    peak = 0
    faults = []
    stop_reason = "completed_or_user_stop"
    owned = set()
    main = asyncio.current_task()

    async def supervise():
        nonlocal peak, stop_reason
        while not stopped.is_set():
            if helper.pid is not None:
                owned.add(helper.pid)
            try:
                rows = await asyncio.to_thread(rss, {parent, *owned})
            except OSError, ValueError, subprocess.SubprocessError:
                rows = {}  # Missing supervision must stop rather than disable limits.
            live = [pid for pid in owned if pid in rows and rows[pid][0] == parent]
            total = rows.get(parent, (0, 0))[1] + sum(rows[pid][1] for pid in live)
            peak = max(peak, total)
            if time.monotonic() - started >= 1800:
                stop_reason = "session_duration_limit"
                if server is not None:
                    server.should_exit = True
                else:
                    assert main is not None
                    main.cancel()
                return
            if (
                parent not in rows
                or total >= 512 * 1024 * 1024
                or len(live) > 1
                or helper.windows_started > 100
            ):
                faults.append("resource_or_duration_limit")
                if server is not None:
                    server.should_exit = True
                else:
                    assert main is not None
                    main.cancel()
                return
            await asyncio.sleep(0.1)

    watchdog = asyncio.create_task(supervise())
    results = []
    try:
        await pool.open()
        await pool.wait(timeout=5)
        await bootstrap(pool, helper)
        app = create_app(pool, helper, datetime.now(UTC) + timedelta(minutes=30))
        results = await check_http(app, pool, helper, close_helper=check_only)
        print(
            json.dumps({"http_checks": results, "evidence": str(cluster.directory)}),
            flush=True,
        )
        if not check_only:
            server = uvicorn.Server(
                uvicorn.Config(
                    app,
                    host="127.0.0.1",
                    port=8000,
                    access_log=False,
                    proxy_headers=False,
                    timeout_graceful_shutdown=25,
                )
            )
            print(
                "REAL SEARCH: native SQL + offline model; synthetic listings/identity/image metadata only. 30min/100windows. Ctrl+C stops owned processes; DB retained.",
                flush=True,
            )
            await server.serve()
    finally:

        async def cleanup() -> None:
            """Finish owned resources/report even if Uvicorn replays SIGINT here."""
            stopped.set()
            watchdog.cancel()
            await asyncio.gather(watchdog, return_exceptions=True)
            await helper.close()
            await pool.close()
            live = rss(owned) if owned else {}
            report = {
                "http_checks": results,
                "peak_api_helper_rss_bytes": peak,
                "helper_starts": helper.starts,
                "windows": helper.windows_started,
                "faults": faults,
                "stop_reason": stop_reason,
                "all_helpers_reaped": not any(pid in live for pid in owned),
                "elapsed_seconds": time.monotonic() - started,
            }
            (cluster.directory / "result.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            assert (
                not faults and report["all_helpers_reaped"]
            ), "Preview resource/cleanup check failed"

        await complete_cleanup(cleanup())


def main() -> None:
    """Only explicit test settings/fixed tools/new local target; never dotenv targets."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--isolated-native-search", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    require_preview_settings(args.isolated_native_search)
    if not args.check_only:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 8000))
    cluster = NativeCluster()
    print(f"Native Search evidence: {cluster.directory}", flush=True)
    try:
        cluster.start()
        asyncio.run(run(cluster, args.check_only))
    finally:
        cluster.stop()


if __name__ == "__main__":
    main()
