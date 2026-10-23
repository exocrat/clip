"""Fresh private PostgreSQL for Identity integration tests; never retained targets."""

import json
import os
from pathlib import Path
import secrets
import subprocess
import time

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def disposable_database(tmp_path_factory):
    """Create one fresh database, migrate it and remove only its own container."""
    root = tmp_path_factory.mktemp("identity-postgres")
    root.chmod(0o700)
    socket = root / "socket"
    socket.mkdir()
    socket.chmod(0o777)
    password = secrets.token_hex(24)
    env = {key: os.environ[key] for key in ("HOME", "PATH")}

    def command(args, extra=None):
        p = subprocess.run(
            args, env=env | (extra or {}), capture_output=True, text=True, timeout=90
        )
        if p.returncode:
            raise RuntimeError(
                "Disposable Identity database command failed; arguments/output withheld"
            )
        return p.stdout.strip()

    context = command(["docker", "context", "show"])
    endpoint = json.loads(command(["docker", "context", "inspect", context]))[0][
        "Endpoints"
    ]["docker"]["Host"]
    assert endpoint.startswith("unix://"), "Local Docker required"
    docker = ["docker", "--context", context]
    container = None

    def connect():
        return psycopg.connect(
            host=str(socket),
            dbname="clip_test_identity",
            user="clip_identity_ci",
            password=password,
            connect_timeout=3,
            autocommit=True,
        )

    try:
        container = command(
            docker
            + [
                "run",
                "--detach",
                "--network",
                "none",
                "--stop-timeout",
                "5",
                "--tmpfs",
                "/var/lib/postgresql:rw",
                "--mount",
                f"type=bind,src={socket},dst=/run/clip-identity",
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                "POSTGRES_USER=clip_identity_ci",
                "--env",
                "POSTGRES_DB=clip_test_identity",
                "--env",
                "POSTGRES_INITDB_ARGS=--auth-local=scram-sha-256 --auth-host=scram-sha-256",
                "postgres:18.6-bookworm",
                "postgres",
                "-c",
                "unix_socket_directories=/var/run/postgresql,/run/clip-identity",
                "-c",
                "unix_socket_permissions=0777",
                "-c",
                "timezone=UTC",
            ],
            {"POSTGRES_PASSWORD": password},
        )
        for attempt in range(45):
            try:
                with connect() as c:
                    assert (
                        c.execute("SHOW server_version_num").fetchone()[0] == "180006"
                    )
                break
            except psycopg.OperationalError:
                if attempt == 44:
                    raise RuntimeError(
                        "Disposable PostgreSQL readiness failed"
                    ) from None
                time.sleep(0.2)
        command(
            docker
            + [
                "run",
                "--rm",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--network",
                f"container:{container}",
                "--env",
                "DATABASE_URL",
                "--mount",
                f"type=bind,src={ROOT}/database/migrations,dst=/db/migrations,readonly",
                "ghcr.io/amacneil/dbmate:2.36.0",
                "--env-file",
                "/dev/null",
                "--migrations-dir",
                "/db/migrations",
                "--no-dump-schema",
                "migrate",
                "--strict",
            ],
            {
                "DATABASE_URL": f"postgres://clip_identity_ci:{password}@127.0.0.1:5432/clip_test_identity?sslmode=disable"
            },
        )
        yield connect
    finally:
        if container:
            command(docker + ["rm", "--force", container])
