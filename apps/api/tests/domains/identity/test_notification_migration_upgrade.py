"""Offline candidate migration rehearsal against an owned 23-file database."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4
import pytest
from scripts.cn03_migration_upgrade import (
    GRANT_SHA256,
    MANIFEST_SHA256,
    UpgradeRefused,
    upgrade,
)

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
    the retained database's unknown baseline. The full suffix and grant commit
    together; a mismatched baseline is refused rather than retried.
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
        connection.execute("CREATE ROLE clip_test_identity_app NOLOGIN")
        with pytest.raises(UpgradeRefused):
            upgrade(
                connection,
                isolated=True,
                approved_manifest="incorrect",
                approved_grant=GRANT_SHA256,
            )
        result = upgrade(
            connection,
            isolated=True,
            approved_manifest=MANIFEST_SHA256,
            approved_grant=GRANT_SHA256,
        )
        assert result == {
            "migration_count": 32,
            "head": "20261029182500",
            "identity_grant_applied": True,
        }
        with pytest.raises(UpgradeRefused):
            upgrade(
                connection,
                isolated=True,
                approved_manifest=MANIFEST_SHA256,
                approved_grant=GRANT_SHA256,
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


def test_upgrade_rolls_back_all_files_when_later_constraint_fails(
    reviewed_disposable_database,
):
    """A bad existing budget rejects the suffix without retaining earlier changes."""
    with reviewed_disposable_database() as connection:
        user_id = uuid4()
        connection.execute("CREATE ROLE clip_test_identity_app NOLOGIN")
        connection.execute(
            "INSERT INTO identity.users(id,account_class,status) VALUES(%s,'regular','active')",
            (user_id,),
        )
        connection.execute(
            "INSERT INTO search.wanted_requests(id,author_id,title,description,category_code,status,budget_paise) "
            "VALUES(%s,%s,'Synthetic','Synthetic','other','open',1000000100)",
            (uuid4(), user_id),
        )
        with pytest.raises(UpgradeRefused):
            upgrade(
                connection,
                isolated=True,
                approved_manifest=MANIFEST_SHA256,
                approved_grant=GRANT_SHA256,
            )
        assert connection.execute(
            "SELECT count(*),max(version) FROM public.schema_migrations"
        ).fetchone() == (23, "20261027112205")
        assert connection.execute(
            "SELECT to_regclass('search.wanted_open_text_search')"
        ).fetchone() == (None,)
        assert connection.execute(
            "SELECT count(*) FROM listings.categories WHERE code='sports_fitness'"
        ).fetchone() == (0,)
