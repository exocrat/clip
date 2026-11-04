"""Profile exact search SQL against its original implementation in an owned DB.

Required --synthetic-local creates a fresh network-isolated PostgreSQL18.6
fixture and removes it on exit. Mathematical vectors measure SQL cost only;
this is not model-quality, authentication, cloud or NFR evidence. No external
DSN, AWS profile, retained target, provider or application opt-in is accepted.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import math
import secrets
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from urllib.parse import urlencode
from uuid import uuid4
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

from psycopg import AsyncConnection, sql
from pydantic import SecretStr
from psycopg.rows import dict_row
from app.contracts.domain_types import ListingQuery
from app.domains.identity.database_setup import LOGGING, create_identity_role
from app.domains.identity.runtime_database import IdentityConnectionPool, ROLE
from app.domains.identity.sessions import IdentitySessions
from app.domains.identity.temporary_crypto import TemporaryKeys
from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_types import EmbeddingPart, default_pipeline_spec
from app.domains.listings.hybrid_read import bind_query, hybrid_statement
from app.domains.listings.lexical_expansion import compile_expansion
from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_identity_database,
)
from apps.api.tests.domains.listings.test_hybrid_read_postgres import live_listing
from apps.api.tests.domains.listings.hybrid_reference import reference_hybrid_statement


def vector_for(index):
    """Dense unit fixtures exercise real numeric work without claiming inference."""
    values = [math.sin(i + index * 0.03) + math.cos(i * 0.3) for i in range(384)]
    length = math.sqrt(sum(value * value for value in values))
    return tuple(value / length for value in values)


def save(path, report):
    """Preserve every completed sample, including interrupted diagnostic runs."""
    path.write_text(json.dumps(report, indent=2) + "\n")


async def profile(parameters, report, path, repetitions, cpu_counter):
    """Seed1000owned rows, then alternate old/new SQL with identical inputs."""
    async with await AsyncConnection.connect(
        **parameters, row_factory=dict_row, autocommit=True
    ) as connection:
        actual = await (
            await connection.execute(
                "SELECT current_database() AS name,inet_server_addr() IS NULL AS local"
            )
        ).fetchone()
        if actual != {"name": "clip_test_identity", "local": True}:
            raise ValueError("owned_local_target_required")
        now = datetime.now(UTC)
        spec = default_pipeline_spec()
        store = EmbeddingStore(connection)
        await store.register(spec)
        await store.set_state(spec, "building")
        vectors = {index: vector_for(index) for index in range(31)}
        outputs = {}
        async with connection.transaction():
            for index in range(1000):
                title = (
                    f"Synthetic bicycle {index}"
                    if index < 50
                    else f"Synthetic campus item {index}"
                )
                listing = await live_listing(
                    connection,
                    210000 + index,
                    now,
                    title,
                    "Controlled SQL performance fixture",
                    index * 100,
                )
                if index >= 50:
                    await connection.execute(
                        "UPDATE listings.sale_listings SET category_id=(SELECT id FROM listings.categories WHERE code='other') WHERE id=%s",
                        (listing,),
                    )
                outputs[listing] = (
                    EmbeddingPart("title", 0, vectors[index % 31]),
                    EmbeddingPart("description", 0, vectors[(index + 7) % 31]),
                )
        await store.queue_missing(spec, 1000)
        for _ in range(1000):
            job = await store.claim(spec)
            if job is None or not await store.complete(job, outputs[job.listing_id], 1):
                raise ValueError("fixture_publication_failed")
        if await store.claim(spec) is not None:
            raise ValueError("unexpected_fixture_jobs")
        await store.set_state(spec, "serving")
        await connection.execute("ANALYZE")
        cases = [
            ("broad-semantic", ListingQuery(q="xylophonic", sort="relevance")),
            (
                "filtered-semantic",
                ListingQuery(q="xylophonic", sort="relevance", max_price_paise=9900),
            ),
            ("selective-lexical-page1", ListingQuery(q="bicycle", sort="relevance")),
            (
                "selective-lexical-page3",
                ListingQuery(q="bicycle", sort="relevance", page=3),
            ),
            ("lexical-recency", ListingQuery(q="campus", sort="created_desc")),
            ("lexical-price", ListingQuery(q="bicycle", sort="price_asc")),
        ]
        report["fixtures"] = {
            "listings": 1000,
            "vector_parts": 2000,
            "distinct_dense_vectors": 31,
        }
        prepared = {}
        for label, request in cases:
            began = time.perf_counter()
            compiled = await compile_expansion(connection, request.q)
            expansion_ms = (time.perf_counter() - began) * 1000
            bound = bind_query(request.q, spec, vectors[0])
            reference = reference_hybrid_statement(
                request,
                now,
                500000,
                bound,
                compiled,
                relevance=request.sort == "relevance",
            )
            optimized_query = hybrid_statement(
                request,
                now,
                500000,
                bound,
                compiled,
                relevance=request.sort == "relevance",
            )
            for attempt in range(repetitions):
                results = {}

                async def execute(name, query):
                    """Record one measured SQL attempt, including failures."""
                    sample = {
                        "case": label,
                        "attempt": attempt + 1,
                        "implementation": name,
                    }
                    began = time.perf_counter()
                    client_cpu = time.process_time()
                    try:
                        async with connection.transaction():
                            await connection.execute(
                                "SET LOCAL statement_timeout='10s'"
                            )
                            value = await (await connection.execute(*query)).fetchone()
                        sample["completed"] = True
                        return value
                    except Exception as error:
                        sample.update(
                            completed=False,
                            error_type=type(error).__name__,
                            sqlstate=getattr(error, "sqlstate", None),
                        )
                        raise
                    finally:
                        sample["elapsed_ms"] = (time.perf_counter() - began) * 1000
                        sample["client_cpu_ms"] = (
                            time.process_time() - client_cpu
                        ) * 1000
                        report["samples"].append(sample)
                        save(path, report)

                if attempt % 2 == 0:
                    results["original"] = await execute("original", reference)
                results["optimized"] = await execute("optimized", optimized_query)
                if attempt % 2:
                    results["original"] = await execute("original", reference)
                if results["original"] != results["optimized"]:
                    raise ValueError("ordered_response_equivalence_failed")
                prepared[label] = (*optimized_query, results["original"])
                report["pairs"].append(
                    {
                        "case": label,
                        "attempt": attempt + 1,
                        "exact_response_match": True,
                        "expansion_ms": expansion_ms,
                    }
                )
                save(path, report)
                print(json.dumps(report["pairs"][-1]), flush=True)
        await concurrency_probe(parameters, prepared, report, path, cpu_counter)


async def concurrency_probe(parameters, cases, report, path, cpu_counter):
    """Measure4reused connections against the2CPU owned database; SQL only.

    Include every fixed diagnostic operation and retain each latency/failure.
    Authentication, model work and network overhead are outside this probe.
    """
    connections = [
        await AsyncConnection.connect(
            **parameters, row_factory=dict_row, autocommit=True
        )
        for _ in range(4)
    ]
    try:
        for connection in connections:
            await connection.execute("SET statement_timeout='10s'")
        for label, sequence in [
            ("broad-semantic", [cases["broad-semantic"]]),
            ("selective-lexical", [cases["selective-lexical-page1"]]),
            (
                "search-mix",
                [
                    cases["broad-semantic"],
                    cases["selective-lexical-page1"],
                    cases["filtered-semantic"],
                ],
            ),
        ]:
            observations = []

            async def worker(connection, worker_index):
                for index in range(10):
                    statement, values, expected = sequence[
                        (worker_index * 10 + index) % len(sequence)
                    ]
                    began = time.perf_counter()
                    try:
                        actual = await (
                            await connection.execute(statement, values)
                        ).fetchone()
                        valid = actual == expected
                        observation = {"correct": valid}
                    except Exception as error:
                        observation = {
                            "correct": False,
                            "error_type": type(error).__name__,
                            "sqlstate": getattr(error, "sqlstate", None),
                        }
                    observation["elapsed_ms"] = (time.perf_counter() - began) * 1000
                    observations.append(observation)

            cpu_before = cpu_counter()
            began = time.perf_counter()
            await asyncio.gather(
                *(
                    worker(connection, index)
                    for index, connection in enumerate(connections)
                )
            )
            seconds = time.perf_counter() - began
            cpu_seconds = (cpu_counter() - cpu_before) / 1_000_000
            result = {
                "case": label,
                "connections": 4,
                "issued": len(observations),
                "correct": sum(item["correct"] for item in observations),
                "seconds": seconds,
                "correct_sql_per_second": sum(item["correct"] for item in observations)
                / seconds,
                "database_cpu_seconds": cpu_seconds,
                "database_cpu_ms_per_issued": cpu_seconds * 1000 / len(observations),
                "observations": observations,
            }
            report.setdefault("sql_only_concurrency", []).append(result)
            save(path, report)
            print(
                json.dumps({k: v for k, v in result.items() if k != "observations"}),
                flush=True,
            )
    finally:
        for connection in connections:
            await connection.close()


def profile_authentication(connect, report, path, cpu_counter):
    """Time the real pooled session+eligibility SQL for one controlled local actor.

    A synthetic session is issued in the new owned DB; no Microsoft, password
    login, real credentials or user account is exercised. Keep every sample and
    observe the same-account locking used by a one-account API workload.
    """

    def admin():
        """Use only this invocation's owned connection with safe logging settings."""
        connection = connect()
        for name, value in LOGGING.items():
            connection.execute(
                sql.SQL("SET {}={}").format(sql.Identifier(name), sql.Literal(value))
            )
        return connection

    with admin() as connection:
        connection.execute("REVOKE ALL ON DATABASE clip_test_identity FROM PUBLIC")
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        host, port = connection.info.host, connection.info.port
    password = secrets.token_hex(24)
    create_identity_role(
        admin,
        SecretStr(password),
        expected_database="clip_test_identity",
        expected_admin="clip_identity_ci",
    )
    dsn = SecretStr(
        "postgresql:///clip_test_identity?"
        + urlencode(
            {
                "host": host,
                "port": port,
                "user": ROLE,
                "password": password,
                "sslmode": "disable",
            }
        )
    )
    pooled = IdentityConnectionPool(dsn, "test", max_size=4)
    sessions = IdentitySessions(
        pooled,
        TemporaryKeys("local-timing", *(secrets.token_bytes(32) for _ in range(3))),
        lambda: datetime.now(UTC),
    )
    actor = uuid4()
    try:
        with admin() as connection:
            connection.execute(
                "INSERT INTO identity.users(id,account_class,status,display_name) VALUES (%s,'regular','active','Controlled local timing actor')",
                (actor,),
            )
        with sessions.transaction() as connection:
            grant = sessions._issue(connection, actor, datetime.now(UTC))
        token = grant.token.get_secret_value()
        # Warm all4leases outside the measured phase, matching a steady pool.
        with ExitStack() as stack:
            for _ in range(4):
                stack.enter_context(pooled())
        observations = []

        def request(index):
            """Run unchanged current-session and fresh account-eligibility reads."""
            began = time.perf_counter()
            cpu = time.thread_time()
            try:
                identity = sessions.authenticate(token)
                row, now = sessions.capabilities._snapshot(identity.caller.user_id)
                correct = sessions.capabilities._active(row, now)
                return {
                    "correct": correct,
                    "elapsed_ms": (time.perf_counter() - began) * 1000,
                    "client_cpu_ms": (time.thread_time() - cpu) * 1000,
                }
            except Exception as error:
                return {
                    "correct": False,
                    "elapsed_ms": (time.perf_counter() - began) * 1000,
                    "error_type": type(error).__name__,
                }

        cpu_before = cpu_counter()
        began = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as executor:
            observations = list(executor.map(request, range(200)))
        elapsed = time.perf_counter() - began
        cpu_seconds = (cpu_counter() - cpu_before) / 1_000_000
        result = {
            "purpose": "pooled session and eligibility SQL only; synthetic session, no provider login",
            "connections": 4,
            "concurrent_callers": 8,
            "issued": 200,
            "correct": sum(item["correct"] for item in observations),
            "seconds": elapsed,
            "correct_phases_per_second": sum(item["correct"] for item in observations)
            / elapsed,
            "database_cpu_ms_per_issued": cpu_seconds * 1000 / 200,
            "observations": observations,
        }
        report["authentication_sql"] = result
        save(path, report)
        print(
            json.dumps(
                {key: value for key, value in result.items() if key != "observations"}
            ),
            flush=True,
        )
        if result["correct"] != 200:
            raise ValueError("local_authentication_phase_failed")
    finally:
        pooled.close()


