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
import shutil
import subprocess
import time
import tempfile

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = "postgres:18.6-bookworm"
DBMATE_IMAGE = "ghcr.io/amacneil/dbmate:2.36.0"
IDENTITY_HEAD = "20261023173439"


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

    def migrate(directory=None, *, rollback=False):
        """Apply/undo only disposable-target migrations, never ambient .env inputs.

        A private baseline directory exercises upgrade from previously applied
        migrations; rollback removes only the new Identity guard migration.
        """
        directory = directory or ROOT / "database/migrations"
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
                f"type=bind,src={directory},dst=/db/migrations,readonly",
                DBMATE_IMAGE,
                "--env-file",
                "/dev/null",
                "--migrations-dir",
                "/db/migrations",
                "--no-dump-schema",
                *(["rollback"] if rollback else ["migrate", "--strict"]),
            ],
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
        if not expected or actual != expected or actual[-1] != IDENTITY_HEAD:
            raise RuntimeError("Migration history differs from the expected head")
        migrate()
        for filename in (
            "schema-smoke.sql",
            "retired-origin-smoke.sql",
            "identity-schema-smoke.sql",
        ):
            sql((ROOT / "database/tests" / filename).read_text())
        if (
            sql(
                "SELECT count(*) FROM pg_tables WHERE schemaname IN ('identity','listings','search','conversations')"
            )
            != "23"
        ):
            raise RuntimeError("Expected 23 domain tables")
        # The only rollback is against this invocation's fresh disposable target.
        # Seed older-schema rows, reject incompatible data atomically, then verify
        # upgrade/down/reapply preserve every fixture value and original guard.
        migrate(rollback=True)
        migrations = sorted((ROOT / "database/migrations").glob("*.sql"))
        with tempfile.TemporaryDirectory(prefix="clip-identity-baseline-") as name:
            baseline = Path(name)
            for source in migrations:
                if not source.name.startswith(IDENTITY_HEAD + "_"):
                    shutil.copyfile(source, baseline / source.name)
            migrate(baseline)
        sql((ROOT / "database/tests/identity-upgrade-seed.sql").read_text())
        sql(
            "UPDATE identity.users SET display_name = repeat('x', 81) "
            "WHERE id = 'e2300000-0000-4000-8000-000000000001'"
        )
        try:
            migrate()
        except RuntimeError as error:
            if "users_display_name_length" not in str(error):
                raise
        else:
            raise RuntimeError("Identity migration silently accepted incompatible data")
        if (
            sql(
                "SELECT count(*) FROM public.schema_migrations WHERE version = '"
                + IDENTITY_HEAD
                + "'"
            )
            != "0"
        ):
            raise RuntimeError("Failed Identity migration left an applied version")
        if (
            sql(
                "SELECT count(*) FROM pg_constraint WHERE conname IN "
                "('users_display_name_length', 'users_revocation_consistency', 'contacts_value_lengths')"
            )
            != "0"
        ):
            raise RuntimeError("Failed Identity migration left partial constraints")
        if (
            sql(
                "SELECT char_length(display_name) FROM identity.users "
                "WHERE id = 'e2300000-0000-4000-8000-000000000001'"
            )
            != "81"
        ):
            raise RuntimeError("Failed Identity migration rewrote fixture data")
        sql(
            "UPDATE identity.users SET display_name = 'Identity upgrade fixture' "
            "WHERE id = 'e2300000-0000-4000-8000-000000000001'"
        )
        migrate()
        sql((ROOT / "database/tests/identity-upgrade-check.sql").read_text())
        sql((ROOT / "database/tests/identity-schema-smoke.sql").read_text())
        migrate(rollback=True)
        sql((ROOT / "database/tests/identity-upgrade-check.sql").read_text())
        if (
            sql(
                "SELECT count(*) FROM pg_trigger WHERE tgname = 'external_identities_history'"
            )
            != "0"
        ):
            raise RuntimeError("Identity rollback left its provider-mapping trigger")
        migrate()
        migrate()
        sql((ROOT / "database/tests/identity-upgrade-check.sql").read_text())
        for filename in (
            "schema-smoke.sql",
            "retired-origin-smoke.sql",
            "identity-schema-smoke.sql",
        ):
            sql((ROOT / "database/tests" / filename).read_text())
        print(
            "PASS: PostgreSQL 18.6; clean/repeat migrations, three smoke suites; "
            "Identity incompatible-upgrade atomicity and data-preserving upgrade/down/reapply"
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
