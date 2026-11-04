"""Run required-rate diagnostic profiles on isolated, resource-limited local apps.

Explicit --synthetic-local only. Own PostgreSQL, six UDS-only application
containers and a loopback proxy. Use the accepted archive's data, real model and
real session SQL. No cloud target/provider, real credentials or production opt-in.
Raw k6 output remains unchanged. This is capacity evidence, never live NFR proof.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
import time
import traceback
from urllib.parse import urlencode
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

import httpx2 as httpx
import numpy as np
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from pydantic import SecretStr
import uvicorn
from app.domains.identity.database_setup import LOGGING, create_identity_role
from app.domains.identity.runtime_database import connection_factory
from app.domains.identity.sessions import IdentitySessions
from app.domains.identity.temporary_crypto import TemporaryKeys
from app.domains.listings.embedding_bootstrap import EmbeddingBootstrap
from app.domains.listings.embedding_client import SemanticHelper
from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_worker import EmbeddingWorker
from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_identity_database,
)
from data.generators import reference
from data.generators.reference_load import LocalObjects
from data.generators.reference_rows import insert_rows
from scripts.evaluation.reference_release import verify_archive
from scripts.evaluation.k6.nfr_profile_builder import build_profile as nfr_profile
from scripts.evaluation.k6.nfr03_profile_builder import build_profile as peak_profile
from scripts.evaluation.k6.nfr_report import summarize as report_nfr
from scripts.evaluation.k6.nfr03_report import summarize as report_peak
from scripts.evaluation.k6.comparison_report import (
    summarize_points as report_comparison,
)
from scripts.evaluation.k6.exp05_pilot_profile_builder import (
    build_profile as pilot_profile,
)
from scripts.evaluation.k6.prepare_comparison_corpus import build_corpus
from scripts.evaluation.frozen_reference import load_frozen_reference
from scripts.evaluation.nfr04_retrieval import evaluate_retrieval
from scripts.evaluation.k6.install_monotonic import _extension_digest
from app.contracts.domain_types import ListingQuery, ListingSummary
from app.domains.listings.hybrid_read import encode_hybrid_query
from app.domains.listings.lexical_expansion import compile_expansion
from apps.api.tests.domains.listings.hybrid_reference import reference_hybrid_statement

BASE = "clip-exp03-hybrid:local-3691a50"
BASE_ID = "sha256:71e52d94699286b7feadfb5bc18f851228935a73a428ed411c56dc45fbf6f84b"
ARCHIVE = ROOT / "data/transfer/next06-reference-20261030.tar.gz"
DEFAULT_K6 = Path("/tmp/clip-experiment-plan/.tools/k6/v2.3.0-monotonic/k6")


def save(path, value):
    """Checkpoint safe aggregate evidence, including failures/interruption."""
    path.write_text(json.dumps(value, indent=2) + "\n")


def command(arguments, *, timeout=180):
    """Never echo subprocess arguments/private stdout on an unexpected failure."""
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"local_command_failed:{Path(arguments[0]).name}")
    return result.stdout.strip()


def build_image(directory, image):
    """Layer reviewed dirty app source and locked NumPy onto the existing model image."""
    docker = ["docker", "--context", "default"]
    assert command(
        docker
        + [
            "context",
            "inspect",
            "default",
            "--format",
            '{{(index .Endpoints "docker").Host}}',
        ]
    ).startswith("unix://")
    assert (
        command(docker + ["image", "inspect", BASE, "--format", "{{.Id}} "]) == BASE_ID
    )
    context = directory / "build"
    context.mkdir()
    shutil.copytree(
        ROOT / "apps/api/app",
        context / "app",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    site = Path(np.__file__).parent.parent
    for name in ["numpy", "numpy.libs", "numpy-2.5.4.dist-info"]:
        shutil.copytree(
            site / name, context / name, ignore=shutil.ignore_patterns("__pycache__")
        )
    shutil.copyfile(
        ROOT / "scripts/evaluation/capacity_local_worker.py", context / "worker.py"
    )
    recipe = f"""FROM {BASE}
