"""Explicit operator migration tools; never imported by application startup.

Only approved callers supply credentials and connections. Live use needs a
reviewed manifest/image and separate cloud/SQL approval, not merely this API.
"""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Callable
from urllib.parse import urlencode
from uuid import uuid4

from psycopg import Rollback, sql
from pydantic import SecretStr

from app.core.config import ConfigurationError
from app.domains.identity.database_setup import LOGGING
from app.domains.identity.temporary_challenges import Database

HOST = "clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com"
PROBE = "clip_test_identity_logging_probe"
SCHEMAS = ("identity", "listings", "search", "conversations")


@dataclass(frozen=True)
class MigrationTarget:
    """Fixed live tunnel or explicitly isolated TLS fixture, never ambient DSN."""

    port: int
    isolated: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.port) is not int
            or not 1 <= self.port <= 65535
            or (not self.isolated and self.port != 15432)
        ):
            raise ValueError("Invalid migration target")

    @property
    def host(self) -> str:
        return "clip-identity-migration.invalid" if self.isolated else HOST

    @property
    def database(self) -> str:
        return "clip_test_identity" if self.isolated else "clip_test"

    @property
    def admin(self) -> str:
        return "clip_identity_ci" if self.isolated else "clip_test_admin"


def _target(c: Database, target: MigrationTarget) -> None:
    if c.execute("SELECT current_database(),current_user,session_user").fetchone() != (
        target.database,
        target.admin,
        target.admin,
    ):
        raise ValueError


