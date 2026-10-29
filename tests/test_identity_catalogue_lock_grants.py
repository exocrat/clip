"""Disposable SQL proof for reviewed marketplace catalogue lock privileges."""

import pytest
from psycopg.errors import InsufficientPrivilege

from apps.api.tests.domains.identity.migration_fixtures import (
    reviewed_migration_directory,
)
from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_database,
    reviewed_disposable_database,
)


def test_column_grants_enable_catalogue_locks_without_table_update(disposable_database):
    """FOR SHARE needs one UPDATE column; assert narrowly scoped effective ACLs."""
    with disposable_database() as c:
        c.execute("CREATE ROLE clip_catalogue_lock_probe NOLOGIN")
        c.execute("GRANT USAGE ON SCHEMA listings TO clip_catalogue_lock_probe")
        c.execute(
            "GRANT SELECT ON listings.categories, listings.conditions TO clip_catalogue_lock_probe"
        )
        for table, code in (("categories", "books"), ("conditions", "good")):
            with pytest.raises(InsufficientPrivilege):
                with c.transaction():
                    c.execute("SET LOCAL ROLE clip_catalogue_lock_probe")
                    c.execute(
                        "SELECT code FROM listings."
                        + table
                        + " WHERE code=%s FOR SHARE",
                        (code,),
                    )
        c.execute(
            "GRANT UPDATE (created_at) ON listings.categories TO clip_catalogue_lock_probe"
        )
        c.execute(
            "GRANT UPDATE (label) ON listings.conditions TO clip_catalogue_lock_probe"
        )
        for table, code in (("categories", "books"), ("conditions", "good")):
            with c.transaction():
                c.execute("SET LOCAL ROLE clip_catalogue_lock_probe")
                assert c.execute(
                    "SELECT code FROM listings." + table + " WHERE code=%s FOR SHARE",
                    (code,),
                ).fetchone() == (code,)
        assert not c.execute(
            "SELECT has_table_privilege('clip_catalogue_lock_probe','listings.categories','UPDATE')"
        ).fetchone()[0]
        assert not c.execute(
            "SELECT has_table_privilege('clip_catalogue_lock_probe','listings.conditions','UPDATE')"
        ).fetchone()[0]
        assert not c.execute(
            "SELECT has_column_privilege('clip_catalogue_lock_probe','listings.categories','active','UPDATE')"
        ).fetchone()[0]
        assert not c.execute(
            "SELECT has_column_privilege('clip_catalogue_lock_probe','listings.conditions','active','UPDATE')"
        ).fetchone()[0]


def test_guarded_restore_is_idempotent_and_refuses_unreviewed_access(
    reviewed_disposable_database,
):
    """Only the two reviewed ACLs return; unexpected broader privileges stop work."""
    from scripts import identity_catalogue_grants as restore

    with reviewed_disposable_database() as c:
        c.execute("CREATE ROLE clip_test_marketplace_app NOLOGIN")
        c.execute("GRANT USAGE ON SCHEMA listings TO clip_test_marketplace_app")
        c.execute(
            "GRANT SELECT ON listings.categories, listings.conditions TO clip_test_marketplace_app"
        )
    first = restore.restore(reviewed_disposable_database, isolated=True)
    assert set(first["changed"]) == {
        "listings.categories.created_at",
        "listings.conditions.label",
    }
    assert restore.restore(reviewed_disposable_database, isolated=True)["changed"] == []
    with reviewed_disposable_database() as c:
        c.execute(
            "REVOKE UPDATE (created_at) ON listings.categories FROM clip_test_marketplace_app"
        )
        c.execute(
            "GRANT UPDATE (active) ON listings.conditions TO clip_test_marketplace_app"
        )
    with pytest.raises(restore.GrantRestoreFailure):
        restore.restore(reviewed_disposable_database, isolated=True)
    with reviewed_disposable_database() as c:
        assert not c.execute(
            "SELECT has_column_privilege('clip_test_marketplace_app','listings.categories','created_at','UPDATE')"
        ).fetchone()[0]
        assert c.execute(
            "SELECT has_column_privilege('clip_test_marketplace_app','listings.conditions','active','UPDATE')"
        ).fetchone() == (True,)
