"""Real disposable-schema diagnostics; no retained targets or cloud credentials."""

from dataclasses import asdict
import json

import pytest

from app.domains.identity.database_metadata import collect_database_metadata
from app.domains.identity.database_setup import VERSIONS


def collect(connect, **kwargs):
    return collect_database_metadata(
        connect,
        expected_database=kwargs.get("database", "clip_test_identity"),
        expected_admin=kwargs.get("admin", "clip_identity_ci"),
    )


def test_normal_metadata_is_not_an_acceptance_claim(disposable_database):
    result = collect(disposable_database)
    assert result.complete and result.failed_phase is None
    assert result.checks["migration_relation_exists"] is True
    assert all(result.checks["required_migrations"].values())
    assert result.checks["identity_table_inventory_matches"] is True
    assert result.checks["identity_role_exists"] is False
    # Fixture's default PUBLIC grants/statement-error logging are unsafe for setup.
    # Diagnosis succeeds and preserves findings; it neither repairs nor approves.
    assert result.checks["public_database_grant_count"] > 0
    assert result.checks["safe_logging"]["log_min_error_statement"] is False


@pytest.mark.parametrize(
    "alter,restore,exists",
    [
        (
            "ALTER TABLE public.schema_migrations RENAME TO synthetic_migrations_hidden",
            "ALTER TABLE public.synthetic_migrations_hidden RENAME TO schema_migrations",
            False,
        ),
        (
            "ALTER TABLE public.schema_migrations RENAME COLUMN version TO synthetic_version",
            "ALTER TABLE public.schema_migrations RENAME COLUMN synthetic_version TO version",
            True,
        ),
    ],
)
def test_missing_tracker_or_column_does_not_abort_inventory(
    disposable_database, alter, restore, exists
):
    with disposable_database() as c:
        c.execute(alter)
    try:
        result = collect(disposable_database)
        assert result.complete and result.failed_phase is None
        assert result.checks["migration_relation_exists"] is exists
        assert result.checks["migration_relation_supported"] is False
        assert result.checks["required_migrations"] == {v: False for v in VERSIONS}
        assert result.checks["identity_table_inventory_matches"] is True
        assert "public_database_grant_count" in result.checks
    finally:
        with disposable_database() as c:
            c.execute(restore)


def test_absent_identity_schema_is_a_finding(disposable_database):
    with disposable_database() as c:
        c.execute("ALTER SCHEMA identity RENAME TO synthetic_identity_hidden")
    try:
        result = collect(disposable_database)
        assert result.complete
        assert result.checks["identity_table_count"] == 0
        assert result.checks["identity_table_inventory_matches"] is False
        assert result.checks["missing_identity_tables"]
    finally:
        with disposable_database() as c:
            c.execute("ALTER SCHEMA synthetic_identity_hidden RENAME TO identity")


@pytest.mark.parametrize(
    "database,admin",
    [("wrong_database", "clip_identity_ci"), ("clip_test_identity", "wrong_admin")],
)
def test_wrong_target_stops_before_inventory(disposable_database, database, admin):
    result = collect(disposable_database, database=database, admin=admin)
    assert not result.complete and result.failed_phase == "target"
    assert "migration_relation_exists" not in result.checks


class InspectConnection:
    """Observe the actual SQL transaction and inject one later redacted failure."""

    def __init__(self, c, fail=False):
        self.c, self.fail = c, fail

    def __enter__(self):
        self.c.__enter__()
        return self

    def __exit__(self, *args):
        return self.c.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self.c, name)

    def execute(self, query, params=None):
        if query == "SELECT current_database(),current_user,session_user":
            assert self.c.execute("SHOW transaction_read_only").fetchone() == ("on",)
            assert self.c.execute("SHOW transaction_isolation").fetchone() == (
                "repeatable read",
            )
        if self.fail and query == "SELECT current_setting(%s)":
            raise RuntimeError("PRIVATE diagnostic that must never be returned")
        return self.c.execute(query, params)


def test_actual_readonly_repeatable_snapshot(disposable_database):
    result = collect(lambda: InspectConnection(disposable_database()))
    assert result.complete


def test_later_failure_keeps_safe_partial_results(disposable_database):
    result = collect(lambda: InspectConnection(disposable_database(), fail=True))
    assert not result.complete and result.failed_phase == "logging"
    assert result.checks["identity_table_inventory_matches"] is True
    assert all(result.checks["required_migrations"].values())
    assert "safe_logging" not in result.checks
    assert "PRIVATE" not in json.dumps(asdict(result))


def test_connection_error_is_redacted():
    def unavailable():
        raise RuntimeError("PRIVATE connection credential")

    result = collect(unavailable)
    assert not result.complete and result.failed_phase == "connection"
    assert result.checks == {}
    assert "PRIVATE" not in json.dumps(asdict(result))