def validate_manifest(
    directory: Path, manifest: Path, image: str, target: MigrationTarget
) -> list[str]:
    """Pin the accepted-main 23-file chain; refuse edited SQL and unreviewed live images."""
    if not re.fullmatch(r"ghcr.io/amacneil/dbmate@sha256:[0-9a-f]{64}", image):
        raise ValueError
    row = json.loads(manifest.read_text())
    if (
        row["tool"] != "dbmate 2.36.0"
        or row["head"] != "20261027112205"
        or row["migration_count"] != 23
    ):
        raise ValueError
    if not target.isolated and (
        row.get("image_digest_review_pending") is not False
        or row.get("image_digest") != image
    ):
        raise ValueError
    files = sorted(directory.glob("*.sql"))
    expected = row["migrations"]
    if len(files) != 23 or len(expected) != 23 or any(p.is_symlink() for p in files):
        raise ValueError
    versions = []
    for path, item in zip(files, expected, strict=True):
        if (
            path.name != Path(item["path"]).name
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError
        version = path.name.split("_")[0]
        if version != item["version"]:
            raise ValueError
        versions.append(version)
    if versions != sorted(set(versions)) or versions[-1] != row["head"]:
        raise ValueError
    return versions


def _baseline(c: Database, target: MigrationTarget, versions: list[str]) -> None:
    """Permit only a fresh four-namespace baseline or this exact complete chain.

    Never auto-adopt manual schemas or resume an applied prefix after a failure.
    Recorded 17-file targets are never adopted or automatically upgraded here.
    Hold the owning wrapper's lock separately from the SQL per-migration key.
    """
    _target(c, target)
    namespaces = {
        r[0]
        for r in c.execute(
            "SELECT nspname FROM pg_namespace WHERE nspname=ANY(%s)", (list(SCHEMAS),)
        )
    }
    exists = c.execute(
        "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
    ).fetchone()
    if exists == (False,):
        if namespaces:
            raise ValueError
    elif exists == (True,):
        actual = [
            r[0]
            for r in c.execute(
                "SELECT version FROM public.schema_migrations ORDER BY version"
            )
        ]
        if actual != versions or namespaces != set(SCHEMAS):
            raise ValueError
        inventory = (
            c.execute(
                "SELECT count(*) FROM pg_tables WHERE schemaname=ANY(%s)",
                (list(SCHEMAS),),
            ).fetchone(),
            c.execute(
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=ANY(%s)",
                (list(SCHEMAS),),
            ).fetchone(),
            c.execute(
                "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal AND n.nspname=ANY(%s)",
                (list(SCHEMAS),),
            ).fetchone(),
        )
        if inventory != ((40,), (36,), (46,)):
            raise ValueError
    else:
        raise ValueError


def run_migrations(
    connect: Callable[[], Database],
    password: SecretStr,
    target: MigrationTarget,
    *,
    directory: Path,
    manifest: Path,
    ca: Path,
    image: str,
) -> None:
    """Apply only the pinned chain with a private stdin password and verified TLS.

    Docker config stores only public URI/options, never the credential. A fixed
    shell exports PGPASSWORD after reading stdin; no interpolation or passfile.
    Raw client output stays in memory and is never printed. Failure preserves
    committed migration prefixes; no down/reset/retry. Linux host networking only.
    """
    container = "clip-id01-migrate-" + uuid4().hex
    attempted: list[str] = []
    env = {k: os.environ[k] for k in ("HOME", "PATH")}
    try:
        versions = validate_manifest(directory, manifest, image, target)
        secret = password.get_secret_value()
        if (
            not secret
            or len(secret) > 256
            or any(ch in secret for ch in "\r\n\0")
            or not secret.isascii()
        ):
            raise ValueError
        if (
            not ca.is_file()
            or ca.is_symlink()
            or not directory.is_dir()
            or directory.is_symlink()
        ):
            raise ValueError
        context = subprocess.run(
            ["docker", "context", "show"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
            check=True,
        ).stdout.strip()
        details = subprocess.run(
            ["docker", "context", "inspect", context],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
            check=True,
        )
        if not json.loads(details.stdout)[0]["Endpoints"]["docker"]["Host"].startswith(
            "unix://"
        ):
            raise ValueError
        docker = ["docker", "--context", context]
        version_container = container + "-version"
        attempted.append(version_container)
        version = subprocess.run(
            docker
            + [
                "run",
                "--rm",
                "--name",
                version_container,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                image,
                "--version",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=True,
        ).stdout.strip()
        if version != "dbmate version 2.36.0":
            raise ValueError
        uri = (
            "postgresql://"
            + target.admin
            + "@"
            + target.host
            + ":"
            + str(target.port)
            + "/"
            + target.database
            + "?"
            + urlencode(
                {
                    "sslmode": "verify-full",
                    "sslrootcert": "/run/clip-ca.pem",
                    "connect_timeout": "3",
                }
            )
        )
        command = docker + [
            "run",
            "--rm",
            "--name",
            container,
            "--interactive",
            "--network",
            "host",
            "--add-host",
            target.host + ":127.0.0.1",
            "--read-only",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--log-driver",
            "none",
            "--env",
            "DATABASE_URL",
            "--env",
            "PGOPTIONS",
            "--mount",
            f"type=bind,src={directory.resolve()},dst=/db/migrations,readonly",
            "--mount",
            f"type=bind,src={ca.resolve()},dst=/run/clip-ca.pem,readonly",
            "--entrypoint",
            "/bin/sh",
            image,
            "-c",
            "IFS= read -r PGPASSWORD || exit 1; export PGPASSWORD; exec /usr/local/bin/dbmate --env-file /dev/null --migrations-dir /db/migrations --no-dump-schema migrate --strict",
        ]
        with connect() as c:
            c.execute("SET statement_timeout='5s'")
            c.execute("SET lock_timeout='3s'")
            if c.execute("SELECT pg_try_advisory_lock(1129072976,12)").fetchone() != (
                True,
            ):
                raise ValueError
            _baseline(c, target, versions)
            attempted.append(container)
            subprocess.run(
                command,
                input=secret + "\n",
                capture_output=True,
                text=True,
                env=env
                | {
                    "DATABASE_URL": uri,
                    "PGOPTIONS": "-c statement_timeout=30000 -c lock_timeout=10000",
                },
                timeout=300,
                check=True,
            )
            validate_manifest(directory, manifest, image, target)
            if c.execute(
                "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
            ).fetchone() != (True,):
                raise ValueError
            _baseline(c, target, versions)
    except Exception:
        raise ConfigurationError(
            "Identity migration run failed; preserve state and inspect metadata"
        ) from None
    finally:
        # Both the version check and migration client can outlive a timed-out
        # Docker CLI. Attempt cleanup of every owned name, then report failures.
        cleanup_failed = False
        for owned in reversed(attempted):
            try:
                cleanup = subprocess.run(
                    ["docker", "--context", context, "rm", "--force", owned],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=15,
                    check=False,
                )
                if cleanup.returncode and "No such container" not in cleanup.stderr:
                    cleanup_failed = True
            except Exception:
                cleanup_failed = True
        if cleanup_failed:
            raise ConfigurationError(
                "Owned migration container cleanup unconfirmed"
            ) from None


@dataclass(frozen=True)
class LoggingProbe:
    """Safe outcome; completion is separate from verified rollback/baseline."""

    completed: bool
    rollback_verified: bool
    failed_phase: str | None


def probe_logging(
    connect: Callable[[], Database], target: MigrationTarget
) -> LoggingProbe:
    """Try local/default settings on a passwordless NOLOGIN role, always rollback.

    No real password, membership/grant, global parameter or application-data SQL.
    A second connection verifies role absence and unchanged effective defaults.
    Probe collisions reject before changes. RDS permissions must be tested live
    only under explicit SQL approval; catalog permission flags alone are not proof.
    """
    phase = "connection"
    baseline = None
    collision = False
    completed = False
    failure = None
    try:
        with connect() as c:
            phase = "target"
            _target(c, target)
            phase = "baseline"
            baseline = {
                name: c.execute("SELECT current_setting(%s)", (name,)).fetchone()
                for name in LOGGING
            }
            phase = "collision"
            collision = (
                c.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=%s", (PROBE,)
                ).fetchone()
                is not None
            )
            if collision:
                raise ValueError
            with c.transaction():
                c.execute("SET LOCAL statement_timeout='5s'")
                c.execute("SET LOCAL lock_timeout='3s'")
                phase = "session settings"
                for name, value in LOGGING.items():
                    c.execute("SELECT set_config(%s,%s,true)", (name, value))
                phase = "probe role"
                c.execute(
                    sql.SQL(
                        "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
                    ).format(sql.Identifier(PROBE))
                )
                phase = "role defaults"
                for name, value in LOGGING.items():
                    c.execute(
                        sql.SQL("ALTER ROLE {} SET {} = {}").format(
                            sql.Identifier(PROBE),
                            sql.Identifier(name),
                            sql.Literal(value),
                        )
                    )
                phase = "settings verification"
                for name, value in LOGGING.items():
                    if c.execute("SELECT current_setting(%s)", (name,)).fetchone() != (
                        value,
                    ):
                        raise ValueError
                settings = c.execute(
                    "SELECT setconfig FROM pg_db_role_setting WHERE setrole=(SELECT oid FROM pg_roles WHERE rolname=%s) AND setdatabase=0",
                    (PROBE,),
                ).fetchone()
                if settings is None or set(settings[0]) != {
                    name + "=" + value for name, value in LOGGING.items()
                }:
                    raise ValueError
                completed = True
                raise Rollback()
    except Exception:
        failure = phase
    verified = False
    if baseline is not None and not collision:
        try:
            with connect() as c, c.transaction():
                c.execute("SET TRANSACTION READ ONLY")
                c.execute("SET LOCAL statement_timeout='5s'")
                _target(c, target)
                verified = c.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=%s", (PROBE,)
                ).fetchone() is None and all(
                    c.execute("SELECT current_setting(%s)", (name,)).fetchone() == row
                    for name, row in baseline.items()
                )
        except Exception:
            verified = False
    return LoggingProbe(completed, verified, failure)
