"""Real PostgreSQL setup/refusal checks in a fresh owned, networkless database."""

import secrets
from urllib.parse import quote, urlencode

from psycopg import sql
from pydantic import SecretStr
import pytest

from app.core.config import ConfigurationError
from app.domains.identity.database_setup import (
    LOGGING,
    create_identity_role,
    inspect_identity_database,
)
from app.domains.identity.runtime_database import (
    ROLE,
    connection_factory,
    validate_database,
)
from app.domains.identity.temporary_crypto import TemporaryKeys

DB = "clip_test_identity"
ADMIN = "clip_identity_ci"


@pytest.fixture
def setup_case(disposable_database):
    """Explicit logging/ACL baseline changes affect only this module's container."""

    def connect():
        c = disposable_database()
        for name, value in LOGGING.items():
            c.execute(
                sql.SQL("SET {} = {}").format(sql.Identifier(name), sql.Literal(value))
            )
        return c

    with connect() as c:
        c.execute("REVOKE CONNECT,TEMPORARY ON DATABASE clip_test_identity FROM PUBLIC")
        c.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        if c.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,)).fetchone():
            c.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(ROLE)))
        c.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(ROLE)))
    yield connect
    with connect() as c:
        if c.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,)).fetchone():
            c.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(ROLE)))
            c.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(ROLE)))


def create(connect, password=None):
    create_identity_role(
        connect,
        password or SecretStr(secrets.token_hex(32)),
        expected_database=DB,
        expected_admin=ADMIN,
    )


def absent(connect):
    with connect() as c:
        assert (
            c.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,)).fetchone()
            is None
        )


def test_create_real_restricted_scram_login(setup_case):
    inspect_identity_database(setup_case, expected_database=DB, expected_admin=ADMIN)
    password = SecretStr(secrets.token_hex(32))
    create(setup_case, password)
    with setup_case() as c:
        info = c.info
        dsn = SecretStr(
            "postgresql:///"
            + quote(DB, safe="")
            + "?"
            + urlencode(
                dict(
                    host=info.host,
                    port=info.port,
                    user=ROLE,
                    password=password.get_secret_value(),
                    sslmode="disable",
                )
            )
        )
        assert c.execute(
            "SELECT rolconnlimit FROM pg_roles WHERE rolname=%s", (ROLE,)
        ).fetchone() == (10,)
    keys = TemporaryKeys("synthetic-v1", *(secrets.token_bytes(32) for _ in range(3)))
    validate_database(connection_factory(dsn, "test"), keys)
    with pytest.raises(ConfigurationError):
        create(setup_case)
    validate_database(connection_factory(dsn, "test"), keys)


@pytest.mark.parametrize(
    "change,restore",
    [
        (
            "GRANT TEMPORARY ON DATABASE clip_test_identity TO PUBLIC",
            "REVOKE TEMPORARY ON DATABASE clip_test_identity FROM PUBLIC",
        ),
        (
            "GRANT CONNECT ON DATABASE clip_test_identity TO PUBLIC",
            "REVOKE CONNECT ON DATABASE clip_test_identity FROM PUBLIC",
        ),
        (
            "GRANT CREATE ON SCHEMA public TO PUBLIC",
            "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
        ),
        (
            "GRANT SELECT ON identity.users TO PUBLIC",
            "REVOKE SELECT ON identity.users FROM PUBLIC",
        ),
        (
            "ALTER DEFAULT PRIVILEGES IN SCHEMA identity GRANT SELECT ON TABLES TO PUBLIC",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA identity REVOKE SELECT ON TABLES FROM PUBLIC",
        ),
        (
            "ALTER TABLE identity.contacts RENAME TO contacts_hidden",
            "ALTER TABLE identity.contacts_hidden RENAME TO contacts",
        ),
        (
            "UPDATE public.schema_migrations SET version='missing-test' WHERE version='20261023202807'",
            "UPDATE public.schema_migrations SET version='20261023202807' WHERE version='missing-test'",
        ),
    ],
)
def test_unsafe_catalog_state_never_creates_role(setup_case, change, restore):
    with setup_case() as c:
        c.execute(change)
    try:
        with pytest.raises(ConfigurationError):
            inspect_identity_database(
                setup_case, expected_database=DB, expected_admin=ADMIN
            )
        with pytest.raises(ConfigurationError):
            create(setup_case)
        absent(setup_case)
    finally:
        with setup_case() as c:
            c.execute(restore)


@pytest.mark.parametrize(
    "setting,value",
    [
        ("log_statement", "all"),
        ("log_min_error_statement", "error"),
        ("log_transaction_sample_rate", "1"),
    ],
)
def test_unsafe_logging_is_not_repaired(setup_case, setting, value):
    def unsafe():
        c = setup_case()
        c.execute(
            sql.SQL("SET {} = {}").format(sql.Identifier(setting), sql.Literal(value))
        )
        return c

    with pytest.raises(ConfigurationError):
        create(unsafe)
    absent(setup_case)


@pytest.mark.parametrize(
    "database,admin", [(DB, "wrong-admin"), ("wrong-database", ADMIN)]
)
def test_wrong_target_rejected(setup_case, database, admin):
    with pytest.raises(ConfigurationError):
        create_identity_role(
            setup_case,
            SecretStr(secrets.token_hex(32)),
            expected_database=database,
            expected_admin=admin,
        )
    absent(setup_case)


def test_failure_after_create_rolls_back_role(setup_case):
    # Real CREATE ROLE succeeds; a deliberately injected failure at the next SQL
    # statement proves the enclosing PostgreSQL transaction rolls it back.
    class FailAfterCreate:
        def __init__(self, c):
            self.c = c

        def __enter__(self):
            self.c.__enter__()
            return self

        def __exit__(self, *args):
            return self.c.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.c, name)

        def execute(self, query, params=None):
            if isinstance(query, sql.Composed) and query.as_string(self.c).startswith(
                "ALTER ROLE"
            ):
                raise RuntimeError("synthetic post-create failure")
            return self.c.execute(query, params)

    with pytest.raises(ConfigurationError):
        create(lambda: FailAfterCreate(setup_case()))
    absent(setup_case)
