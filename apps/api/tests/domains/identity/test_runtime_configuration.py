"""Offline SSM ports and real low-privilege disposable PostgreSQL startup checks."""

import base64
from datetime import UTC, datetime
from ipaddress import ip_address
import json
from pathlib import Path
import secrets
from types import SimpleNamespace
from urllib.parse import quote, urlencode
from uuid import uuid4

from psycopg import errors, sql
from pydantic import SecretStr, ValidationError
import pytest

from app.core.config import ConfigurationError, Settings
from app.domains.identity.http import BrowserPolicy
from app.domains.identity.runtime_configuration import (
    RuntimeReferences,
    parse_authentication_keys,
    prepare_hosted_test_identity,
    prepare_local_identity,
    read_secure_parameter,
)
from app.domains.identity.runtime_database import (
    IdentityConnectionPool,
    ROLE,
    connection_factory,
    validate_database,
)
from apps.api.tests.domains.identity.session_fixtures import (
    CaptureMail,
    EMAIL,
    PASSWORD,
)

ROOT = Path(__file__).resolve().parents[5]
NOW = datetime(2030, 1, 1, tzinfo=UTC)
REFS = RuntimeReferences()


def key_document():
    """Fresh synthetic keys kept in process only; no real credential/SSM read."""
    return {
        "schema_version": 1,
        "key_version": "synthetic-v1",
        **{
            field: base64.b64encode(secrets.token_bytes(32)).decode("ascii")
            for field in ("lookup", "verifier", "target_encryption")
        },
    }


class Parameters:
    """Return exact typed synthetic parameter versions and capture read names only."""

    def __init__(self, values):
        self.values = values
        self.calls = []

    def get_parameter(self, **kwargs):
        self.calls.append(kwargs["Name"])
        return {
            "Parameter": {
                "Name": kwargs["Name"],
                "Type": "SecureString",
                "Version": 1,
                "Value": self.values[kwargs["Name"]],
            }
        }


@pytest.fixture(scope="module")
def app_role(disposable_database):
    """Create SCRAM login/grants only in the fixture's fresh owned SQL container."""
    password = secrets.token_hex(24)
    with disposable_database() as c:
        c.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10 PASSWORD {}"
            ).format(sql.Identifier(ROLE), sql.Literal(password))
        )
        c.execute("REVOKE TEMPORARY ON DATABASE clip_test_identity FROM PUBLIC")
        c.execute(
            sql.SQL("GRANT CONNECT ON DATABASE clip_test_identity TO {}").format(
                sql.Identifier(ROLE)
            )
        )
        proposal = (ROOT / "database/roles/identity-runtime.sql.proposed").read_text()
        proposal += (
            "\n"
            + (
                ROOT / "database/roles/identity-notification-runtime.sql.proposed"
            ).read_text()
        )
        c.execute(proposal)
        info = c.info
        dsn = (
            "postgresql:///"
            + quote(info.dbname, safe="")
            + "?"
            + urlencode(
                {
                    "host": info.host,
                    "port": info.port,
                    "user": ROLE,
                    "password": password,
                    "sslmode": "disable",
                }
            )
        )
    return SimpleNamespace(
        admin=disposable_database, dsn=SecretStr(dsn), proposal=proposal
    )


@pytest.fixture
def runtime_case(app_role):
    """Reset only this module's disposable state; restore proposal before each case."""
    with app_role.admin() as c:
        c.execute("TRUNCATE identity.users,identity.otp_key_binding CASCADE")
        c.execute(app_role.proposal)
    document = key_document()
    client = Parameters(
        {
            REFS.authentication_keys: json.dumps(document),
            REFS.database_url: app_role.dsn.get_secret_value(),
            REFS.email_delivery: json.dumps(
                {"version": 1, "primary": "resend", "resend_api_key": "synthetic-key"}
            ),
        }
    )
    settings = Settings(
        environment="test",
        identity_provider="microsoft",
        email_provider="dual",
        ses_test_recipients=(EMAIL,),
    )
    return SimpleNamespace(
        target=app_role, document=document, client=client, settings=settings
    )