USER root
COPY numpy /opt/venv/lib/python3.14/site-packages/numpy
COPY numpy.libs /opt/venv/lib/python3.14/site-packages/numpy.libs
COPY numpy-2.5.4.dist-info /opt/venv/lib/python3.14/site-packages/numpy-2.5.4.dist-info
COPY app /app/apps/api/app
COPY worker.py /app/capacity_local_worker.py
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
RUN python -c "import numpy; assert numpy.__version__ == '2.5.4'"
"""
    (context / "Dockerfile").write_text(recipe)
    with (directory / "image-build.log").open("w") as stream:
        result = subprocess.run(
            docker
            + ["build", "--network=none", "--pull=false", "--tag", image, str(context)],
            stdout=stream,
            stderr=subprocess.STDOUT,
            timeout=240,
        )
    if result.returncode:
        raise RuntimeError("local_image_build_failed")
    return command(docker + ["image", "inspect", image, "--format", "{{.Id}}"])


def prepare_database(connect, directory, report):
    """Load an owned exact reference copy, isolated roles and transient local sessions."""
    index = json.loads(
        (ROOT / "data/transfer/next06-reference-20261030.json").read_text()
    )
    verify_archive(index, ARCHIVE)
    unpacked = directory / "archive"
    unpacked.mkdir()
    with tarfile.open(ARCHIVE) as archive:
        archive.extractall(unpacked, filter="data")
    bundle = {
        **json.loads(
            (
                unpacked / "data/runs/next06-transfer-42-20261030-a/dataset.json"
            ).read_text()
        )
    }
    bundle["manifest"] = json.loads(
        (unpacked / "data/runs/next06-transfer-42-20261030-a/manifest.json").read_text()
    )
    # Validate the accepted frozen archive, not a regeneration against today's
    # additive API contract hashes. This copy must retain its original data ID.
    manifest = bundle["manifest"]
    config_fields = (
        "generator_version",
        "requested_counts",
        "source_revision",
        "seed",
        "logical_time",
        "schema_version",
        "source_binding",
        "recipe_digest",
        "image_source_digest",
        "sensitive_purchase_threshold_paise",
    )
    logical = {
        "config": {name: manifest[name] for name in config_fields},
        "users": bundle["users"],
        "listings": bundle["listings"],
        "image_plan": bundle["image_plan"],
    }
    frozen = json.loads(
        (ROOT / "docs/evaluation/domain/next-06/frozen-dataset.json").read_text()
    )
    if (
        reference.digest(logical) != manifest["logical_data_fingerprint"]
        or manifest["logical_data_fingerprint"] != frozen["logical_data_fingerprint"]
    ):
        raise ValueError("Frozen capacity input differs")
    objects = LocalObjects(directory / "media")
    for image in bundle["image_plan"]:
        content = (unpacked / "images" / image["source_relative_path"]).read_bytes()
        if (
            len(content) != image["size_bytes"]
            or hashlib.sha256(content).hexdigest() != image["sha256"]
        ):
            raise ValueError("Frozen photo bytes differ")
        objects.put(
            objects.object_key_for(image["upload_id"]), content, image["media_type"]
        )
    media = objects.verify(bundle)
    with connect() as c:
        report["reference_copy"] = insert_rows(
            c, bundle, object_key_for=objects.object_key_for, audit=datetime.now(UTC)
        )
    report["reference_copy"]["logical_data_fingerprint"] = bundle["manifest"][
        "logical_data_fingerprint"
    ]
    report["reference_copy"]["real_local_photo_bytes"] = media
    with connect() as c:
        c.execute("REVOKE ALL ON DATABASE clip_test_identity FROM PUBLIC")
        c.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")

    def admin():
        c = connect()
        for key, value in LOGGING.items():
            c.execute(
                sql.SQL("SET {} = {}").format(sql.Identifier(key), sql.Literal(value))
            )
        return c

    identity_password = secrets.token_hex(24)
    create_identity_role(
        admin,
        SecretStr(identity_password),
        expected_database="clip_test_identity",
        expected_admin="clip_identity_ci",
    )
    passwords = {
        "clip_test_marketplace_app": secrets.token_hex(24),
        "clip_test_conversations_app": secrets.token_hex(24),
    }
    with connect() as c:
        c.execute("ALTER ROLE clip_test_identity_app CONNECTION LIMIT 20")
        for role, password in passwords.items():
            verifier = c.pgconn.encrypt_password(
                password.encode(), role.encode(), b"scram-sha-256"
            ).decode()
            c.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOINHERIT CONNECTION LIMIT {} PASSWORD {}"
                ).format(
                    sql.Identifier(role),
                    sql.Literal(40 if "marketplace" in role else 4),
                    sql.Literal(verifier),
                )
            )
            c.execute(
                sql.SQL("GRANT CONNECT ON DATABASE clip_test_identity TO {}").format(
                    sql.Identifier(role)
                )
            )
        c.execute(
            "GRANT USAGE ON SCHEMA public,listings,search TO clip_test_marketplace_app"
        )
        c.execute(
            "GRANT SELECT ON public.schema_migrations TO clip_test_marketplace_app"
        )
        c.execute(
            "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA listings,search TO clip_test_marketplace_app"
        )
        c.execute(
            "GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA listings,search TO clip_test_marketplace_app"
        )
        c.execute(
            "GRANT USAGE ON SCHEMA public,conversations,identity TO clip_test_conversations_app"
        )
        c.execute(
            "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA conversations TO clip_test_conversations_app"
        )
        c.execute(
            "GRANT SELECT ON identity.participant_profiles TO clip_test_conversations_app"
        )
    keys = [secrets.token_hex(32) for _ in range(3)]

    def dsn(role, password, host):
        return (
            "postgresql:///"
            + "clip_test_identity?"
            + urlencode(
                {"host": host, "user": role, "password": password, "sslmode": "disable"}
            )
        )

    with connect() as c:
        host = c.info.host
        parameters = dict(
            host=host, dbname=c.info.dbname, user=c.info.user, password=c.info.password
        )
    sessions = IdentitySessions(
        connection_factory(
            SecretStr(dsn("clip_test_identity_app", identity_password, host)), "test"
        ),
        TemporaryKeys("capacity", *(bytes.fromhex(v) for v in keys)),
        lambda: datetime.now(UTC),
    )
    user = UUID(bundle["users"][-1]["id"])
    with sessions.transaction() as c:
        grant = sessions._issue(c, user, datetime.now(UTC))
    token = grant.token.get_secret_value()
    config = {
        "keys": keys,
        "identity_dsn": dsn(
            "clip_test_identity_app", identity_password, "/run/clip-db"
        ),
        "marketplace_dsn": dsn(
            "clip_test_marketplace_app",
            passwords["clip_test_marketplace_app"],
            "/run/clip-db",
        ),
        "conversations_dsn": dsn(
            "clip_test_conversations_app",
            passwords["clip_test_conversations_app"],
            "/run/clip-db",
        ),
    }
    return bundle, parameters, token, config, objects


async def prepare_vectors(parameters, report):
    """Publish real pinned-model generations in the owned reference copy only."""
    helper = SemanticHelper(
        ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
    )
    try:
        await helper.start()
        async with await psycopg.AsyncConnection.connect(
            **parameters, autocommit=True, row_factory=dict_row
        ) as c:
            operator = EmbeddingBootstrap(c)
            await operator.prepare()
            assert await operator.queue(1000) == 1000
            worker = EmbeddingWorker(EmbeddingStore(c), helper)
            for index in range(1000):
                assert await worker.run_one() == "published"
                if (index + 1) % 250 == 0:
                    print(
                        json.dumps(
                            {"stage": "local_real_vectors", "published": index + 1}
                        ),
                        flush=True,
                    )
            await operator.activate()
            report["real_vectors"] = {
                "generations": 1000,
                "model_windows": helper.windows_started,
                "model_revision": helper.spec.encoding["model_revision"],
            }
    finally:
        await helper.close()


async def run_profiles(
    connect,
    directory,
    output,
    report,
    token,
    config,
    parameters,
    image,
    k6,
    profile_set,
    lambda_weight,
    short_diagnostic=False,
    ecs_fallback_only=False,
    pool_directory=None,
    pool_identifier=None,
    lambda_environments=4,
    only_profile=None,
    repetitions=1,
):
    """Serve actual A/B app paths through loopback, run unchanged required profiles."""
    docker = list(connect.profile_docker)
    containers = []
    clients = {}
    metric_clients = {}
    server = task = None
    configuration = ["A"]
    round_robin = {"ecs": 0, "lambda": 0}
    selected_sequence = [0]
    routing_weight = [lambda_weight]
    lambda_available = asyncio.Queue()
    for index in range(lambda_environments):
        lambda_available.put_nowait(index)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    runtime = directory / "runtime"
    runtime.mkdir(mode=0o700)
    config["origin"] = origin
    (runtime / "runtime.json").write_text(json.dumps(config))
    (runtime / "runtime.json").chmod(0o600)
    root_socket = Path(parameters["host"])
    try:
        for kind in (["ecs"] if ecs_fallback_only else ["ecs", "lambda"]):
            for number in range(2 if kind == "ecs" else lambda_environments):
                name = f"{kind}-{number}"
                identifier = command(
                    docker
                    + [
                        "run",
                        "--detach",
                        "--network",
                        "none",
                        "--cpus",
                        "1",
                        "--memory",
                        "2g",
                        "--pids-limit",
                        "128",
                        "--user",
                        f"{os.getuid()}:{os.getgid()}",
                        "--mount",
                        f"type=bind,src={root_socket},dst=/run/clip-db",
                        "--mount",
                        f"type=bind,src={runtime},dst=/run/clip-capacity",
                        *(
                            [
                                "--mount",
                                f"type=bind,src={pool_directory},dst=/run/clip-pool",
                            ]
                            if pool_directory
                            else []
                        ),
                        "--entrypoint",
                        "python",
                        image,
                        "/app/capacity_local_worker.py",
                        kind,
                        str(number),
                    ]
                )
                containers.append((name, identifier))
                client = httpx.AsyncClient(
                    transport=httpx.AsyncHTTPTransport(
                        uds=str(runtime / f"{name}.sock")
                    ),
                    base_url=origin,
                    timeout=10,
                )
                clients[name] = client
                # Monitoring must not compete for the load proxy's HTTP pool.
                metric_clients[name] = httpx.AsyncClient(
                    transport=httpx.AsyncHTTPTransport(
                        uds=str(runtime / f"{name}.sock")
                    ),
                    base_url=origin,
                    timeout=3,
                )
                deadline = time.monotonic() + 45
                while True:
                    try:
                        response = await client.get("/health")
                        if response.status_code == 200:
                            break
                    except OSError, httpx.HTTPError:
                        pass
                    if time.monotonic() > deadline:
                        logs = command(docker + ["logs", identifier])
                        (output.parent / f"{name}-startup.log").write_text(logs)
                        raise RuntimeError(f"local_worker_not_ready:{name}")
                    await asyncio.sleep(0.2)
        print(
            json.dumps(
                {
                    "stage": "local_apps_ready",
                    "app_count": len(containers),
                    "cpu_each": 1,
                    "memory_gib_each": 2,
                }
            ),
            flush=True,
        )

        async def proxy(scope, receive, send):
            """Fixed loopback-only forwarding, no application response rewriting/retries."""
            if scope["type"] != "http":
                return
            if scope.get("client", ("",))[0] != "127.0.0.1":
                await send(
                    {"type": "http.response.start", "status": 403, "headers": []}
                )
                await send({"type": "http.response.body", "body": b""})
                return
            path = scope["path"]
            selected = scope["method"] == "GET" and (
                path == "/api/listings"
                or path.startswith("/api/listings/")
                and len(path.split("/")) == 4
            )
            use_lambda = False
            if selected and configuration[0] == "B":
                # Deterministic spread for local diagnostics only. Actual ALB
                # routing/weights and delivered fractions require live evidence.
                use_lambda = (selected_sequence[0] * 37) % 100 < routing_weight[0]
                selected_sequence[0] += 1
            kind = "lambda" if use_lambda else "ecs"
            number = round_robin[kind] % 2
            chunks = []
            while True:
                event = await receive()
                if event["type"] == "http.disconnect":
                    return
                chunks.append(event.get("body", b""))
                if not event.get("more_body"):
                    break
            headers = {
                k.decode(): v.decode()
                for k, v in scope["headers"]
                if k.lower()
                not in {b"connection", b"content-length", b"transfer-encoding"}
            }
            if headers.get("origin") == origin:
                headers["origin"] = "https://clip-iisc.site"
            target = path if kind == "lambda" else path.removeprefix("/api")
            if scope.get("query_string"):
                target += "?" + scope["query_string"].decode()
            if use_lambda:
                try:
                    number = lambda_available.get_nowait()
                except asyncio.QueueEmpty:
                    # Explicit local concurrency exhaustion, never hidden queue
                    # time or ECS fallback. Real ALB/Lambda error mapping differs.
                    await send(
                        {"type": "http.response.start", "status": 429, "headers": []}
                    )
                    await send({"type": "http.response.body", "body": b""})
                    return
            else:
                round_robin[kind] += 1
            try:
                response = await clients[f"{kind}-{number}"].request(
                    scope["method"], target, headers=headers, content=b"".join(chunks)
                )
            finally:
                if use_lambda:
                    lambda_available.put_nowait(number)
            response_headers = [
                (k, v)
                for k, v in response.headers.raw
                if k.lower()
                not in {
                    b"transfer-encoding",
                    b"connection",
                    b"content-encoding",
                    b"content-length",
                }
            ]
            await send(
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": response_headers,
                }
            )
            await send({"type": "http.response.body", "body": response.content})

        server = uvicorn.Server(
            uvicorn.Config(
                proxy,
                host="127.0.0.1",
                port=port,
                log_level="warning",
                access_log=False,
                lifespan="off",
            )
        )
        task = asyncio.create_task(server.serve())
        while not server.started:
            await asyncio.sleep(0.05)
        cookie = "__Host-clip_session=" + token
        async with httpx.AsyncClient(
            base_url=origin,
            headers={"Cookie": cookie, "Origin": origin, "X-CLIP-Request": "1"},
        ) as client:

            async def request(method, path, expected=200, **kwargs):
                response = await client.request(method, "/api" + path, **kwargs)
                if response.status_code != expected:
                    raise RuntimeError(
                        f'fixture_http_status:{response.status_code}:{path.split("/")[1]}'
                    )
                return response.json() if response.content else None

            csrf = (await request("GET", "/auth/csrf"))["csrf_token"]
            client.headers["X-CSRF-Token"] = csrf
            page = await request("GET", "/listings?page=1&page_size=20")
            identifiers = [row["listing_id"] for row in page["items"]]
            conversation = await request(
                "POST",
                f"/listings/{identifiers[0]}/conversations",
                expected=201,
                json={"operation_id": str(uuid4())},
            )
            for identifier in identifiers[:5]:
                await request(
                    "PUT",
                    f"/me/saved-listings/{identifier}",
                    json={"operation_id": str(uuid4())},
                )
            wanted = await request(
                "POST",
                "/wanted-requests",
                expected=201,
                json={
                    "operation_id": str(uuid4()),
                    "title": "Capacity controlled wanted fixture",
                    "description": "Owned local workload fixture",
                    "category_code": "other",
                    "budget_paise": None,
                },
            )
        fixture = {
            "dataset_fingerprint": "sha256:7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98",
            "wanted_request_id": wanted["request_id"],
            "conversation_id": conversation["conversation_id"],
            "saved_listing_ids": identifiers[:5],
            "category_code": "other",
        }
        report["local_configuration"] = {
            "application_cpus": 1,
            "application_memory_gib": 2,
            "ecs_tasks": 2,
            "lambda_serial_environments_tested": (
                0 if ecs_fallback_only else lambda_environments
            ),
            "B_read_weight_percent": None if ecs_fallback_only else lambda_weight,
            "database_cpus": 2,
            "database_memory_gib": 1,
            "database_max_connections": 78,
            "identity_role_limit": 20,
            "marketplace_role_limit": 40,
            "conversations_role_limit": 4,
            "transport": "loopback HTTP plus private UDS; HTTPS scheme adaptation only; no TLS/ALB emulation",
        }
        phases = [
            ("A", "nfr-03"),
            ("B", "nfr-03"),
            ("A", "nfr-01"),
            ("B", "nfr-01"),
            ("A", "nfr-02"),
            ("B", "nfr-02"),
        ]
        if profile_set == "route-trace":
            trace = []
            trace_cases = build_corpus()["cases"]
            async with httpx.AsyncClient(
                base_url=origin + "/api", timeout=20, headers={"Cookie": cookie}
            ) as probe:
                for name in ("A", "B"):
                    configuration[0] = name
                    for iteration in range(30):
                        item = trace_cases[iteration % len(trace_cases)]
                        request = item["request"]
                        path = (
                            "/listings/" + request["listing_id"]
                            if request["kind"] == "detail"
                            else "/listings"
                        )
                        started = time.monotonic()
                        response = await probe.get(path, params=request.get("query"))
                        trace.append(
                            {
                                "configuration": name,
                                "kind": request["kind"],
                                "elapsed_ms": (time.monotonic() - started) * 1000,
                                "status": response.status_code,
                            }
                        )
                    for worker, client in metric_clients.items():
                        report.setdefault("trace_worker_metrics", {})[worker] = (
                            await client.get("/__capacity_metrics")
                        ).json()
            save(output.parent / "route-trace.json", trace)
            report["trace"] = trace
            save(output, report)
            phases = []
        if profile_set == "nfr-remaining":
            phases = [phase for phase in phases if phase[1] != "nfr-03"]
        comparison_cases = None
        if profile_set in {"comparison-quality", "short-release"}:
            phases = [
                ("A", "exp-05"),
                ("B", "exp-05"),
                ("A", "nfr-03"),
                ("B", "nfr-03"),
            ]
            if profile_set == "short-release":
                phases += [
                    ("A", "nfr-01"),
                    ("B", "nfr-01"),
                    ("A", "nfr-02"),
                    ("B", "nfr-02"),
                ]
            _bundle, labels, binding = load_frozen_reference()
            report["quality_checks"] = []
            comparison_cases = build_corpus()["cases"]
            quality_oracles = {}
            # The pilot's strict ordered search oracle comes from original SQL,
            # not from the application under test. This occurs before traffic.
            helper = SemanticHelper(
                ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
            )
            try:
                await helper.start()
                async with await psycopg.AsyncConnection.connect(
                    **parameters, autocommit=True, row_factory=dict_row
                ) as connection:
                    query_inputs = [
                        (item["request"]["query"], item)
                        for item in comparison_cases
                        if item["request"]["kind"] == "search"
                    ]
                    query_inputs += [
                        ({"q": row["query_text"], **row["context"]}, None)
                        for row in labels["queries"]
                        if row["include_in_nfr04"]
                    ]
                    for query_input, item in query_inputs:
                        query = ListingQuery.model_validate(query_input)
                        if query.q not in quality_oracles:
                            embedding = await encode_hybrid_query(helper, query)
                            compiled = await compile_expansion(connection, query.q)
                            statement, values = reference_hybrid_statement(
                                query,
                                datetime.now(UTC),
                                500000,
                                embedding,
                                compiled,
                                relevance=True,
                            )
                            row = await (
                                await connection.execute(statement, values)
                            ).fetchone()
                            if row is None or not row["ready"]:
                                raise RuntimeError("local_original_oracle_unavailable")
                            rows = row["items"]
                            quality_oracles[query.q] = {
                                "items": [
                                    ListingSummary.model_validate(value).model_dump(
                                        mode="json"
                                    )
                                    for value in rows[: query.page_size]
                                ],
                                "page": query.page,
                                "page_size": query.page_size,
                                "has_next": len(rows) > query.page_size,
                            }
                        if item is not None:
                            item["expected"] = quality_oracles[query.q]
            finally:
                await helper.close()
            save(output.parent / "comparison-original-sql-cases.json", comparison_cases)
            save(output.parent / "quality-original-sql-pages.json", quality_oracles)
            async with httpx.AsyncClient(
                base_url=origin + "/api", timeout=20, headers={"Cookie": cookie}
            ) as quality_client:
                for config_name in (("A",) if ecs_fallback_only else ("A", "B")):
                    configuration[0] = config_name
                    routing_weight[0] = (
                        100  # Every reviewed query exercises each code path.
                    )
                    responses = {}
                    observations = []
                    for row in labels["queries"]:
                        if not row["include_in_nfr04"]:
                            continue
                        started = time.monotonic()
                        response = await quality_client.get(
                            "/listings",
                            params={"q": row["query_text"], **row["context"]},
                        )
                        elapsed_ms = (time.monotonic() - started) * 1000
                        body = response.json()
                        responses[row["query_text"]] = (response.status_code, body)
                        observations.append(
                            {
                                "query_id": row["query_id"],
                                "status": response.status_code,
                                "elapsed_ms": elapsed_ms,
                                "body": body,
                            }
                        )
                    raw_quality = output.parent / f"quality-{config_name}.raw.json"
                    save(raw_quality, observations)
                    quality = evaluate_retrieval(
                        labels,
                        binding,
                        lambda text, context: responses[text],
                        labels_sha256=hashlib.sha256(
                            (ROOT / "data/evaluation/query-labels.json").read_bytes()
                        ).hexdigest(),
                        model_revision=report["real_vectors"]["model_revision"],
                        application_revision=report["source_revision"],
                        source_kind="local_fixture",
                    )
                    quality["local_diagnostic_only"] = True
                    quality["all_ordered_pages_match_original_sql"] = all(
                        status == 200 and body == quality_oracles[text]
                        for text, (status, body) in responses.items()
                    )
                    quality["selected_read_weight_percent"] = (
                        0 if config_name == "A" else 100
                    )
                    quality["raw_path"] = str(raw_quality)
                    quality["raw_sha256"] = hashlib.sha256(
                        raw_quality.read_bytes()
                    ).hexdigest()
                    report["quality_checks"].append(
                        {"configuration": config_name, **quality}
                    )
                    save(output, report)
                    print(
                        json.dumps(
                            {
                                "stage": "reviewed_quality_checked",
                                "configuration": config_name,
                                "retrieval_failures": quality["retrieval_failures"],
                            }
                        ),
                        flush=True,
                    )
        routing_weight[0] = lambda_weight
        if only_profile:
            phases = [phase for phase in phases if phase[1] in only_profile]
        # Repeat the same ordered profiles without rebuilding or changing their
        # rates. Every repetition gets distinct raw/report paths and cleanup.
        phases = phases * repetitions
        for config_name, kind in phases:
            if ecs_fallback_only and config_name != "A":
                continue
            configuration[0] = config_name
            run_id = f"lunch-{config_name.lower()}-{kind}-{secrets.token_hex(3)}"
            if kind == "exp-05":
                profile = pilot_profile(
                    {
                        "cases": comparison_cases,
                        "sequence_starts": {"low": 0, "normal": 0, "burst": 0},
                        "capacity": {"preAllocatedVUs": 100, "maxVUs": 300},
                        "timeout_seconds": 5,
                    },
                    run_id,
                    config_name,
                    100,
                    300,
                    fixture["dataset_fingerprint"],
                )
            elif kind == "nfr-03":
                profile = peak_profile(run_id, config_name, fixture, 100, 300)
            else:
                profile = nfr_profile(kind, config_name, run_id, 100, 300)
            path = output.parent / f"{run_id}.profile.json"
            save(path, profile)
            # The strict profile remains immutable. Only explicit local mode
            # overrides runtime timing, and its report cannot count as formal.
            reporting_profile = dict(profile)
            if short_diagnostic:
                reporting_profile.update(warmup_seconds=10, measured_seconds=60)
            save(output.parent / f"{run_id}.runtime-profile.json", reporting_profile)
            raw = output.parent / f"{run_id}.raw.jsonl"
            log = output.parent / f"{run_id}.k6.log"
            env = {k: os.environ[k] for k in ("HOME", "PATH")}
            if short_diagnostic:
                env["CLIP_CAPACITY_LOCAL_SHORT"] = "true"
            if kind == "nfr-03":
                env.update(
                    CLIP_NFR03_LOCAL_LOAD="true",
                    CLIP_NFR03_LOCAL_TARGET=origin + "/api",
                    CLIP_NFR03_LOCAL_PROFILE=str(path),
                    CLIP_NFR03_LOCAL_COOKIE=cookie,
                    CLIP_NFR03_LOCAL_CSRF=csrf,
                    CLIP_NFR03_LOCAL_ORIGIN=origin,
                )
                script = "nfr03_load.js"
            elif kind == "exp-05":
                env.update(
                    CLIP_EXP05_LOCAL_LOAD="true",
                    CLIP_EXP05_LOCAL_TARGET=origin + "/api",
                    CLIP_EXP05_LOCAL_PROFILE=str(path),
                    CLIP_EXP05_LOCAL_COOKIE=cookie,
                )
                script = "exp05_pilot_load.js"
            else:
                env.update(
                    CLIP_NFR_LOCAL_LOAD="true",
                    CLIP_NFR_LOCAL_TARGET=origin + "/api",
                    CLIP_NFR_LOCAL_PROFILE=str(path),
                    CLIP_NFR_LOCAL_COOKIE=cookie,
                )
                script = "nfr_load.js"
            observations = []
            resource_path = output.parent / f"{run_id}.resources.json"
            with log.open("w") as stream:
                process = await asyncio.create_subprocess_exec(
                    str(k6),
                    "run",
                    "--quiet",
                    "--out",
                    "json=" + str(raw),
                    str(ROOT / "scripts/evaluation/k6" / script),
                    env=env,
                    stdout=stream,
                    stderr=asyncio.subprocess.STDOUT,
                )
                print(
                    json.dumps(
                        {
                            "stage": "required_profile_started",
                            "configuration": config_name,
                            "profile": kind,
                            "raw": str(raw),
                        }
                    ),
                    flush=True,
                )
                started = time.monotonic()
                try:
                    while process.returncode is None:
                        sample = {
                            "elapsed_seconds": time.monotonic() - started,
                            "applications": {},
                            "host_memory_pressure": Path(
                                "/proc/pressure/memory"
                            ).read_text(),
                            "host_memory": {
                                line.split(":")[0]: line.split(":")[1].strip()
                                for line in Path("/proc/meminfo")
                                .read_text()
                                .splitlines()
                                if line.split(":")[0] in {"MemAvailable", "SwapFree"}
                            },
                        }
                        for name, identifier in containers:
                            values = await asyncio.to_thread(
                                command,
                                docker
                                + [
                                    "exec",
                                    identifier,
                                    "cat",
                                    "/sys/fs/cgroup/cpu.stat",
                                    "/sys/fs/cgroup/memory.current",
                                ],
                            )
                            lines = values.splitlines()
                            sample["applications"][name] = {
                                "cpu_usec": int(
                                    next(
                                        v.split()[1]
                                        for v in lines
                                        if v.startswith("usage_usec ")
                                    )
                                ),
                                "memory_bytes": int(lines[-1]),
                                "pools": (
                                    await metric_clients[name].get(
                                        "/__capacity_metrics"
                                    )
                                ).json(),
                            }
                        if pool_identifier:
                            from scripts.evaluation.pgbouncer_local import snapshot

                            sample["pgbouncer"] = await asyncio.to_thread(
                                snapshot, pool_directory, config["identity_dsn"]
                            )
                            sample["pgbouncer"]["cpu_stat"] = await asyncio.to_thread(
                                command,
                                docker
                                + [
                                    "exec",
                                    pool_identifier,
                                    "cat",
                                    "/sys/fs/cgroup/cpu.stat",
                                ],
                            )
                        values = await asyncio.to_thread(
                            command,
                            docker
                            + [
                                "exec",
                                connect.profile_container_id,
                                "cat",
                                "/sys/fs/cgroup/cpu.stat",
                                "/sys/fs/cgroup/memory.current",
                            ],
                        )
                        lines = values.splitlines()
                        sample["database"] = {
                            "cpu_usec": int(
                                next(
                                    v.split()[1]
                                    for v in lines
                                    if v.startswith("usage_usec ")
                                )
                            ),
                            "memory_bytes": int(lines[-1]),
                        }

                        def database_waits():
                            with connect() as connection:
                                return connection.execute(
                                    "SELECT usename,state,wait_event_type,wait_event,count(*) FROM pg_stat_activity WHERE datname=current_database() GROUP BY 1,2,3,4"
                                ).fetchall()

                        sample["database"]["waits"] = await asyncio.to_thread(
                            database_waits
                        )
                        observations.append(sample)
                        save(resource_path, observations)
                        if "script exception" in log.read_text()[:20000]:
                            raise RuntimeError("local_workload_script_exception")
                        if time.monotonic() - started > 430:
                            raise TimeoutError("local_profile_deadline")
                        try:
                            await asyncio.wait_for(process.wait(), timeout=2)
                        except TimeoutError:
                            pass
                finally:
                    if process.returncode is None:
                        process.terminate()
                        await process.wait()
                    save(resource_path, observations)
            points = []
            if raw.exists():
                with raw.open() as source:
                    points = [json.loads(line) for line in source]
            result = (
                report_peak(points, reporting_profile, local_short=short_diagnostic)
                if kind == "nfr-03"
                else (
                    report_comparison(points, reporting_profile, "burst")
                    if kind == "exp-05"
                    else report_nfr(
                        points, reporting_profile, local_short=short_diagnostic
                    )
                )
            )
            result["local_diagnostic_only"] = True
            result_path = output.parent / f"{run_id}.report.json"
            save(result_path, result)
            resource_path = output.parent / f"{run_id}.resources.json"
            save(resource_path, observations)
            report.setdefault("runs", []).append(
                {
                    "run_id": run_id,
                    "configuration": config_name,
                    "profile": kind,
                    "exit_code": process.returncode,
                    "raw_path": str(raw),
                    "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                    "report_path": str(result_path),
                    "resources_path": str(resource_path),
                    "threshold_met_in_preview": result.get("threshold_met_in_preview"),
                    "accounting_complete": result["accounting_complete"],
                    "delivery_complete": result["delivery_complete"],
                }
            )
            save(output, report)
            print(json.dumps(report["runs"][-1]), flush=True)
            if (
                process.returncode
                or not result["accounting_complete"]
                or not result["delivery_complete"]
            ):
                raise RuntimeError("required_profile_invalid_preserved")
    finally:
        if server is not None:
            server.should_exit = True
        if task is not None:
            await task
        for client in (*clients.values(), *metric_clients.values()):
            await client.aclose()
        for name, identifier in containers:
            with (output.parent / f"{name}-runtime.log").open("w") as stream:
                subprocess.run(
                    docker + ["logs", identifier],
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=15,
                )
            command(docker + ["rm", "--force", identifier])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-local", required=True, action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--k6", type=Path, default=DEFAULT_K6)
    parser.add_argument(
        "--profile-set",
        choices=(
            "nfr",
            "nfr-remaining",
            "comparison-quality",
            "route-trace",
            "short-release",
        ),
        default="nfr",
    )
    parser.add_argument(
        "--lambda-weight-percent", type=int, choices=(25, 50, 75, 100), default=100
    )
    parser.add_argument(
        "--ecs-fallback-only",
        action="store_true",
        help="Check ECS only in short-release mode, using the selected direct or PgBouncer transport; never claims a B result.",
    )
    parser.add_argument(
        "--pgbouncer",
        action="store_true",
        help="Use the actual bounded local PgBouncer service for both architectures.",
    )
    parser.add_argument(
        "--lambda-environments",
        type=int,
        choices=range(1, 11),
        default=4,
        help="Explicit simulated Lambda concurrency; match the reviewed target. Exhaustion returns local 429 rather than queueing behind a busy environment.",
    )
    parser.add_argument(
        "--only-profile",
        action="append",
        choices=("exp-05", "nfr-01", "nfr-02", "nfr-03"),
        help="Isolate a failed local profile without changing its workload or rate.",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        choices=range(1, 4),
        default=1,
        help="Repeat the selected local profiles in the same order, retaining every result.",
    )
    args = parser.parse_args()
    short_diagnostic = args.profile_set == "short-release"
    if args.ecs_fallback_only and not short_diagnostic:
        parser.error("ECS fallback selection requires short-release mode")
    if (
        args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
    ):
        parser.error("choose a new output file in an existing directory")
    if any(name.startswith(("PG", "CLIP_", "AWS_")) for name in os.environ):
        parser.error("ambient cloud/application/database configuration refused")
    report = {
        "at_utc": datetime.now(UTC).isoformat(),
        "purpose": "required-rate local diagnostic; no deployed NFR acceptance",
        "complete": False,
        "profile_set": args.profile_set,
        "only_profile": args.only_profile,
        "repetitions": args.repetitions,
        "short_local_diagnostic": short_diagnostic,
        "configurations": ["A"] if args.ecs_fallback_only else ["A", "B"],
        "database_transport": (
            "local-pgbouncer-unix-sockets"
            if args.pgbouncer
            else "direct-local-postgresql-not-managed-proxy"
        ),
        "runtime_window": (
            {"warmup_seconds": 10, "measured_seconds": 60} if short_diagnostic else None
        ),
        "source_revision": command(["git", "rev-parse", "HEAD"]),
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in list((ROOT / "apps/api/app").rglob("*.py"))
            + [
                ROOT / "pyproject.toml",
                ROOT / "uv.lock",
                Path(__file__),
                ROOT / "scripts/evaluation/capacity_local_worker.py",
                ROOT / "scripts/evaluation/frozen_reference.py",
                ROOT / "scripts/evaluation/k6/prepare_comparison_corpus.py",
                ROOT / "scripts/evaluation/k6/prepare_nfr_cases.py",
                ROOT / "scripts/evaluation/k6/nfr_report.py",
                ROOT / "scripts/evaluation/k6/nfr03_report.py",
                ROOT / "scripts/evaluation/k6/comparison_report.py",
                ROOT / "apps/api/tests/domains/listings/hybrid_reference.py",
            ]
        },
    }
    metadata = json.loads(args.k6.with_name("build.json").read_text())
    if (
        metadata["binary_sha256"] != hashlib.sha256(args.k6.read_bytes()).hexdigest()
        or metadata["extension_sha256"] != _extension_digest()
        or metadata["clock"] != "monotonic-time-time-subtraction"
    ):
        parser.error("the local monotonic k6 binary/extension receipt differs")
    report["timing_binary"] = metadata
    report["workload_source_sha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / "scripts/evaluation/k6").glob("*.js")
    }
    save(args.output, report)
    image = "clip-local-capacity:" + secrets.token_hex(6)
    built = False
    try:
        with TemporaryDirectory(prefix="clip-capacity-local-", dir="/tmp") as temp:
            directory = Path(temp)
            report["image_id"] = build_image(directory, image)
            built = True
            (directory / "database").mkdir(mode=0o700)
            with disposable_identity_database(
                directory / "database", profile_limits=True, profile_memory_gib=1
            ) as connect:
                bundle, parameters, token, config, objects = prepare_database(
                    connect, directory, report
                )
                save(args.output, report)
                asyncio.run(prepare_vectors(parameters, report))
                save(args.output, report)
                from contextlib import nullcontext
                from scripts.evaluation.pgbouncer_local import local_pool

                pool_context = (
                    local_pool(directory, Path(parameters["host"]), config, report)
                    if args.pgbouncer
                    else nullcontext((None, None))
                )
                with pool_context as (pool_directory, pool_identifier):
                    asyncio.run(
                        run_profiles(
                            connect,
                            directory,
                            args.output,
                            report,
                            token,
                            config,
                            parameters,
                            image,
                            args.k6,
                            args.profile_set,
                            args.lambda_weight_percent,
                            short_diagnostic,
                            args.ecs_fallback_only,
                            pool_directory,
                            pool_identifier,
                            args.lambda_environments,
                            args.only_profile,
                            args.repetitions,
                        )
                    )
        report["complete"] = True
        report["owned_resources_removed"] = True
    except Exception as error:
        report["failure"] = {
            "type": type(error).__name__,
            "safe_code": (
                str(error)
                if isinstance(error, RuntimeError)
                and str(error).startswith(("local_", "required_", "fixture_"))
                else "details_withheld"
            ),
        }
        report["failure"]["source_trace"] = [
            {"file": frame.filename, "line": frame.lineno, "function": frame.name}
            for frame in traceback.extract_tb(error.__traceback__)
        ]
        save(args.output, report)
        print(
            json.dumps(
                {
                    "failed": True,
                    "evidence": str(args.output),
                    "failure": report["failure"],
                }
            ),
            flush=True,
        )
        return 1
    finally:
        if built:
            command(["docker", "--context", "default", "image", "rm", image])
        save(args.output, report)
    print(json.dumps({"complete": True, "evidence": str(args.output)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
