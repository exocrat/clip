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
IDENTITY_GUARD = "20261023173439"
OTP_HEAD = "20261023192856"
IDENTITY_HEAD = "20261023202807"


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

        Private baseline directories exercise historical and current upgrades;
        rollback removes only the latest applied migration in this fresh target.
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

    def migrate_guard(through=IDENTITY_GUARD):
        """Exercise the original Step3 upgrade with exactly its historical chain."""
        with tempfile.TemporaryDirectory(prefix="clip-identity-guard-") as name:
            directory = Path(name)
            for source in (ROOT / "database/migrations").glob("*.sql"):
                if source.name.split("_")[0] <= through:
                    shutil.copyfile(source, directory / source.name)
            migrate(directory)

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
            "identity-otp-smoke.sql",
            "identity-session-smoke.sql",
        ):
            sql((ROOT / "database/tests" / filename).read_text())
        if (
            sql(
                "SELECT count(*) FROM pg_tables WHERE schemaname IN ('identity','listings','search','conversations')"
            )
            != "30"
        ):
            raise RuntimeError("Expected 30 domain tables")
        # The only rollback is against this invocation's fresh disposable target.
        # Seed older-schema rows, reject incompatible data atomically, then verify
        # upgrade/down/reapply preserve every fixture value and original guard.
        # Empty OTP rollback preserves all older data; occupied rollback is
        # separately checked by the actual transactional service suite.
        migrate(rollback=True)
        if sql("SELECT max(version) FROM public.schema_migrations") != OTP_HEAD:
            raise RuntimeError("Session rollback did not restore OTP head")
        migrate(rollback=True)
        if sql("SELECT max(version) FROM public.schema_migrations") != IDENTITY_GUARD:
            raise RuntimeError("OTP rollback did not restore the Identity guard head")
        migrate(rollback=True)
        migrations = sorted((ROOT / "database/migrations").glob("*.sql"))
        with tempfile.TemporaryDirectory(prefix="clip-identity-baseline-") as name:
            baseline = Path(name)
            for source in migrations:
                if source.name.split("_")[0] < IDENTITY_GUARD:
                    shutil.copyfile(source, baseline / source.name)
            migrate(baseline)
        sql((ROOT / "database/tests/identity-upgrade-seed.sql").read_text())
        sql(
            "UPDATE identity.users SET display_name = repeat('x', 81) "
            "WHERE id = 'e2300000-0000-4000-8000-000000000001'"
        )
        try:
            migrate_guard()
        except RuntimeError as error:
            if "users_display_name_length" not in str(error):
                raise
        else:
            raise RuntimeError("Identity migration silently accepted incompatible data")
        if (
            sql(
                "SELECT count(*) FROM public.schema_migrations WHERE version = '"
                + IDENTITY_GUARD
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
        migrate_guard()
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
        migrate_guard()
        migrate_guard()
        sql((ROOT / "database/tests/identity-upgrade-check.sql").read_text())
        for filename in (
            "schema-smoke.sql",
            "retired-origin-smoke.sql",
            "identity-schema-smoke.sql",
        ):
            sql((ROOT / "database/tests" / filename).read_text())
        # Legacy verifier rows survive both OTP directions without invented
        # encryption/key references; the new service fails closed on adoption.
        sql(
            "INSERT INTO identity.otp_challenges "
            "(id,target_lookup_digest,verifier,purpose,expires_at) VALUES "
            "('e2300000-0000-4000-8000-000000000099',decode('11','hex'),decode('22','hex'),"
            "'initial_verification',CURRENT_TIMESTAMP + INTERVAL '10 minutes')"
        )
        migrate_guard(OTP_HEAD)
        if (
            sql(
                "SELECT key_version IS NULL AND encrypted_target IS NULL FROM identity.otp_challenges "
                "WHERE id='e2300000-0000-4000-8000-000000000099'"
            )
            != "t"
        ):
            raise RuntimeError("OTP upgrade invented legacy key/encryption data")
        migrate(rollback=True)
        if (
            sql(
                "SELECT encode(verifier,'hex') FROM identity.otp_challenges "
                "WHERE id='e2300000-0000-4000-8000-000000000099'"
            )
            != "22"
        ):
            raise RuntimeError("OTP rollback changed a legacy verifier")
        migrate_guard(OTP_HEAD)
        sql(
            "INSERT INTO identity.sessions(id,user_id,token_digest,expires_at) VALUES "
            "('e2700000-0000-4000-8000-000000000099','e2300000-0000-4000-8000-000000000001',"
            "decode('33','hex'),CURRENT_TIMESTAMP+INTERVAL '8 days')"
        )
        migrate()
        if (
            sql(
                "SELECT last_seen_at IS NULL FROM identity.sessions WHERE id='e2700000-0000-4000-8000-000000000099'"
            )
            != "t"
        ):
            raise RuntimeError("Session migration invented legacy activity")
        migrate(rollback=True)
        if (
            sql(
                "SELECT encode(token_digest,'hex') FROM identity.sessions WHERE id='e2700000-0000-4000-8000-000000000099'"
            )
            != "33"
        ):
            raise RuntimeError("Session rollback rewrote legacy digest")
        migrate()
        migrate()
        sql((ROOT / "database/tests/identity-upgrade-check.sql").read_text())
        sql((ROOT / "database/tests/identity-otp-smoke.sql").read_text())
        sql((ROOT / "database/tests/identity-session-smoke.sql").read_text())
        print(
            "PASS: PostgreSQL 18.6; clean/repeat migrations, five smoke suites; "
            "Identity incompatible-upgrade atomicity, data-preserving guard/OTP/session upgrade/down/reapply"
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
