"""Fresh private PostgreSQL for Identity integration tests; never retained targets."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[5]


def failure_category(output):
    """Map private subprocess output to fixed categories; never return raw text."""
    message = output.lower()
    for category, phrases in (
        ("connection-refused", ("connection refused",)),
        ("authentication", ("password authentication failed",)),
        ("permission", ("permission denied",)),
        (
            "name-resolution",
            (
                "could not resolve host",
                "no such host",
                "temporary failure in name resolution",
            ),
        ),
        (
            "image-unavailable",
            ("pull access denied", "toomanyrequests", "manifest unknown"),
        ),
    ):
        if any(phrase in message for phrase in phrases):
            return category
    return "command-failed"


def wait_for_migration_tcp(command, docker, container, password):
    """Gate migrations on authenticated TCP in the owned container, not bootstrap Unix SQL.

    The official image temporarily accepts Unix connections before its final TCP
    server starts. Probe the same host/database/user as dbmate inside that network
    namespace. Keep the deadline bounded and credentials in environment only.
    """
    deadline = time.monotonic() + 30
    reason = "not-ready"
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(
                f"Disposable PostgreSQL TCP readiness failed ({reason}); output withheld"
            ) from None
        try:
            version = command(
                docker
                + [
                    "exec",
                    "--env",
                    "PGPASSWORD",
                    "--env",
                    "PGCONNECT_TIMEOUT",
                    container,
                    "psql",
                    "-XqAtw",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "clip_identity_ci",
                    "-d",
                    "clip_test_identity",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    "SHOW server_version_num",
                ],
                {"PGPASSWORD": password, "PGCONNECT_TIMEOUT": "2"},
                phase="tcp-readiness",
                timeout=min(5, remaining),
            )
        except RuntimeError:
            # The command's own exception contains only fixed, safe diagnostics.
            reason = "probe-failed"
            time.sleep(min(0.2, max(0, deadline - time.monotonic())))
            continue
        if version != "180006":
            raise RuntimeError(
                "Disposable PostgreSQL version mismatch; output withheld"
            )
        return


@pytest.fixture(scope="module")
def disposable_database(tmp_path_factory):
    """Create one fresh database, migrate it and remove only its own container."""
    with disposable_identity_database(
        tmp_path_factory.mktemp("identity-postgres")
    ) as connect:
        yield connect


@contextmanager
def disposable_identity_database(root):
    """Reusable owned local test DB only; no caller-selected DSN or retained target.

    The explicit UI preview shares the same no-network, ephemeral PostgreSQL and
    migration path as tests; always remove only the container created here.
    """
    root.chmod(0o700)
    socket = root / "socket"
    socket.mkdir()
    socket.chmod(0o777)
    password = secrets.token_hex(24)
    env = {key: os.environ[key] for key in ("HOME", "PATH")}

    def command(args, extra=None, *, phase="setup", timeout=90):
        """Run a fixed fixture operation; report its stage without private arguments/output."""
        try:
            p = subprocess.run(
                args,
                env=env | (extra or {}),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Disposable Identity database {phase} timed out; output withheld"
            ) from None
        if p.returncode:
            raise RuntimeError(
                f"Disposable Identity database {phase} failed (exit={p.returncode}, category={failure_category(p.stderr + p.stdout)}); arguments/output withheld"
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
        wait_for_migration_tcp(command, docker, container, password)
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
            phase="migration",
        )
        yield connect
    finally:
        if container:
            command(docker + ["rm", "--force", container])