def bootstrap(case):
    """Real bootstrap: offline SSM, actual role/TLS/logging/key validation, no send."""
    return prepare_local_identity(
        case.settings,
        BrowserPolicy(("https://clip-iisc.site",)),
        client=case.client,
        clock=lambda: NOW,
    )


def test_bootstrap_and_real_auth_work_with_restricted_role(runtime_case):
    case = runtime_case
    # Exercise the guard directly first to retain its safe phase-only diagnostic.
    validate_database(
        connection_factory(case.target.dsn, "test"),
        parse_authentication_keys(SecretStr(json.dumps(case.document))),
    )
    state = bootstrap(case)
    assert case.client.calls == [
        REFS.authentication_keys,
        REFS.database_url,
        REFS.email_delivery,
    ]
    # Warmup caches configuration; a second warmup reads nothing and sends nothing.
    state.sender.warmup()
    assert len(case.client.calls) == 3
    mailbox = CaptureMail()
    request = state.sessions.challenges.start(
        EMAIL, "initial_verification", uuid4(), ip_address("192.0.2.27")
    )
    assert request.delivery.dispatch(mailbox, now=NOW)
    grant = state.sessions.activate(request.challenge_id, mailbox.code(), PASSWORD)
    assert (
        state.sessions.authenticate(grant.token.get_secret_value()).caller.account_class
        == "temporary"
    )
    state.sessions.contacts.set_contact(grant.identity.caller, "phone", "+12025550100")
    assert (
        state.sessions.contacts.read_contacts(grant.identity.caller).phone
        == "+12025550100"
    )
    state.sessions.logout(grant.token.get_secret_value())
    # A restarted process keeps the stored key binding; the loader never rekeys.
    bootstrap(case)


def test_pool_reuses_leases_bounds_waits_and_rolls_back(runtime_case):
    """Real restricted DB: reuse a backend, bound exhaustion and discard failed work."""
    from psycopg_pool import PoolTimeout

    pooled = IdentityConnectionPool(runtime_case.target.dsn, "test", max_size=1)
    try:
        with pooled() as first:
            pid = first.execute("SELECT pg_backend_pid()").fetchone()[0]
            with pytest.raises(PoolTimeout):
                with pooled():
                    pytest.fail("A second borrower exceeded the pool bound")
        with pytest.raises(errors.DivisionByZero):
            with pooled() as connection, connection.transaction():
                connection.execute("SELECT 1/0")
        with pooled() as reused:
            assert reused.execute("SELECT pg_backend_pid()").fetchone()[0] == pid
            assert reused.execute("SELECT 1").fetchone() == (1,)
    finally:
        pooled.close()


def test_pooled_authentication_observes_logout_and_expiry(runtime_case):
    """Pooling never caches a session or extends its account/session deadlines."""
    from datetime import timedelta
    from app.core.errors import PublicError
    from app.domains.identity.sessions import IdentitySessions

    state = bootstrap(runtime_case)
    mailbox = CaptureMail()
    request = state.sessions.challenges.start(
        EMAIL, "initial_verification", uuid4(), ip_address("192.0.2.27")
    )
    assert request.delivery.dispatch(mailbox, now=NOW)
    grant = state.sessions.activate(request.challenge_id, mailbox.code(), PASSWORD)
    pooled = IdentityConnectionPool(runtime_case.target.dsn, "test", max_size=2)
    clock = [NOW]
    service = IdentitySessions(
        pooled,
        parse_authentication_keys(SecretStr(json.dumps(runtime_case.document))),
        lambda: clock[0],
    )
    try:
        assert (
            service.authenticate(grant.token.get_secret_value()).caller.user_id
            == grant.identity.caller.user_id
        )
        clock[0] += timedelta(days=8)
        with pytest.raises(PublicError):
            service.authenticate(grant.token.get_secret_value())
        clock[0] = NOW
        state.sessions.logout(grant.token.get_secret_value())
        with pytest.raises(PublicError):
            service.authenticate(grant.token.get_secret_value())
    finally:
        pooled.close()