def main():
    """Require explicit local opt-in and a new output path before starting fixtures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-local", required=True, action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repetitions", type=int, choices=(3, 5), default=3)
    args = parser.parse_args()
    if (
        args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
    ):
        parser.error("Choose a new output file in an existing directory")
    if any(name.startswith(("PG", "CLIP_", "AWS_")) for name in os.environ):
        parser.error("Run without ambient database, application or AWS configuration")
    sources = [
        "apps/api/app/domains/listings/hybrid_read.py",
        "apps/api/app/domains/listings/postgres_store.py",
        "apps/api/app/domains/listings/embedding_client.py",
        "apps/api/tests/domains/listings/hybrid_reference.py",
    ]
    report = {
        "at_utc": datetime.now(UTC).isoformat(),
        "purpose": "local diagnostic; synthetic sessions; no real provider/cloud/model-quality/NFR claim",
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in sources
        },
        "samples": [],
        "pairs": [],
        "complete": False,
        "owned_database_removed": False,
    }
    save(args.output, report)
    try:
        with TemporaryDirectory(prefix="clip-search-profile-", dir="/tmp") as directory:
            with disposable_identity_database(
                Path(directory), profile_limits=True
            ) as connect:
                with connect() as connection:
                    parameters = dict(
                        host=connection.info.host,
                        port=connection.info.port,
                        dbname=connection.info.dbname,
                        user=connection.info.user,
                        password=connection.info.password,
                    )
                docker = list(connect.profile_docker)
                container_id = connect.profile_container_id

                def cpu_counter():
                    """Read aggregate CPU use of only this invocation's container."""
                    values = subprocess.check_output(
                        docker
                        + ["exec", container_id, "cat", "/sys/fs/cgroup/cpu.stat"],
                        text=True,
                    )
                    return int(
                        next(
                            line.split()[1]
                            for line in values.splitlines()
                            if line.startswith("usage_usec ")
                        )
                    )

                report["local_database_limits"] = {
                    "cpu_quota_vcpu": 2,
                    "memory_gib": 2,
                    "cloud_hardware_emulated": False,
                }
                asyncio.run(
                    profile(
                        parameters, report, args.output, args.repetitions, cpu_counter
                    )
                )
                profile_authentication(connect, report, args.output, cpu_counter)
        report["complete"] = True
        report["owned_database_removed"] = True
    except Exception as error:
        report["failure"] = {
            "type": type(error).__name__,
            "sqlstate": getattr(error, "sqlstate", None),
        }
        save(args.output, report)
        print(
            json.dumps({"diagnostic_failed": True, "safe_failure": report["failure"]})
        )
        return 1
    save(args.output, report)
    print(json.dumps({"complete": True, "evidence": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
