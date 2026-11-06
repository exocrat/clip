"""Opt-in NEXT-06 native SQL/photo rehearsal; no Docker/AWS/retained target.

Own a fresh Unix-only PG18.6 cluster, apply actual migrations, materialize actual
bytes and verify a guarded bulk load plus real Listings HTTP/service paths.
Caller/eligibility and local signed-object transport are explicit test fixtures;
actual Identity sessions and S3 remain pending, not simulated. --embeddings adds
the actual installed offline model; the default leaves that integration pending.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))

import psycopg  # noqa: E402
from data.generators import reference, files  # noqa: E402
from data.generators.reference_load import (
    DATABASE,
    ROLE,
    LocalObjects,
    load_local,
    validate_rows,
)  # noqa: E402


class OwnedCluster:
    """Only a newly created private target, fixed tools, fixed DB/role and no TCP."""

    def __init__(self):
        self.root = Path(
            tempfile.mkdtemp(prefix="clip-next06-reference-", dir="/private/tmp")
        )
        self.root.chmod(0o700)
        self.socket = self.root / "pgsocket"
        self.socket.mkdir(mode=0o700)
        self.cluster = self.root / "cluster"
        self.pg = ROOT / ".tools/native-db/pgsql/bin"
        self.dbmate = ROOT / ".tools/native-db/downloads/dbmate-macos-arm64"
        self.env = {"PATH": f"{self.pg}:/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC"}
        self.started = False
        self._reference_created = False

    def run(self, executable, arguments, log, *, env=None):
        """Bound a fixed owned process and retain private output without printing it."""
        with (self.root / log).open("ab") as stream:
            subprocess.run(
                [str(executable), *arguments],
                env=self.env | (env or {}),
                stdout=stream,
                stderr=stream,
                check=True,
                timeout=60,
            )

    def connection(self, database=DATABASE):
        """Build a Unix-only connection from this runner's own path, never ambient URLs."""
        return psycopg.connect(
            host=str(self.socket),
            port=55438,
            dbname=database,
            user=ROLE,
            connect_timeout=3,
            autocommit=True,
        )

    def start(self):
        """Version-gate tools, initialize and migrate the new empty target only."""
        for tool, version in (
            (self.pg / "postgres", "postgres (PostgreSQL) 18.6"),
            (self.dbmate, "dbmate version 2.36.0"),
        ):
            if (
                subprocess.check_output(
                    [str(tool), "--version"], env=self.env, text=True, timeout=5
                ).strip()
                != version
            ):
                raise ValueError("Pinned native tool version mismatch")
        self.run(
            self.pg / "initdb",
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
        self.started = True
        self.run(
            self.pg / "pg_ctl",
            [
                "-D",
                str(self.cluster),
                "-l",
                str(self.root / "postgres.log"),
                "-w",
                "-o",
                f"-k {self.socket} -p 55438 -c listen_addresses='' -c shared_buffers=16MB -c max_connections=10 -c timezone=UTC",
                "start",
            ],
            "start.log",
        )
        self.run(
            self.pg / "psql",
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
                f"CREATE ROLE {ROLE} LOGIN",
            ],
            "role.log",
        )
        self.create_reference()

    def create_reference(self):
        """Create/migrate only the fixed reference DB in this invocation's cluster."""
        self.run(
            self.pg / "createdb",
            [
                "-h",
                str(self.socket),
                "-p",
                "55438",
                "-U",
                "clip_native_test",
                "-O",
                ROLE,
                DATABASE,
            ],
            "createdb.log",
        )
        self._reference_created = True
        url = f"postgres://{ROLE}@localhost:55438/{DATABASE}?host={self.socket}&sslmode=disable"
        self.run(
            self.dbmate,
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
            env={"DATABASE_URL": url},
        )

    def rebuild_reference(self):
        """Explicit Step6 reset of our own newly created DB only; never adopt a target.

        No force/disconnect or if-exists option: unexpected users/missing state
        abort instead of widening the reset. Original local inputs/media survive.
        """
        if not self.started or not self._reference_created:
            raise ValueError(
                "Only this invocation's created reference DB can be rebuilt"
            )
        if self.cluster.parent != self.root or self.socket.parent != self.root:
            raise ValueError("Owned cluster paths differ")
        with self.connection() as connection:
            row = connection.execute(
                "SELECT current_database(), current_user, inet_server_addr()"
            ).fetchone()
            if row != (DATABASE, ROLE, None) or connection.info.host != str(
                self.socket
            ):
                raise ValueError("Owned rebuild target differs")
        self.run(
            self.pg / "dropdb",
            ["-h", str(self.socket), "-p", "55438", "-U", "clip_native_test", DATABASE],
            "rebuild-drop.log",
        )
        self._reference_created = False
        self.create_reference()

    def clone_probe(self):
        """Clone only the newly owned reference DB, keeping smoke writes out of its snapshot."""
        self.run(
            self.pg / "createdb",
            [
                "-h",
                str(self.socket),
                "-p",
                "55438",
                "-U",
                "clip_native_test",
                "-O",
                ROLE,
                "-T",
                DATABASE,
                "clip_test_next06_probe",
            ],
            "probe-clone.log",
        )

    def stop(self):
        """Stop only this invocation's PGDATA; retain data, media and logs for inspection."""
        if self.started:
            self.run(
                self.pg / "pg_ctl",
                ["-D", str(self.cluster), "-m", "fast", "-w", "stop"],
                "stop.log",
            )
            self.started = False


