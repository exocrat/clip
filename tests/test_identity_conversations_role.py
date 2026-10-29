"""Operator helper checks run only in a fixture-owned PostgreSQL cluster."""

import secrets

from pydantic import SecretStr
import pytest

from apps.api.tests.domains.identity.migration_fixtures import (
    reviewed_migration_directory,
)
from apps.api.tests.domains.identity.postgres_fixtures import (
    reviewed_disposable_database,
)
from scripts import identity_conversations_role as operator


@pytest.fixture
def connect(reviewed_disposable_database):
    """Normalize only this owned database's PUBLIC baseline; preserve schema/data."""
    with reviewed_disposable_database() as c:
        c.execute("REVOKE CONNECT,TEMPORARY ON DATABASE clip_test_identity FROM PUBLIC")
        c.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        (
            c.execute("DROP OWNED BY clip_test_conversations_app")
            if c.execute(
                "SELECT 1 FROM pg_roles WHERE rolname='clip_test_conversations_app'"
            ).fetchone()
            else None
        )
        c.execute("DROP ROLE IF EXISTS clip_test_conversations_app")
    return reviewed_disposable_database


def test_exact_proposal_creates_only_scoped_role_and_refuses_rotation(connect):
    """Effective ACLs are checked before commit; an existing login is immutable here."""
    result = operator.provision(
        connect,
        SecretStr(secrets.token_urlsafe(32)),
        approved_sql_sha256=operator.APPROVED_SQL_SHA256,
        isolated=True,
    )
    assert result["role_created"] and not result["ssm_written"]
    with connect() as c:
        oid = c.execute(
            "SELECT oid FROM pg_roles WHERE rolname=%s", (operator.ROLE,)
        ).fetchone()[0]
        assert c.execute(
            "SELECT rolconnlimit FROM pg_roles WHERE rolname=%s", (operator.ROLE,)
        ).fetchone() == (2,)
    with pytest.raises(operator.RoleSetupFailure):
        operator.provision(
            connect,
            SecretStr(secrets.token_urlsafe(32)),
            approved_sql_sha256=operator.APPROVED_SQL_SHA256,
            isolated=True,
        )
    with connect() as c:
        assert c.execute(
            "SELECT oid FROM pg_roles WHERE rolname=%s", (operator.ROLE,)
        ).fetchone() == (oid,)


def test_public_privilege_drift_refuses_without_repair_or_role(connect):
    """Shared ACL drift is a stop condition, never an implicit global revoke."""
    with connect() as c:
        c.execute("GRANT TEMP ON DATABASE clip_test_identity TO PUBLIC")
    with pytest.raises(operator.RoleSetupFailure):
        operator.provision(
            connect,
            SecretStr(secrets.token_urlsafe(32)),
            approved_sql_sha256=operator.APPROVED_SQL_SHA256,
            isolated=True,
        )
    with connect() as c:
        assert not c.execute(
            "SELECT 1 FROM pg_roles WHERE rolname=%s", (operator.ROLE,)
        ).fetchone()
        assert c.execute(
            "SELECT has_database_privilege('public','clip_test_identity','TEMP')"
        ).fetchone() == (True,)


def test_wrong_hash_and_live_target_refuse(connect):
    """Neither an unreviewed proposal nor a local connection can satisfy live guards."""
    for digest, isolated in (("0" * 64, True), (operator.APPROVED_SQL_SHA256, False)):
        with pytest.raises(operator.RoleSetupFailure):
            operator.provision(
                connect,
                SecretStr(secrets.token_urlsafe(32)),
                approved_sql_sha256=digest,
                isolated=isolated,
            )
    with connect() as c:
        assert not c.execute(
            "SELECT 1 FROM pg_roles WHERE rolname=%s", (operator.ROLE,)
        ).fetchone()


def test_private_uri_preserves_tls_and_refuses_wrong_target():
    """Only the fixed hosted database with verify-full/CA yields a masked URI."""
    password = SecretStr(secrets.token_urlsafe(32))
    base = SecretStr(
        "postgresql://synthetic@"
        + operator.HOST
        + "/clip_test?sslmode=verify-full&sslrootcert=/app/ca.pem"
    )
    result = operator.credential_uri(base, password)
    assert str(result) == "**********"
    assert "sslmode=verify-full" in result.get_secret_value()
    for bad in (
        base.get_secret_value().replace("verify-full", "require"),
        base.get_secret_value().replace(operator.HOST, "wrong.invalid"),
        base.get_secret_value() + "&user=clip_test_admin",
        base.get_secret_value() + "&options=-c%20role%3Dclip_test_admin",
    ):
        with pytest.raises(operator.RoleSetupFailure):
            operator.credential_uri(SecretStr(bad), password)


def test_effective_grant_mismatch_rolls_back_new_login(connect, monkeypatch):
    """A failed postcondition rolls back role creation and all its grants."""
    monkeypatch.setitem(operator.TABLES, "threads", {"SELECT"})
    with pytest.raises(operator.RoleSetupFailure):
        operator.provision(
            connect,
            SecretStr(secrets.token_urlsafe(32)),
            approved_sql_sha256=operator.APPROVED_SQL_SHA256,
            isolated=True,
        )
    with connect() as c:
        assert not c.execute(
            "SELECT 1 FROM pg_roles WHERE rolname=%s", (operator.ROLE,)
        ).fetchone()


def test_runtime_system_trust_uri_matches_existing_image_configuration():
    """The approved image installs RDS roots in OS trust and uses verify-full."""
    base = SecretStr(
        "postgresql://synthetic@"
        + operator.HOST
        + "/clip_test?sslmode=verify-full&sslrootcert=system"
    )
    result = operator.credential_uri(base, SecretStr(secrets.token_urlsafe(32)))
    assert "sslrootcert=system" in result.get_secret_value()
    assert str(result) == "**********"
