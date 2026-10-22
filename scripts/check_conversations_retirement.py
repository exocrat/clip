"""Run Conversations database operations against a fresh local PostgreSQL.

The harness binds a generated host port to loopback only, uses tmpfs instead of
a persistent volume, applies the checked-in migrations, runs focused API tests,
and removes only the container it created. It never accepts a database target.
"""

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = "postgres:18.6-bookworm"
DBMATE_IMAGE = "ghcr.io/amacneil/dbmate:2.36.0"
DATABASE_NAME = "clip_test_cn01"
DATABASE_USER = "clip_ci"


def main() -> int:
    """Create, migrate, test, and remove one isolated local database."""
    environment = {
        key: os.environ[key] for key in ("HOME", "PATH") if key in os.environ
    }
    password = secrets.token_hex(24)
    container: str | None = None

    def run(command: list[str], *, stdin: str | None = None, extra=None) -> str:
        """Bound a child command and redact the synthetic database password."""
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment | (extra or {}),
            input=stdin,
            text=True,
            capture_output=True,
            timeout=240,
        )
        if result.returncode:
            output = (result.stdout + result.stderr).replace(password, "[REDACTED]")
            raise RuntimeError(f"local database check failed: {output[-3000:]}")
        return result.stdout.strip()

    try:
        context_name = run(["docker", "context", "show"])
        context_data = json.loads(run(["docker", "context", "inspect", context_name]))
        endpoint = context_data[0]["Endpoints"]["docker"]["Host"]
        if not endpoint.startswith("unix://"):
            raise RuntimeError("a local Unix-socket Docker context is required")
        docker = ["docker", "--context", context_name]

        container = run(
            docker
            + [
                "run",
                "--detach",
                "--publish",
                "127.0.0.1::5432",
                "--stop-timeout",
                "5",
                "--tmpfs",
                "/var/lib/postgresql:rw",
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                f"POSTGRES_USER={DATABASE_USER}",
                "--env",
                f"POSTGRES_DB={DATABASE_NAME}",
                "--env",
                "POSTGRES_HOST_AUTH_METHOD=scram-sha-256",
                "--env",
                "POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --encoding=UTF8 --locale=C.UTF-8",
                POSTGRES_IMAGE,
                "postgres",
                "-c",
                "timezone=UTC",
                "-c",
                "log_timezone=UTC",
            ],
            extra={"POSTGRES_PASSWORD": password},
        )
        published = run(docker + ["port", container, "5432/tcp"])
        if not published.startswith("127.0.0.1:"):
            raise RuntimeError("PostgreSQL was not published to loopback only")
        host_port = int(published.rsplit(":", 1)[1])

        def sql(statement: str) -> str:
            """Execute SQL only inside the newly created test container."""
            return run(
                docker
                + [
                    "exec",
                    "-i",
                    "--env",
                    "PGPASSWORD",
                    container,
                    "psql",
                    "-XqAt",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    DATABASE_USER,
                    "-d",
                    DATABASE_NAME,
                    "-v",
                    "ON_ERROR_STOP=1",
                ],
                stdin=statement,
                extra={"PGPASSWORD": password},
            )

        ready = False
        for attempt in range(60):
            try:
                if sql("SELECT 1") == "1":
                    ready = True
                    break
            except RuntimeError:
                if attempt == 59:
                    raise
            time.sleep(1)
        if not ready:
            raise RuntimeError("the disposable PostgreSQL did not become ready")
        if sql("SHOW server_version_num") != "180006":
            raise RuntimeError("expected PostgreSQL 18.6")

        database_url = (
            f"postgres://{DATABASE_USER}:{password}@127.0.0.1:5432/"
            f"{DATABASE_NAME}?sslmode=disable"
        )
        run(
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
                DBMATE_IMAGE,
                "--env-file",
                "/dev/null",
                "--migrations-dir",
                "/db/migrations",
                "--no-dump-schema",
                "migrate",
            ],
            extra={"DATABASE_URL": database_url},
        )
        if sql("SELECT max(version) FROM public.schema_migrations") != "20261021101000":
            raise RuntimeError(
                "the disposable database is not at the current migration head"
            )

        # The API test fixture captures this test-only variable at import time;
        # its common autouse fixture then removes all CLIP_* variables.
        test_conninfo = (
            f"host=127.0.0.1 port={host_port} dbname={DATABASE_NAME} "
            f"user={DATABASE_USER} password={password} sslmode=disable"
        )
        test_environment = environment | {"CLIP_TEST_DATABASE_DSN": test_conninfo}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "apps/api/tests/test_origin_retirement.py",
                "apps/api/tests/test_thread_creation.py",
                "-q",
                "-W",
                "error",
            ],
            cwd=ROOT,
            env=test_environment,
            text=True,
            capture_output=True,
            timeout=300,
        )
        output = (result.stdout + result.stderr).replace(password, "[REDACTED]")
        if result.returncode:
            raise RuntimeError(
                f"Conversations integration tests failed: {output[-4000:]}"
            )
        print(output.strip())
        print("PASS: focused Conversations operations on fresh PostgreSQL 18.6")
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        subprocess.TimeoutExpired,
        RuntimeError,
    ) as error:
        print(f"Conversations database check failed: {error}", file=sys.stderr)
        return 1
    finally:
        if container is not None:
            cleanup = subprocess.run(
                ["docker", "rm", "--force", container],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if cleanup.returncode:
                raise RuntimeError("could not remove the owned disposable container")


if __name__ == "__main__":
    raise SystemExit(main())
