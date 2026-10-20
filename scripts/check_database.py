"""Verify migrations/smoke checks in a new, disposable local PostgreSQL container.

No database target, host port, persistent data volume or caller database setting
is accepted. ``--listings-store`` adds one adapter check using a private temporary
Unix socket. Only this invocation's container is removed, even after failure.
Requires local Docker; pinned images may be downloaded from public registries.
"""

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = "postgres:18.6-bookworm"
DBMATE_IMAGE = "ghcr.io/amacneil/dbmate:2.36.0"


def main():
    """Create an isolated database, verify real SQL, then remove owned resources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--listings-store",
        action="store_true",
        help="also exercise the Listings adapter against this disposable database",
    )
    arguments = parser.parse_args()
    env = {key: os.environ[key] for key in ("HOME", "PATH")}
    password = secrets.token_hex(24)
    container = None
    socket_temp = None
    socket_directory = None
    phase = "initialization"

    def run(args, *, stdin=None, extra=None, expect_failure=False):
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
            if expect_failure:
                return result.returncode, output[-4000:]
            # Identify the failed tool without echoing its arguments/environment.
            tool = (
                "psql"
                if "psql" in args
                else (
                    "dbmate"
                    if DBMATE_IMAGE in args
                    else "pytest" if "pytest" in args else "Docker"
                )
            )
            raise RuntimeError(f"{tool} exited {result.returncode}: {output[-4000:]}")
        return result.stdout.strip()

    # Pin a local Unix-socket context, never an ambient remote Docker endpoint.
    phase = "local Docker context validation"
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

    def migrate(operation="migrate", *, expect_failure=False):
        """Run pinned dbmate without implicit .env input against only this container."""
        arguments = docker + [
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
            "--env-file",
            "/dev/null",
            "--migrations-dir",
            "/db/migrations",
            "--no-dump-schema",
            operation,
        ]
        if operation == "migrate":
            arguments.append("--strict")
        result = run(
            arguments,
            extra={
                "DATABASE_URL": f"postgres://clip_ci:{password}@127.0.0.1:5432/clip_test_ci?sslmode=disable"
            },
            expect_failure=expect_failure,
        )
        if expect_failure:
            expected_message = "Cannot roll back retirement migration while operation results or markers exist"
            if not isinstance(result, tuple):
                raise RuntimeError("Expected rollback to refuse recorded retirement state")
            if expected_message not in result[1]:
                raise RuntimeError("Rollback failed for a reason other than retained retirement state")
        return result

    try:
        # No names to collide with existing services, no ports or named volumes.
        container_args = docker + [
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
        ]
        if arguments.listings_store:
            socket_temp = tempfile.TemporaryDirectory(
                prefix="clip-listings-test-", dir="/tmp"
            )
            socket_directory = Path(socket_temp.name) / "pgsocket"
            socket_directory.mkdir()
            # PostgreSQL runs as its own unprivileged container user. The short-
            # lived parent remains private; only this socket directory is shared.
            socket_directory.chmod(0o777)
            container_args.extend(
                [
                    "--mount",
                    f"type=bind,src={socket_directory},dst=/tmp/clip-pg-socket",
                ]
            )
        container_args.extend(
            [
                POSTGRES_IMAGE,
                "postgres",
                "-c",
                "timezone=UTC",
                "-c",
                "log_timezone=UTC",
            ]
        )
        if socket_directory is not None:
            container_args.extend(
                [
                    "-c",
                    "unix_socket_directories=/var/run/postgresql,/tmp/clip-pg-socket",
                ]
            )
        phase = "starting the disposable PostgreSQL container"
        container = run(container_args, extra={"POSTGRES_PASSWORD": password})
        phase = "waiting for PostgreSQL startup"
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
        phase = "applying migrations"
        migrate()
        expected = sorted(
            path.name.split("_")[0]
            for path in (ROOT / "database/migrations").glob("*.sql")
        )
        actual = sql(
            "SELECT version FROM public.schema_migrations ORDER BY version"
        ).splitlines()
        if not expected or actual != expected or actual[-1] != "20261020142319":
            raise RuntimeError("Migration history differs from the expected head")
        migrate()
        for filename in ("schema-smoke.sql", "retired-origin-smoke.sql"):
            sql((ROOT / "database/tests" / filename).read_text())
        if (
            sql(
                "SELECT count(*) FROM pg_tables WHERE schemaname IN ('identity','listings','search','conversations')"
            )
            != "26"
        ):
            raise RuntimeError("Expected 26 domain tables")
        phase = "rolling back and reapplying migrations"
        sql("""
            INSERT INTO conversations.origin_retirement_operations
                (operation_id, origin_kind, origin_id, cutoff_utc, outcome, marked_count)
            VALUES ('00000000-0000-4000-8000-000000000001', 'listing',
                '00000000-0000-4000-8000-000000000002', clock_timestamp(), 'marked', 0)
        """)
        migrate("rollback", expect_failure=True)
        if (
            sql("SELECT count(*) FROM conversations.origin_retirement_operations") != "1"
            or sql("SELECT max(version) FROM public.schema_migrations") != "20261020142319"
        ):
            raise RuntimeError("Rollback changed recorded retirement state or migration head")
        sql("DELETE FROM conversations.origin_retirement_operations WHERE operation_id = '00000000-0000-4000-8000-000000000001'")
        for _ in expected:
            migrate("rollback")
        if sql("SELECT count(*) FROM public.schema_migrations") != "0":
            raise RuntimeError("Expected rollback to remove every applied migration")
        if (
            sql(
                "SELECT count(*) FROM pg_namespace WHERE nspname IN ('identity','listings','search','conversations')"
            )
            != "0"
        ):
            raise RuntimeError("Expected rollback to remove every domain namespace")
        migrate()
        reapplied = sql(
            "SELECT version FROM public.schema_migrations ORDER BY version"
        ).splitlines()
        if reapplied != expected:
            raise RuntimeError("Migration history differs after clean reapply")
        for filename in ("schema-smoke.sql", "retired-origin-smoke.sql"):
            sql((ROOT / "database/tests" / filename).read_text())
        if arguments.listings_store:
            phase = "running the Listings adapter workflow"
            host = quote(str(socket_directory), safe="")
            test_database_url = (
                f"postgresql://clip_ci:{password}@/clip_test_ci?"
                f"host={host}&sslmode=disable"
            )
            output = run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "apps/api/tests/domains/listings/test_postgres_store.py",
                    "-q",
                    "-W",
                    "error",
                ],
                extra={"LISTINGS_TEST_DATABASE_URL": test_database_url},
            )
            if output:
                print(output)
            print(
                "PASS: Listings adapter workflow used the disposable PostgreSQL database"
            )
            sample = sql("""
                SELECT json_build_object(
                    'listing_id', listing.id,
                    'title', listing.title,
                    'availability', listing.availability,
                    'revision', listing.revision,
                    'selected_buyer_id', listing.selected_buyer_id,
                    'selected_conversation_id', listing.selected_conversation_id,
                    'live_image_count', (
                        SELECT count(*) FROM listings.images AS image
                        WHERE image.listing_id = listing.id AND image.retired_at IS NULL
                    ),
                    'create_receipt_count', (
                        SELECT count(*) FROM listings.create_command_results AS receipt
                        WHERE receipt.listing_id = listing.id
                    ),
                    'owner_receipt_count', (
                        SELECT count(*) FROM listings.owner_command_results AS receipt
                        WHERE receipt.listing_id = listing.id
                    )
                )::text
                FROM listings.sale_listings AS listing
                WHERE listing.title = 'Revised synthetic textbook'
                """)
            if not sample:
                raise RuntimeError(
                    "The Listings workflow did not leave its expected test row"
                )
            print(f"POSTGRES_LISTING_SAMPLE_ROW {sample}")
        print(
            "PASS: PostgreSQL 18.6; clean apply/head, repeat apply, both smokes, full rollback and clean reapply"
        )
    except (subprocess.TimeoutExpired, OSError, ValueError) as error:
        raise RuntimeError(
            f"Database checks failed during {phase} ({type(error).__name__})"
        ) from None
    finally:
        try:
            if container:
                phase = "removing the disposable PostgreSQL container"
                run(docker + ["rm", "--force", container])
        finally:
            if socket_temp is not None:
                phase = "removing the temporary Unix socket directory"
                socket_temp.cleanup()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        import sys

        print(f"Database checks failed: {error}", file=sys.stderr)
        raise SystemExit(1)
    except (subprocess.TimeoutExpired, OSError, ValueError) as error:
        # Do not emit command arguments/environment from unexpected failures.
        import sys

        print(
            f"Database checks failed ({type(error).__name__}); "
            "inspect pinned images, Docker availability "
            "or migration/schema changes.",
            file=sys.stderr,
        )
        raise SystemExit(1)
