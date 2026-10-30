"""Offline candidate migration rehearsal against an owned 23-file database."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from apps.api.tests.domains.identity.migration_fixtures import (
    reviewed_migration_directory,
)
from apps.api.tests.domains.identity.postgres_fixtures import (
    reviewed_disposable_database,
)

ROOT = Path(__file__).resolve().parents[5]


def test_candidate_upgrade_from_reviewed_identity_baseline(
    reviewed_disposable_database,
):
    """Apply only the hash-pinned suffix and verify its schema and migration ledger.

    This is an isolated rehearsal, not an operator migration tool or evidence of
    the retained database's unknown baseline. Each SQL file and ledger insert
    commit together, so a failure rolls back its current migration.
    """
    manifest = json.loads(
        (ROOT / "docs/environment/cn-03-candidate-migration-manifest.json").read_text()
    )
    entries = manifest["migrations"]
    assert len(entries) == manifest["migration_count"] == 32
    assert entries[22]["version"] == "20261027112205"
    with reviewed_disposable_database() as connection:
        versions = [
            r[0]
            for r in connection.execute(
                "SELECT version FROM public.schema_migrations ORDER BY version"
            )
        ]
        assert versions == [entry["version"] for entry in entries[:23]]
        user_id = uuid4()
        connection.execute(
            "INSERT INTO identity.users(id, account_class, status, display_name) "
            "VALUES (%s, 'regular', 'active', 'SyntheticUser')",
            (user_id,),
        )
        for entry in entries:
            assert (
                hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest()
                == entry["sha256"]
            )
        for entry in entries[23:]:
            raw = (ROOT / entry["path"]).read_text()
            up = raw.split("-- migrate:up", 1)[1].split("-- migrate:down", 1)[0]
            with connection.transaction():
                connection.execute(up, prepare=False)
                connection.execute(
                    "INSERT INTO public.schema_migrations(version) VALUES (%s)",
                    (entry["version"],),
                )
        assert [
            r[0]
            for r in connection.execute(
                "SELECT version FROM public.schema_migrations ORDER BY version"
            )
        ] == [entry["version"] for entry in entries]
        assert connection.execute(
            "SELECT to_regclass('identity.notification_destinations'), "
            "to_regclass('conversations.notification_retry_due')"
        ).fetchone() == (
            "identity.notification_destinations",
            "conversations.notification_retry_due",
        )
        assert connection.execute(
            "SELECT column_default FROM information_schema.columns WHERE "
            "table_schema='identity' AND table_name='users' AND "
            "column_name='conversation_email_enabled'"
        ).fetchone() == ("true",)
        assert connection.execute(
            "SELECT display_name,handle_ready,conversation_email_enabled FROM identity.users WHERE id=%s",
            (user_id,),
        ).fetchone() == ("SyntheticUser", True, True)
