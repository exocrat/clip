"""Guarded CN-03 migration candidate; importing this module makes no connection.

Only an explicitly approved operator may call this with an already established
connection. It neither reads credentials nor starts AWS resources, and it never
automatically retries or repairs a different migration baseline.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/environment/cn-03-candidate-migration-manifest.json"
MANIFEST_SHA256 = "39759241f0e0e7188c0b16e4ee1c767c9f48de2e19cbc0b54f6c63f672d76a77"
GRANT = ROOT / "database/roles/identity-notification-runtime.sql.proposed"
GRANT_SHA256 = "9396226df6df7703646d4ac04c649e51d9e52c679c3951b60c54f0cadef3a547"
HOST = "clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com"


class UpgradeRefused(Exception):
    """Fixed, sanitized diagnostic; never expose SQL or credentials."""


def _files():
    """Verify every candidate migration and the additive Identity grant."""
    if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != MANIFEST_SHA256:
        raise ValueError
    data = json.loads(MANIFEST.read_text())
    paths = sorted((ROOT / "database/migrations").glob("*.sql"))
    entries = data["migrations"]
    if len(paths) != 32 or data["migration_count"] != 32 or len(entries) != 32:
        raise ValueError
    for path, entry in zip(paths, entries, strict=True):
        if (
            path.is_symlink()
            or entry["path"] != str(path.relative_to(ROOT))
            or entry["version"] != path.name.split("_")[0]
            or entry["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()
        ):
            raise ValueError
    versions = [entry["version"] for entry in entries]
    if versions != sorted(set(versions)) or versions[22] != "20261027112205":
        raise ValueError
    if hashlib.sha256(GRANT.read_bytes()).hexdigest() != GRANT_SHA256:
        raise ValueError
    return paths, versions


def upgrade(connection, *, isolated: bool, approved_manifest: str, approved_grant: str):
    """Atomically apply the reviewed nine-file suffix and one Identity grant.

    Refuse unexpected target, role, TLS, hashes or ledger. All migrations and
    grant commit together; failure rolls back when outcome is known. A lost
    connection at commit requires manual inspection, never automatic retry.
    The isolated mode only permits the disposable local test database.
    """
    try:
        if approved_manifest != MANIFEST_SHA256 or approved_grant != GRANT_SHA256:
            raise ValueError
        paths, versions = _files()
        expected = (
            ("clip_test_identity", "clip_identity_ci")
            if isolated
            else ("clip_test", "clip_test_admin")
        )
        with connection.transaction():
            connection.execute("SET LOCAL lock_timeout='10s'")
            connection.execute("SET LOCAL statement_timeout='60s'")
            connection.execute("SELECT pg_advisory_xact_lock(1129072976, 12)")
            current = connection.execute(
                "SELECT current_database(), current_user, session_user"
            ).fetchone()
            if current != (expected[0], expected[1], expected[1]):
                raise ValueError
            if isolated:
                if not connection.info.host.startswith("/"):
                    raise ValueError
            elif (
                connection.info.host != HOST
                or connection.info.port != 15432
                or not connection.pgconn.ssl_in_use
                or connection.info.get_parameters().get("sslmode") != "verify-full"
            ):
                raise ValueError
            actual = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM public.schema_migrations ORDER BY version"
                )
            ]
            if actual != versions[:23]:
                raise ValueError
            if connection.execute(
                "SELECT to_regclass('identity.notification_destinations') IS NULL AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname='clip_test_identity_app')"
            ).fetchone() != (True,):
                raise ValueError
            for path, version in zip(paths[23:], versions[23:], strict=True):
                raw = path.read_text()
                up = raw.split("-- migrate:up", 1)[1].split("-- migrate:down", 1)[0]
                connection.execute(up, prepare=False)
                connection.execute(
                    "INSERT INTO public.schema_migrations(version) VALUES (%s)",
                    (version,),
                )
            connection.execute(GRANT.read_text(), prepare=False)
            result = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM public.schema_migrations ORDER BY version"
                )
            ]
            if result != versions:
                raise ValueError
        return {
            "migration_count": 32,
            "head": versions[-1],
            "identity_grant_applied": True,
        }
    except Exception:
        raise UpgradeRefused(
            "CN-03 upgrade stopped; inspect outcome before any retry"
        ) from None