def test_lambda_identity_pool_releases_idle_connections(runtime_case):
    """A frozen idle Lambda environment must not retain a database lease."""
    pooled = IdentityConnectionPool(
        runtime_case.target.dsn, "test", max_size=1, retain_idle=False
    )
    try:
        with pooled() as connection:
            pid = connection.execute("SELECT pg_backend_pid()").fetchone()[0]
        with runtime_case.target.admin() as admin:
            assert admin.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE pid=%s", (pid,)
            ).fetchone() == (0,)
    finally:
        pooled.close()


def test_hosted_test_bootstrap_uses_exact_origins_and_no_send(runtime_case):
    """The explicit ASGI path shares real startup checks without demo auth."""
    case = runtime_case
    settings = Settings(
        environment="test",
        identity_provider="microsoft",
        email_provider="dual",
        ses_test_recipients=(EMAIL,),
        identity_runtime_enabled=True,
        identity_browser_origins=("https://clip-iisc.site",),
        database_url=case.target.dsn,
    )
    state = prepare_hosted_test_identity(
        settings,
        client=case.client,
        clock=lambda: NOW,
    )
    assert state.policy.origins == ("https://clip-iisc.site",)
    assert not state.policy.development
    assert case.client.calls == [
        REFS.authentication_keys,
        REFS.database_url,
        REFS.email_delivery,
    ]


def test_key_change_rejected_without_changing_persistent_binding(runtime_case):
    case = runtime_case
    state = bootstrap(case)
    with state.sessions.transaction():
        pass
    case.client.values[REFS.authentication_keys] = json.dumps(key_document())
    with pytest.raises(ConfigurationError, match="startup validation failed"):
        bootstrap(case)
    with case.target.admin() as c:
        assert c.execute(
            "SELECT count(*) FROM identity.otp_key_binding"
        ).fetchone() == (1,)


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE identity.forbidden_test(id int)",
        "TRUNCATE identity.contacts",
        "DELETE FROM identity.temporary_enrollments",
        "UPDATE identity.otp_key_binding SET key_version='changed'",
        "SELECT * FROM listings.sale_listings",
    ],
)
def test_actual_role_denies_ddl_other_data_and_guard_mutations(runtime_case, statement):
    bootstrap(runtime_case)
    connect = connection_factory(runtime_case.target.dsn, "test")
    with connect() as c:
        with pytest.raises(errors.InsufficientPrivilege):
            c.execute(statement)


@pytest.mark.parametrize(
    "change",
    [
        "REVOKE UPDATE ON identity.users FROM clip_test_identity_app",
        "REVOKE SELECT ON identity.notification_destinations FROM clip_test_identity_app",
        "GRANT TRUNCATE ON identity.notification_destinations TO clip_test_identity_app",
        "GRANT TRUNCATE ON identity.contacts TO clip_test_identity_app",
        "GRANT DELETE ON identity.temporary_enrollments TO clip_test_identity_app",
        "GRANT USAGE ON SCHEMA listings TO clip_test_identity_app; GRANT SELECT ON listings.sale_listings TO clip_test_identity_app",
    ],
)
def test_startup_rejects_missing_or_excess_permissions(runtime_case, change):
    case = runtime_case
    try:
        with case.target.admin() as c:
            c.execute(change)
        with pytest.raises(ConfigurationError):
            bootstrap(case)
    finally:
        with case.target.admin() as c:
            c.execute(
                "REVOKE ALL ON ALL TABLES IN SCHEMA identity,listings FROM clip_test_identity_app"
            )
            c.execute("REVOKE USAGE ON SCHEMA listings FROM clip_test_identity_app")
            c.execute(case.target.proposal)


def test_startup_rejects_superuser_and_logging_changes(runtime_case):
    case = runtime_case
    try:
        with case.target.admin() as c:
            c.execute("ALTER ROLE clip_test_identity_app SUPERUSER")
        with pytest.raises(ConfigurationError):
            bootstrap(case)
    finally:
        with case.target.admin() as c:
            c.execute("ALTER ROLE clip_test_identity_app NOSUPERUSER")
    try:
        with case.target.admin() as c:
            c.execute(
                "ALTER ROLE clip_test_identity_app SET log_min_error_statement='error'"
            )
        with pytest.raises(ConfigurationError):
            bootstrap(case)
    finally:
        with case.target.admin() as c:
            c.execute(case.target.proposal)


