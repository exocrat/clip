"""Actual PgBouncer/PostgreSQL transaction and reuse checks on owned containers."""

from pathlib import Path
import importlib.util
import os
import asyncio
import secrets
import time
from urllib.parse import urlencode

import psycopg
import pytest

from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_identity_database,
)
from scripts.evaluation.pgbouncer_local import local_pool
from app.core.database_transport import (
    check_proxy_connection,
    connection_kwargs,
    route_database,
)
from app.domains.identity.runtime_database import IdentityConnectionPool
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "pgbouncer_entrypoint", ROOT / "infra/pgbouncer/entrypoint.py"
)
entrypoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entrypoint)


def test_original_sources_and_private_routing_remain_strict():
    source = "postgresql://clip_test_identity_app:synthetic-only@clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com:5432/clip_next06_reference?sslmode=verify-full&sslrootcert=system"
    assert (
        entrypoint.parse_source(source, "clip_test_identity_app")[1] == "synthetic-only"
    )
    for invalid in [
        source.replace("verify-full", "require"),
        source + "&options=anything",
        source.replace("clip_next06_reference", "postgres"),
        source.replace("identity_app", "marketplace_app"),
    ]:
        with pytest.raises(ValueError):
            entrypoint.parse_source(invalid, "clip_test_identity_app")
    values = psycopg.conninfo.conninfo_to_dict(route_database(source, "10.64.1.83"))
    assert values["host"] == "10.64.1.83" and values["port"] == "6432"
    assert values["sslmode"] == "verify-full" and values["sslrootcert"] == "system"
    assert entrypoint.auth_quote('synthetic"quote') == '"synthetic""quote"'


@pytest.fixture(scope="module")
def pool(tmp_path_factory):
    """Real restricted users and pool, always removed even when assertions fail."""
    if os.environ.get("CLIP_NATIVE_PGBOUNCER_TESTS") != "1":
        pytest.skip("explicit owned Docker pool test required")
    directory = tmp_path_factory.mktemp("pgbouncer-native")
    report = {}
    config = {}
    passwords = {}
    with disposable_identity_database(directory, profile_limits=True) as admin:
        with admin() as db:
            db.execute("CREATE TABLE public.pool_probe (id integer PRIMARY KEY)")
            for name, (role, _) in entrypoint.ROLES.items():
                password = secrets.token_hex(24)
                passwords[role] = password
                db.execute(
                    psycopg.sql.SQL(
                        "CREATE ROLE {} LOGIN PASSWORD {} CONNECTION LIMIT {}"
                    ).format(
                        psycopg.sql.Identifier(role),
                        psycopg.sql.Literal(password),
                        psycopg.sql.Literal(
                            {"IDENTITY": 10, "MARKETPLACE": 32, "CONVERSATIONS": 4}[
                                name
                            ]
                        ),
                    )
                )
                config[name.lower() + "_dsn"] = "postgresql:///?" + urlencode(
                    {
                        "host": "/run/clip-db",
                        "dbname": "clip_test_identity",
                        "user": role,
                        "password": password,
                        "sslmode": "disable",
                    }
                )
            db.execute(
                "GRANT SELECT, INSERT ON public.pool_probe TO clip_test_marketplace_app"
            )
            database_socket = Path(db.info.host)
        with local_pool(directory, database_socket, config, report) as (
            path,
            identifier,
        ):

            def connect(role="clip_test_identity_app", **extra):
                return psycopg.connect(
                    host=str(path),
                    port=6432,
                    dbname="clip_test_identity",
                    user=role,
                    password=passwords[role],
                    connect_timeout=3,
                    prepare_threshold=None,
                    **extra,
                )

            yield connect, admin, report, path, passwords, identifier


def test_fresh_clients_reuse_backend_and_timeouts(pool):
    connect, *_ = pool
    pids = set()
    for _ in range(25):
        with connect() as client:
            check_proxy_connection(client)
            pids.add(client.execute("SELECT pg_backend_pid()").fetchone()[0])
    assert len(pids) <= 2


def test_transactions_rollback_local_settings_and_role_isolation(pool):
    connect, *_ = pool
    with connect() as client:
        with client.transaction():
            client.execute("SET LOCAL statement_timeout='2s'")
            assert client.execute("SHOW statement_timeout").fetchone() == ("2s",)
        check_proxy_connection(client)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            client.execute("SELECT * FROM public.pool_probe")
        client.rollback()
    with connect("clip_test_marketplace_app") as client:
        client.execute("INSERT INTO public.pool_probe VALUES (1)")
        client.rollback()
        assert client.execute("SELECT count(*) FROM public.pool_probe").fetchone() == (
            0,
        )


def test_backend_cap_and_bounded_queue(pool):
    connect, *_ = pool
    clients = []
    try:
        for _ in range(8):
            client = connect()
            clients.append(client)
            client.execute("SELECT 1")
        with connect() as waiting:
            started = time.monotonic()
            with pytest.raises(psycopg.OperationalError):
                waiting.execute("SELECT 1")
            assert 0.5 < time.monotonic() - started < 3
    finally:
        for client in clients:
            client.close()


def test_bad_credentials_rejected_and_dead_backend_replaced(pool):
    connect, admin, _, path, passwords, _ = pool
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(
            host=str(path),
            port=6432,
            dbname="clip_test_identity",
            user="clip_test_identity_app",
            password="wrong-synthetic-value",
            connect_timeout=3,
        )
    with connect() as client:
        pid = client.execute("SELECT pg_backend_pid()").fetchone()[0]
    with admin() as db:
        db.execute("SELECT pg_terminate_backend(%s)", (pid,))
    time.sleep(0.1)
    with connect() as client:
        check_proxy_connection(client)
        assert client.execute("SELECT 1").fetchone() == (1,)


def test_lambda_proxy_client_reuse_and_stale_replacement(pool):
    """Frozen-client recovery must occur before business SQL, without retaining a transaction."""
    _, _, _, path, passwords, _ = pool
    dsn = "postgresql:///?" + urlencode(
        {
            "host": str(path),
            "port": "6432",
            "dbname": "clip_test_identity",
            "user": "clip_test_identity_app",
            "password": passwords["clip_test_identity_app"],
            "sslmode": "disable",
        }
    )
    client_pool = IdentityConnectionPool(
        SecretStr(dsn), "test", max_size=1, retain_idle=False
    )

    async def invocation():
        async with client_pool.invocation():
            with client_pool() as connection:
                with connection.transaction():
                    assert connection.execute("SELECT 1").fetchone() == (1,)
                return connection

    try:
        first = asyncio.run(invocation())
        assert asyncio.run(invocation()) is first
        assert first.info.transaction_status == psycopg.pq.TransactionStatus.IDLE
        first.close()  # Emulates the pool expiring a client while Lambda is frozen.
        replacement = asyncio.run(invocation())
        assert replacement is not first and not replacement.closed
    finally:
        client_pool.close()