def require_local(opt_in):
    """Reject accidental activation, ambient targets/providers and inadequate local space."""
    if (
        not opt_in
        or os.environ.get("CLIP_ENVIRONMENT") != "test"
        or os.environ.get("CLIP_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or any(k.startswith(("PG", "AWS_")) for k in os.environ)
    ):
        raise ValueError(
            "Explicit local test settings without ambient targets required"
        )
    if shutil.disk_usage("/private/tmp").free < 2 * 1024**3:
        raise ValueError("At least2GiB local free space required")


async def app_probe(cluster, objects, bundle, image_root, *, helper=None):
    """Real handlers/SQL/byte confirmation/delivery; explicit trusted test caller only.

    No listeners or real credential flow. Verify1000owner deliveries, hide closed
    listings from nonowners, deny unauthenticated callers, and use a separate
    cloned DB for normal upload/confirm/create. With a real helper, also check
    representative searches and automatic new-listing vectors via the dispatcher.
    """
    from fastapi import FastAPI
    import httpx2
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool
    from app.core.auth import CallerContext
    from app.core.errors import install_error_handlers
    from app.domains.listings.routes import router
    from app.domains.listings.postgres_store import PostgresListingsStore
    from app.domains.listings.service import StoredImageMetadata, InvalidImageContent
    from app.domains.listings.s3_storage import _sniff_image_type

    pool = AsyncConnectionPool(
        kwargs={
            "host": str(cluster.socket),
            "port": 55438,
            "dbname": "clip_test_next06_probe",
            "user": ROLE,
            "row_factory": dict_row,
            "autocommit": True,
            "options": "-c statement_timeout=5000 -c lock_timeout=1000",
        },
        min_size=1,
        max_size=4,
        open=False,
    )

    class Eligibility:
        """SQL-backed fixture capability signature, not real Identity session acceptance."""

        async def account_is_eligible(self, user_id):
            async with pool.connection() as connection:
                row = await (
                    await connection.execute(
                        "SELECT status='active' AND profile_removed_at IS NULL FROM identity.users WHERE id=%s",
                        (user_id,),
                    )
                ).fetchone()
            return bool(row and row["?column?"])

    class Storage:
        """Typed real-byte local provider with opaque expiring URLs; no external request."""

        def __init__(self):
            self.urls = {}

        def object_key_for(self, upload_id):
            return objects.object_key_for(upload_id)

        async def create_upload_url(self, key, media_type, expires, size_bytes):
            return self.sign(key, "put", expires)

        async def create_download_url(self, key, expires):
            return self.sign(key, "get", expires)

        def sign(self, key, action, expires):
            url = f"https://reference.local.invalid/{uuid4()}"
            self.urls[url] = (key, action, expires)
            return url

        def consume(self, url, action):
            key, kind, expires = self.urls[url]
            if kind != action or expires <= datetime.now(UTC):
                raise ValueError("Invalid local transport ticket")
            return key

        async def inspect_object(self, key):
            try:
                content = objects.read(key)
            except FileNotFoundError:
                return None
            mime = _sniff_image_type(content)
            if mime is None or objects.types.get(key) != mime:
                raise InvalidImageContent
            return StoredImageMetadata(media_type=mime, size_bytes=len(content))

        async def delete_object(self, key):
            raise ValueError("Deletion is not part of this local rehearsal")

    current = [None]
    storage = Storage()
    app = FastAPI()
    install_error_handlers(app)
    app.state.listings_store = PostgresListingsStore(
        pool, 500000, hybrid_helper=helper, hybrid_pool=pool if helper else None
    )
    app.state.listings_browse_identity = Eligibility()
    app.state.listings_identity = Eligibility()
    app.state.listings_image_storage = storage
    app.state.listings_conversations = None

    @app.middleware("http")
    async def fixture_scope(request, call_next):
        """Only the harness sets trusted scope; no header/query can choose an actor."""
        if current[0] is not None:
            request.scope["clip.caller"] = current[0]
        return await call_next(request)

    app.include_router(router)

    def actor(identifier):
        return CallerContext(
            UUID(identifier), "regular", datetime.now(UTC) + timedelta(minutes=15)
        )

    dispatcher = None
    try:
        await pool.open()
        await pool.wait(timeout=5)
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            current[0] = actor(bundle["users"][0]["id"])
            embedding_checks = {}
            if helper is not None:
                from scripts.evaluation.reference_embeddings import search_smoke

                embedding_checks["search_smoke"] = await search_smoke(client, bundle)
            seen = []
            for page in range(1, 9):
                response = await client.get(
                    f"/listings?page={page}&page_size=100&sort=created_desc&search_mode=keyword"
                )
                if response.status_code != 200:
                    raise ValueError(
                        f"Real browse pagination failed status={response.status_code}"
                    )
                seen.extend(row["listing_id"] for row in response.json()["items"])
            expected = sorted(
                (
                    r["id"]
                    for r in bundle["listings"]
                    if r["availability_scenario"] == "available"
                ),
                reverse=True,
            )
            if seen != expected or len(set(seen)) != 800:
                raise ValueError(
                    "Real browse tied pagination differs from frozen input"
                )
            for image in bundle["image_plan"]:
                current[0] = actor(image["owner_id"])
                result = await client.get(f"/images/{image['image_id']}/delivery")
                if result.status_code != 200:
                    raise ValueError(
                        f"Owner image delivery failed status={result.status_code}"
                    )
                key = storage.consume(result.json()["url"], "get")
                import hashlib

                if hashlib.sha256(objects.read(key)).hexdigest() != image["sha256"]:
                    raise ValueError("Delivered bytes differ")
            hidden = next(
                r
                for r in bundle["listings"]
                if r["availability_scenario"] == "unavailable"
            )
            other = next(
                u["id"] for u in bundle["users"] if u["id"] != hidden["owner_id"]
            )
            current[0] = actor(other)
            if (
                await client.get(f"/images/{hidden['image_id']}/delivery")
            ).status_code != 404:
                raise ValueError("Hidden image leaked")
            current[0] = None
            if (
                await client.get(f"/images/{hidden['image_id']}/delivery")
            ).status_code != 401:
                raise ValueError("Anonymous image allowed")
            sample = next(
                r for r in bundle["listings"] if r["category_code"] == "books"
            )
            source = next(
                i for i in bundle["image_plan"] if i["listing_id"] == sample["id"]
            )
            current[0] = actor(sample["owner_id"])
            response = await client.post(
                "/image-uploads",
                json={
                    "media_type": source["media_type"],
                    "size_bytes": source["size_bytes"],
                    "operation_id": str(uuid4()),
                },
            )
            if response.status_code != 201:
                raise ValueError(f"Normal intent failed status={response.status_code}")
            instruction = response.json()
            key = storage.consume(instruction["upload_url"], "put")
            objects.put(
                key,
                (image_root / source["source_relative_path"]).read_bytes(),
                source["media_type"],
            )
            response = await client.post(
                f"/image-uploads/{instruction['upload_id']}/confirm"
            )
            if response.status_code != 200:
                raise ValueError(
                    f"Normal confirmation failed status={response.status_code}"
                )
            body = {
                k: sample[k]
                for k in (
                    "title",
                    "description",
                    "category_code",
                    "condition_code",
                    "negotiable",
                )
            }
            body.update(
                title="Synthetic normal publication smoke",
                asking_price_paise=0,
                image_upload_ids=[instruction["upload_id"]],
                operation_id=str(uuid4()),
            )
            if helper is not None:
                from psycopg.conninfo import make_conninfo
                from app.domains.listings.embedding_dispatch import EmbeddingDispatcher
                from scripts.evaluation.reference_embeddings import connection_options

                options = connection_options(cluster, "clip_test_next06_probe")
                options.pop("row_factory")
                options.pop("autocommit")
                dispatcher = EmbeddingDispatcher(make_conninfo(**options), helper)
                await dispatcher.start()
            response = await client.post("/listings", json=body)
            if response.status_code != 201:
                raise ValueError(f"Normal create failed status={response.status_code}")
            created = response.json()
            if (
                await client.get(f"/listings/{created['listing_id']}")
            ).status_code != 200:
                raise ValueError("Normal detail read failed")
            if helper is not None:
                from scripts.evaluation.reference_embeddings import wait_for_publication

                embedding_checks["normal_publication_coverage"] = (
                    await wait_for_publication(cluster, dispatcher)
                )
                response = await client.get(
                    "/listings",
                    params={
                        "q": "Synthetic normal publication smoke",
                        "search_mode": "hybrid",
                        "sort": "relevance",
                        "page_size": 100,
                    },
                )
                if response.status_code != 200 or created["listing_id"] not in {
                    row["listing_id"] for row in response.json()["items"]
                }:
                    raise ValueError(
                        "Normal published listing absent from real Hybrid results"
                    )
                embedding_checks["normal_new_listing_hybrid"] = "pass"
        return {
            "owner_delivery_hashes_verified": 1000,
            "real_browse_pages_verified": 8,
            "real_browse_unique_ids_verified": 800,
            "hidden_nonowner_status": 404,
            "anonymous_status": 401,
            "normal_upload_confirm_create_detail": "pass in separate cloned DB",
            "normal_new_listing_id": created["listing_id"],
            "real_session_auth": "not verified; trusted test scope fixture",
            "cloud_storage": "not verified; real local bytes through typed fixture",
            "automatic_vectors": embedding_checks
            or "pending Step4 real pipeline check",
        }
    finally:
        try:
            if dispatcher is not None:
                await dispatcher.close()
        finally:
            await pool.close()


async def embedding_rehearsal(cluster, objects, bundle, image_root):
    """Own the actual helper across bulk inference and a separate normal-flow clone."""
    from scripts.evaluation.reference_embeddings import (
        ReferenceHelper,
        prepare_reference,
        connection_options,
        require_coverage,
    )
    from app.domains.listings.embedding_bootstrap import EmbeddingBootstrap

    helper = ReferenceHelper(
        ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
    )
    try:
        await helper.start()
        pipeline = await prepare_reference(cluster, helper)
        cluster.clone_probe()
        probe = await app_probe(cluster, objects, bundle, image_root, helper=helper)
        async with await psycopg.AsyncConnection.connect(
            **connection_options(cluster, DATABASE)
        ) as connection:
            require_coverage(await EmbeddingBootstrap(connection).status(), 1000)
    finally:
        await helper.close()
    if helper.pid is not None or helper.starts != 1:
        raise ValueError("Reference helper lifecycle differs")
    return {
        "pipeline": pipeline,
        "application_probe": probe,
        "helper": {
            "starts": helper.starts,
            "windows_started": helper.windows_started,
            "peak_rss_bytes": helper.helper_peak_rss_bytes,
            "stopped": True,
        },
    }


def main(argv=None):
    """Run the reviewed bounded local rehearsal; no external target argument exists."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--name", required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Run real pinned offline model and normal publication vector checks",
    )
    parser.add_argument(
        "--rebuild-check",
        action="store_true",
        help="Recreate only this run's new reference DB and compare real vectors",
    )
    parser.add_argument(
        "--isolated-local-reference", action="store_true", required=True
    )
    args = parser.parse_args(argv)
    cluster = None
    previous_alarm_handler = None
    phase = "preflight"
    result = {"state": "failed", "cloud": "no AWS calls; local only"}
    try:
        require_local(args.isolated_local_reference)
        if args.rebuild_check and not args.embeddings:
            raise ValueError("Rebuild evidence requires real embeddings")

        def deadline_reached(signum, frame):
            """Interrupt only this rehearsal after ten minutes; finally stops owned PGDATA."""
            raise TimeoutError("Local rehearsal deadline reached")

        previous_alarm_handler = signal.signal(signal.SIGALRM, deadline_reached)
        signal.alarm(600)
        reference.read_reference(args.name, image_root=args.image_root)
        bundle = files._read_json(files._run_path(args.name) / "dataset.json")
        cluster = OwnedCluster()
        print(f"Owned rehearsal target: {cluster.root}", flush=True)
        phase = "cluster-start-and-migrations"
        cluster.start()
        objects = LocalObjects(cluster.root / "media")
        phase = "media-materialization"
        media = objects.materialize(bundle, args.image_root)
        phase = "bulk-load-and-validation"
        with cluster.connection() as connection:
            result = load_local(connection, bundle, objects, args.image_root)
            try:
                load_local(connection, bundle, objects, args.image_root)
            except ValueError as error:
                if "not empty" not in str(error):
                    raise
                result["nonempty_retry"] = "refused without overwriting"
            else:
                raise ValueError("A duplicate bulk load was accepted")
        rebuild_before = None
        if args.rebuild_check:
            from scripts.evaluation.reference_rebuild import build_before_reset

            phase = "initial-vector-build-and-owned-reset"
            rebuild_before = asyncio.run(build_before_reset(cluster))
            cluster.rebuild_reference()
            phase = "rebuild-migrations-and-reload"
            with cluster.connection() as connection:
                reloaded = load_local(connection, bundle, objects, args.image_root)
            if any(
                reloaded[key] != result[key]
                for key in (
                    "input_fingerprint",
                    "mapping_digest",
                    "logical_projection_digest",
                    "users_verified",
                    "listings_verified",
                    "images_verified",
                )
            ):
                raise ValueError("Rebuilt logical records/media differ")
            result["reset_reload"] = {
                "same_owned_target": True,
                "fresh_schema_reloaded": True,
                "logical_records_media_identical": True,
            }
        phase = (
            "embedding-and-application-probe"
            if args.embeddings
            else "application-probe"
        )
        if args.embeddings:
            result["embedding_rehearsal"] = asyncio.run(
                asyncio.wait_for(
                    embedding_rehearsal(cluster, objects, bundle, args.image_root),
                    timeout=480,
                )
            )
            result["new_listing_vectors_verified"] = True
            result["vector_verification_scope"] = (
                "real local model/SQL/dispatcher; trusted caller and local storage fixtures; cloud acceptance pending"
            )
            if rebuild_before is not None:
                from scripts.evaluation.reference_rebuild import vector_snapshot

                after = vector_snapshot(cluster)
                from scripts.evaluation.reference_freeze_snapshot import (
                    vector_index_snapshot,
                )

                with cluster.connection() as snapshot_connection:
                    comparable_snapshot = vector_index_snapshot(snapshot_connection)
                if comparable_snapshot != after:
                    raise ValueError("Read-only cloud/native snapshot encoding differs")
                result["reset_reload"]["readonly_snapshot_reader_identical"] = True
                if after != rebuild_before["snapshot"]:
                    raise ValueError("Rebuilt vector/index fingerprints differ")
                result["reset_reload"].update(
                    before=rebuild_before, after=after, vectors_indexes_identical=True
                )
        else:
            cluster.clone_probe()
            result["application_probe"] = asyncio.run(
                asyncio.wait_for(
                    app_probe(cluster, objects, bundle, args.image_root), timeout=300
                )
            )
        with cluster.connection() as connection:
            result["reference_unchanged_after_probe"] = validate_rows(
                connection, bundle
            )
        result.update(
            state=(
                "local rehearsal passed; cloud/auth/human-label/freeze gates pending"
                if args.embeddings
                else "local rehearsal passed; cloud/auth/vector/freeze gates pending"
            ),
            source_run=args.name,
            media=media,
        )
        print(
            "PASS:5000users/1000listings/1000real local image references; normal isolated HTTP flow verified.",
            flush=True,
        )
        return 0
    except (
        ValueError,
        OSError,
        subprocess.SubprocessError,
        psycopg.Error,
        TimeoutError,
        RuntimeError,
    ) as error:
        result.update(
            state="failed", failure_phase=phase, failure_type=type(error).__name__
        )
        if isinstance(error, ValueError):
            result["controlled_reason"] = str(error)
        if isinstance(error, psycopg.Error):
            result["sqlstate"] = error.sqlstate
            result["constraint"] = error.diag.constraint_name
        print(
            "Local reference rehearsal failed; inspect the owned private logs/receipt. No external target used.",
            flush=True,
        )
        return 1
    finally:
        if previous_alarm_handler is not None:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_alarm_handler)
        if cluster is not None:
            try:
                cluster.stop()
            finally:
                result["cluster_stopped"] = not cluster.started
                (cluster.root / "result.json").write_text(
                    json.dumps(result, indent=2, default=str) + "\n"
                )


if __name__ == "__main__":
    raise SystemExit(main())