@pytest.mark.parametrize(
    "alter",
    [
        "missing",
        "extra",
        "wrong-version",
        "bool-version",
        "duplicate",
        "short",
        "reused",
        "bad-label",
        "not-json",
    ],
)
def test_invalid_persistent_key_payload_is_redacted(alter):
    row = key_document()
    if alter == "missing":
        del row["lookup"]
    elif alter == "extra":
        row["PRIVATE_SECRET"] = "PRIVATE_VALUE"
    elif alter == "wrong-version":
        row["schema_version"] = 2
    elif alter == "bool-version":
        row["schema_version"] = True
    elif alter == "short":
        row["lookup"] = base64.b64encode(b"short").decode()
    elif alter == "reused":
        row["lookup"] = row["verifier"]
    elif alter == "bad-label":
        row["key_version"] = "PRIVATE unsafe label"
    value = json.dumps(row)
    if alter == "duplicate":
        value = value[:-1] + ',"key_version":"different"}'
    elif alter == "not-json":
        value = "PRIVATE_NOT_JSON"
    with pytest.raises(ConfigurationError) as error:
        parse_authentication_keys(SecretStr(value))
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("Type", "String"),
        ("Version", True),
        ("Version", 0),
        ("Name", "/clip/wrong"),
        ("Value", "x" * 4097),
    ],
)
def test_secure_parameter_metadata_is_validated(field, value):
    class Invalid:
        def get_parameter(self, **kwargs):
            row = {
                "Name": REFS.authentication_keys,
                "Type": "SecureString",
                "Version": 1,
                "Value": "PRIVATE",
            }
            row[field] = value
            return {"Parameter": row}

    with pytest.raises(ConfigurationError) as error:
        read_secure_parameter(Invalid(), REFS.authentication_keys)
    assert "PRIVATE" not in str(error.value)


def test_no_automatic_bootstrap_or_unsafe_mode_reads():
    client = Parameters({})
    for settings in (
        Settings(environment="production"),
        Settings(environment="test"),
        Settings(environment="test", development_auth=True),
    ):
        with pytest.raises(ConfigurationError):
            prepare_local_identity(
                settings, BrowserPolicy(("https://clip-iisc.site",)), client=client
            )
    assert client.calls == []
    with pytest.raises(ValueError):
        RuntimeReferences(authentication_keys="/clip/prod/key")
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            email_provider="dual",
            ses_test_recipients=(EMAIL,),
        )


@pytest.mark.parametrize(
    "dsn,environment",
    [
        (
            "postgresql://clip_test_identity_app:PRIVATE@remote/unreviewed_database?sslmode=verify-full&sslrootcert=system",
            "test",
        ),
        (
            "postgresql://master:PRIVATE@remote/clip_test?sslmode=verify-full&sslrootcert=system",
            "local",
        ),
        (
            "postgresql://clip_test_identity_app:PRIVATE@remote/clip_test?sslmode=require",
            "local",
        ),
        (
            "postgresql://clip_test_identity_app:PRIVATE@remote/clip_test?sslmode=verify-full",
            "local",
        ),
        (
            "postgresql://clip_test_identity_app:PRIVATE@remote/clip_test?sslmode=verify-full&sslrootcert=system&options=unsafe",
            "local",
        ),
        (
            "postgresql://clip_test_identity_app:PRIVATE@remote/clip_test?sslmode=verify-full&sslrootcert=system",
            "production",
        ),
    ],
)
def test_database_transport_and_target_validation(dsn, environment):
    with pytest.raises(ConfigurationError) as error:
        connection_factory(SecretStr(dsn), environment)
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize("database", ["clip_test", "clip_next06_reference"])
def test_reviewed_hosted_databases_are_accepted_without_connecting(database):
    """The final dataset and its restored copy use the same strict transport."""
    connect = connection_factory(
        SecretStr(
            f"postgresql://clip_test_identity_app:PRIVATE@remote/{database}"
            "?sslmode=verify-full&sslrootcert=system"
        ),
        "test",
    )
    assert callable(connect)


