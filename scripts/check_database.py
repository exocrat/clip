"""Verify migrations/smoke checks in a new, disposable local PostgreSQL container.

No target arguments, host ports, persistent volumes or caller database settings
are accepted. Only this invocation's container is removed, even after failure.
Requires local Docker; pinned images may be downloaded from public registries.
"""

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = "postgres:18.6-bookworm"
DBMATE_IMAGE = "ghcr.io/amacneil/dbmate:2.36.0"


def main():
    """Create an isolated database, verify real SQL, then remove owned resources."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    env = {key: os.environ[key] for key in ("HOME", "PATH")}
    password = secrets.token_hex(24)
    container = None

    def run(args, *, stdin=None, extra=None):
        """Bound subprocess execution and redact the ephemeral password on failure."""
        result = subprocess.run(
            args,
            cwd=ROOT,
            env=env | (extra or {}),
            input=stdin,
            text=True,
            capture_output=True,
            timeout=180,
        )
        if result.returncode:
            output = (result.stdout + result.stderr).replace(password, "[REDACTED]")
            # Identify the failed tool without echoing its arguments/environment.
            tool = (
                "psql"
                if "psql" in args
                else "dbmate" if DBMATE_IMAGE in args else "Docker"
            )
            raise RuntimeError(f"{tool} exited {result.returncode}: {output[-4000:]}")
        return result.stdout.strip()

    # Pin a local Unix-socket context, never an ambient remote Docker endpoint.
    context = run(["docker", "context", "show"])
    endpoint = json.loads(run(["docker", "context", "inspect", context]))[0][
        "Endpoints"
    ]["docker"]["Host"]
    if not endpoint.startswith("unix://"):
        raise RuntimeError("A local Unix-socket Docker context is required")
    docker = ["docker", "--context", context]

    def sql(statement):
        """Use authenticated loopback TCP inside only the fresh test container."""
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
                "clip_ci",
                "-d",
                "clip_test_ci",
                "-v",
                "ON_ERROR_STOP=1",
            ],
            stdin=statement,
            extra={"PGPASSWORD": password},
        )

    def migrate(operation="migrate"):
        """Run a locked-tool migration operation without implicit .env input."""
        command = [
            "--env-file",
            "/dev/null",
            "--migrations-dir",
            "/db/migrations",
            "--no-dump-schema",
            operation,
        ]
        if operation == "migrate":
            command.append("--strict")
        run(
            docker
            + [
                "run",
                "--rm",
                # Match the source owner so private (umask 077) clones work
                # without granting DAC override capabilities to the tool.
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
            ]
            + command,
            extra={
                "DATABASE_URL": f"postgres://clip_ci:{password}@127.0.0.1:5432/clip_test_ci?sslmode=disable"
            },
        )

    try:
        # No names to collide with existing services, no ports or named volumes.
        container = run(
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
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                "POSTGRES_USER=clip_ci",
                "--env",
                "POSTGRES_DB=clip_test_ci",
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
        for attempt in range(60):
            try:
                if sql("SELECT 1") == "1":
                    break
            except RuntimeError:
                if attempt == 59:
                    raise
            time.sleep(1)
        if sql("SHOW server_version_num") != "180006":
            raise RuntimeError("Expected PostgreSQL 18.6")
        if (
            sql(
                "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')"
            )
            != "0"
        ):
            raise RuntimeError("Expected an empty database")
        migrate()
        expected = sorted(
            path.name.split("_")[0]
            for path in (ROOT / "database/migrations").glob("*.sql")
        )
        actual = sql(
            "SELECT version FROM public.schema_migrations ORDER BY version"
        ).splitlines()
        if not expected or actual != expected or actual[-1] != "20261021101000":
            raise RuntimeError("Migration history differs from the expected head")
        migrate()
        for filename in ("schema-smoke.sql", "retired-origin-smoke.sql"):
            sql((ROOT / "database/tests" / filename).read_text())
        if (
            sql(
                "SELECT count(*) FROM pg_tables WHERE schemaname IN ('identity','listings','search','conversations')"
            )
            != "24"
        ):
            raise RuntimeError("Expected 24 domain tables")
        migrate("rollback")
        if sql("SELECT max(version) FROM public.schema_migrations") != "20261018152702":
            raise RuntimeError("Rollback did not return to the prior migration head")
        if sql("SELECT to_regclass('conversations.origin_retirement_operations') IS NULL") != "t":
            raise RuntimeError("Rollback left the retirement-operation table behind")
        if (
            sql(
                "SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid "
                "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE a.attname IN "
                "('retirement_pending_operation_id','retirement_pending_cutoff_utc',"
                "'participant_writes_blocked_at') AND NOT a.attisdropped "
                "AND n.nspname IN ('listings','search','conversations')"
            )
            != "0"
        ):
            raise RuntimeError("Rollback left retirement columns behind")
        migrate()
        if sql("SELECT max(version) FROM public.schema_migrations") != "20261021101000":
            raise RuntimeError("Reapply did not restore the current migration head")
        for filename in ("schema-smoke.sql", "retired-origin-smoke.sql"):
            sql((ROOT / "database/tests" / filename).read_text())
        print(
            "PASS: PostgreSQL 18.6; clean migrations, exact head, repeat apply, both smoke suites, "
            "latest down/up and retirement-marker checks"
        )
    finally:
        if container:
            run(docker + ["rm", "--force", container])


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        import sys

        print(f"Database checks failed: {error}", file=sys.stderr)
        raise SystemExit(1)
    except subprocess.TimeoutExpired, OSError, ValueError:
        # Do not emit command arguments/environment from unexpected failures.
        import sys

        print(
            "Database checks failed; inspect pinned images, Docker availability or migration/schema changes.",
            file=sys.stderr,
        )
        raise SystemExit(1)
