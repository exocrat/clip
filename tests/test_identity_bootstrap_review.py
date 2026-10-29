"""Real disposable SQL review checks, never shared/cloud reset or new grants."""

import json
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from app.domains.identity import migration_runner as runner
from apps.api.tests.domains.identity.migration_fixtures import (
    migration_case,
    reviewed_migration_directory,
    tls_database,
)

ROOT = Path(__file__).resolve().parents[1]


def migrate(case, directory):
    """Only the existing isolated fixture may apply the reviewed 23-file source."""
    runner.run_migrations(
        case.connect,
        case.password,
        case.target,
        directory=directory,
        manifest=ROOT
        / "docs/evaluation/identity/id-01-step-12/shared-migration-manifest.json",
        ca=case.ca,
        image=case.image,
    )


def test_inventory_sees_external_fk_and_internal_view_owner(
    migration_case, reviewed_migration_directory
):
    """Catch the two distinct cross-schema CASCADE paths without executing DROP."""
    migrate(migration_case, reviewed_migration_directory)
    with migration_case.connect() as c:
        c.execute("CREATE SCHEMA outside_review")
        c.execute(
            "CREATE TABLE outside_review.keep (id uuid REFERENCES identity.users(id))"
        )
        c.execute(
            "CREATE VIEW outside_review.keep_view AS SELECT id FROM identity.users"
        )
        original = (
            ROOT / "docs/evaluation/identity/id-01-step-13/bootstrap-inventory.sql"
        ).read_text()
        # Substitute only the fixed target predicate for this named isolated
        # fixture; the live candidate remains hard-pinned and unchanged on disk.
        candidate = original
        for old, new in [
            (
                "current_database() = 'clip_test'",
                "current_database() = 'clip_test_identity'",
            ),
            ("current_user = 'clip_test_admin'", "current_user = 'clip_identity_ci'"),
            ("session_user = 'clip_test_admin'", "session_user = 'clip_identity_ci'"),
        ]:
            assert candidate.count(old) == 1
            candidate = candidate.replace(old, new)
        cursor = c.execute(candidate, prepare=False)
        external_fk = []
        external_view = []
        while True:
            if cursor.description:
                names = [column.name for column in cursor.description]
                rows = cursor.fetchall()
                if "external_fk_schema" in names:
                    external_fk = rows
                if "object_schema" in names and "object_type" in names:
                    external_view = [
                        r
                        for r in rows
                        if r[names.index("object_schema")] == "outside_review"
                    ]
            if not cursor.nextset():
                break
        assert external_fk and external_view
        assert c.execute(
            "SELECT to_regclass('outside_review.keep'),to_regclass('outside_review.keep_view')"
        ).fetchone() == ("outside_review.keep", "outside_review.keep_view")


def test_historical_grants_do_not_cover_current_listing_trigger_or_conversations(
    migration_case,
    reviewed_migration_directory,
):
    """Prove the old receipt is insufficient, not that live ACLs equal that receipt."""
    migrate(migration_case, reviewed_migration_directory)
    role = "clip_test_marketplace_app"
    receipt = json.loads(
        (
            ROOT
            / "docs/evaluation/identity/id-01-step-12/marketplace-runtime-role-result-20261026T104412Z.json"
        ).read_text()
    )
    with migration_case.connect() as c:
        c.execute(
            sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT").format(sql.Identifier(role))
        )
        c.execute(
            sql.SQL("GRANT USAGE ON SCHEMA listings,search TO {}").format(
                sql.Identifier(role)
            )
        )
        for table, privileges in receipt["grants"]["tables"].items():
            schema, name = table.split(".")
            c.execute(
                sql.SQL("GRANT {} ON {} TO {}").format(
                    sql.SQL(",").join(map(sql.SQL, privileges)),
                    sql.Identifier(schema, name),
                    sql.Identifier(role),
                )
            )
        owner = uuid4()
        c.execute(
            "INSERT INTO identity.users(id,account_class,status) VALUES(%s,'regular','active')",
            (owner,),
        )
        category = c.execute(
            "SELECT id FROM listings.categories ORDER BY id LIMIT 1"
        ).fetchone()[0]
        condition = c.execute(
            "SELECT code FROM listings.conditions ORDER BY code LIMIT 1"
        ).fetchone()[0]
        c.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
        try:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                c.execute("SELECT 1 FROM conversations.threads LIMIT 1")
            with pytest.raises(psycopg.errors.InsufficientPrivilege) as error:
                c.execute(
                    """INSERT INTO listings.sale_listings
                    (id,owner_id,title,description,category_id,condition_code,
                     asking_price_paise,negotiable,pickup_area,availability)
                    VALUES(%s,%s,'Synthetic review','Synthetic review',%s,%s,10000,true,'Synthetic','available')""",
                    (uuid4(), owner, category, condition),
                )
            assert "embedding" in error.value.diag.message_primary
        finally:
            c.execute("RESET ROLE")
        assert c.execute("SELECT count(*) FROM listings.sale_listings").fetchone() == (
            0,
        )


def test_live_candidate_rejects_other_database_login(tls_database):
    """The original live guard rejects the owned fixture before further queries."""
    candidate = (
        ROOT / "docs/evaluation/identity/id-01-step-13/bootstrap-inventory.sql"
    ).read_text()
    with tls_database.connect() as c:
        try:
            with pytest.raises(psycopg.errors.DivisionByZero):
                c.execute(candidate, prepare=False)
        finally:
            c.execute("ROLLBACK")