def test_lambda_invocation_reuses_transport_but_closes_before_next_call(runtime_case):
    """Both thread helpers share one backend; the next invocation opens a new one."""
    import asyncio
    from starlette.concurrency import run_in_threadpool

    pooled = IdentityConnectionPool(
        runtime_case.target.dsn, "test", max_size=1, retain_idle=False
    )

    def read():
        with pooled() as connection, connection.transaction():
            return (
                connection.execute("SELECT pg_backend_pid()").fetchone()[0],
                connection,
            )

    async def exercise():
        async with pooled.invocation():
            first = await asyncio.to_thread(read)
            second = await run_in_threadpool(read)
            assert first[0] == second[0] and first[1] is second[1]
            assert pooled._pool.get_stats()["connections_num"] == 1
        assert first[1].closed
        assert pooled._pool.get_stats()["pool_size"] == 0
        async with pooled.invocation():
            third = await asyncio.to_thread(read)
            assert third[0] != first[0]
        assert third[1].closed

    try:
        asyncio.run(exercise())
    finally:
        pooled.close()


def test_lambda_invocation_preserves_rollback_and_fresh_logout(runtime_case):
    """Reuse does not cache decisions or carry a failed transaction into another call."""
    import asyncio
    from app.core.errors import PublicError
    from app.domains.identity.sessions import IdentitySessions

    state = bootstrap(runtime_case)
    mailbox = CaptureMail()
    challenge = state.sessions.challenges.start(
        EMAIL, "initial_verification", uuid4(), ip_address("192.0.2.27")
    )
    assert challenge.delivery.dispatch(mailbox, now=NOW)
    grant = state.sessions.activate(challenge.challenge_id, mailbox.code(), PASSWORD)
    pooled = IdentityConnectionPool(
        runtime_case.target.dsn, "test", max_size=1, retain_idle=False
    )
    service = IdentitySessions(
        pooled,
        parse_authentication_keys(SecretStr(json.dumps(runtime_case.document))),
        lambda: NOW,
    )

    def fail_then_read():
        with pytest.raises(errors.DivisionByZero):
            with pooled() as connection, connection.transaction():
                connection.execute("SELECT 1/0")
        with pooled() as connection, connection.transaction():
            assert connection.execute("SELECT 1").fetchone() == (1,)

    async def exercise():
        token = grant.token.get_secret_value()
        async with pooled.invocation():
            await asyncio.to_thread(fail_then_read)
            await asyncio.to_thread(service.authenticate, token)
            await asyncio.to_thread(state.sessions.logout, token)
            with pytest.raises(PublicError):
                await asyncio.to_thread(service.authenticate, token)
        async with pooled.invocation():
            with pytest.raises(PublicError):
                await asyncio.to_thread(service.authenticate, token)
        assert pooled._pool.get_stats()["pool_size"] == 0

    try:
        asyncio.run(exercise())
    finally:
        pooled.close()


def test_lambda_cancellation_joins_inflight_sql_before_releasing_scope(runtime_case):
    """A cancelled request cannot freeze a thread that will return an idle backend later."""
    import asyncio
    import threading

    pooled = IdentityConnectionPool(
        runtime_case.target.dsn, "test", max_size=1, retain_idle=False
    )
    started, finished = threading.Event(), threading.Event()
    connections = []

    def slow():
        with pooled() as connection:
            connections.append(connection)
            started.set()
            connection.execute("SELECT pg_sleep(0.1)")
            finished.set()

    async def request():
        async with pooled.invocation():
            await asyncio.to_thread(slow)

    async def exercise():
        task = asyncio.create_task(request())
        while not started.is_set():
            await asyncio.sleep(0.001)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert finished.is_set() and connections[0].closed
        assert pooled._pool.get_stats()["pool_size"] == 0

    try:
        asyncio.run(exercise())
    finally:
        pooled.close()
