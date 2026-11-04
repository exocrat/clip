"""Identity-only connection/role/key checks; never creates roles or grants access.

The reviewed runtime uses its own login, separately from the Listings pool.
Only explicit bootstrap calls connect. All diagnostics are fixed/redacted; no
connection string, database error, fingerprint or key is returned or logged.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import AbstractContextManager, asynccontextmanager, contextmanager
from contextvars import ContextVar
from threading import Lock
from typing import Callable

import psycopg
from psycopg.conninfo import conninfo_to_dict
from pydantic import SecretStr
from psycopg_pool import ConnectionPool, NullConnectionPool, PoolTimeout

from app.core.config import ConfigurationError
from app.core.database_transport import (
    uses_proxy,
    connection_kwargs,
    check_proxy_connection,
)
from app.domains.identity.temporary_challenges import Database
from app.domains.identity.temporary_crypto import TemporaryKeys

ROLE = "clip_test_identity_app"
# Both are reviewed test databases. Isolated restores retain the source database
# name; role, password and verified TLS checks below still apply to every host.
HOSTED_DATABASES = frozenset({"clip_test", "clip_next06_reference"})
# Permanent guards are append-only; users are retained and only updated/redacted.
APPEND_ONLY = frozenset(
    {
        "external_identities",
        "temporary_enrollments",
        "otp_key_binding",
        "otp_operations",
    }
)
TABLES = frozenset(
    {
        "users",
        "external_identities",
        "contacts",
        "temporary_credentials",
        "sessions",
        "otp_challenges",
        "temporary_enrollments",
        "otp_key_binding",
        "otp_operations",
        "otp_send_reservations",
        "otp_verification_windows",
        "password_login_windows",
        "auth_source_events",
        "microsoft_login_attempts",
    }
)
# Keep TABLES as the historical bootstrap grant manifest; current runtime also
# needs the encrypted notification destination introduced by CN-03.
RUNTIME_TABLES = TABLES | {"notification_destinations"}
PRIVILEGES = (
    "SELECT",
    "INSERT",
    "UPDATE",
    "DELETE",
    "TRUNCATE",
    "REFERENCES",
    "TRIGGER",
    "MAINTAIN",
)


def connection_factory(dsn: SecretStr, environment: str) -> Callable[[], Database]:
    """Validate a private URI and return fresh bounded non-pooled connections.

    Remote targets require certificate/hostname verification with system roots.
    Only test-mode private Unix sockets may disable TLS, against clip_test_identity.
    No service/passfile/options or ambient multi-host fallback is accepted.
    """
    try:
        raw = dsn.get_secret_value()
        if environment not in {"local", "test"} or not raw.startswith(
            ("postgres://", "postgresql://")
        ):
            raise ValueError
        values = conninfo_to_dict(raw)
        if set(values) - {
            "host",
            "port",
            "dbname",
            "user",
            "password",
            "sslmode",
            "sslrootcert",
        }:
            raise ValueError
        host = values.get("host", "")
        if (
            not isinstance(host, str)
            or not host
            or "," in host
            or values.get("user") != ROLE
        ):
            raise ValueError
        if host.startswith("/"):
            if (
                environment != "test"
                or values.get("dbname") != "clip_test_identity"
                or values.get("sslmode") != "disable"
            ):
                raise ValueError
        elif (
            values.get("dbname") not in HOSTED_DATABASES
            or not values.get("password")
            or values.get("sslmode") != "verify-full"
            or values.get("sslrootcert") != "system"
        ):
            raise ValueError
        if not values.get("password"):
            raise ValueError
        raw_port = values.get("port", "5432")
        if not isinstance(raw_port, (str, int)):
            raise ValueError
        port = int(raw_port)
        if not 1 <= port <= 65535:
            raise ValueError
    except Exception:
        raise ConfigurationError("Invalid Identity database configuration") from None

    def connect() -> Database:
        """Open with explicit credentials/timeouts and no local passfile lookup."""
        try:
            connection = psycopg.connect(
                raw,
                **connection_kwargs(
                    raw,
                    passfile="/dev/null",
                    connect_timeout=3,
                    application_name="clip-identity",
                    autocommit=True,
                ),
            )
            try:
                check_proxy_connection(connection)
            except BaseException:
                connection.close()
                raise
            return connection
        except Exception:
            raise ConfigurationError("Identity database unavailable") from None

    return connect


class _InvocationConnection:
    """One exclusive connection shared by this invocation's separate transactions.

    A borrower never shares an active transaction with another thread. Cleanup
    waits for an in-flight borrower, then returns the lease to the null pool,
    which physically closes it before the HTTP response can complete.
    """

    def __init__(self, pool: ConnectionPool):
        self._pool = pool
        self._lock = Lock()
        self._lease: AbstractContextManager[Database] | None = None
        self._connection: Database | None = None
        self._closed = False

    @contextmanager
    def borrow(self) -> Iterator[Database]:
        if not self._lock.acquire(timeout=1):
            raise PoolTimeout("Identity invocation connection busy")
        try:
            if self._closed:
                raise ConfigurationError("Identity invocation has finished")
            if self._connection is None:
                lease = self._pool.connection(timeout=1)
                connection = lease.__enter__()
                self._lease, self._connection = lease, connection
            yield self._connection
        finally:
            self._lock.release()

    def close(self) -> None:
        """Join any remaining SQL borrower; never leave a late idle connection."""
        with self._lock:
            self._closed = True
            lease, self._lease = self._lease, None
            self._connection = None
            if lease is not None:
                lease.__exit__(None, None, None)


class IdentityConnectionPool:
    """Reuse bounded, exclusive connections without caching authentication state.

    Every borrower still runs the existing transactions, current-account checks,
    session expiry and revocation checks. Acquisition waits at most one second;
    at most64 callers may queue. SQL and transaction timeouts bound a stalled
    borrower. A zero minimum avoids idle Lambda connections and import-time I/O.
    """

    def __init__(
        self,
        dsn: SecretStr,
        environment: str,
        *,
        max_size: int,
        retain_idle: bool = True,
    ) -> None:
        """Validate the same role/TLS/target policy before constructing a lazy pool."""
        connection_factory(dsn, environment)
        if type(max_size) is not int or not 1 <= max_size <= 4:
            raise ConfigurationError("Invalid Identity pool bound")
        self._lock = Lock()
        self._opened = False
        self._retain_idle = retain_idle
        self._request_lease: ContextVar[_InvocationConnection | None] = ContextVar(
            "clip_identity_request_connection", default=None
        )
        pool_type = ConnectionPool if retain_idle else NullConnectionPool
        self._pool: ConnectionPool = pool_type(
            conninfo=dsn.get_secret_value(),
            kwargs=connection_kwargs(
                dsn.get_secret_value(),
                **{
                    "passfile": "/dev/null",
                    "connect_timeout": 3,
                    "application_name": "clip-identity-pooled",
                    "autocommit": True,
                    "options": "-c statement_timeout=5000 -c lock_timeout=3000 -c idle_in_transaction_session_timeout=5000",
                },
            ),
            configure=check_proxy_connection,
            check=(
                ConnectionPool.check_connection
                if uses_proxy(dsn.get_secret_value())
                else None
            ),
            min_size=0,
            max_size=max_size,
            max_waiting=64,
            timeout=1,
            max_idle=60,
            open=False,
        )

    @contextmanager
    def __call__(self) -> Iterator[Database]:
        """Return an exclusive lease; pool context commits/rolls back before reuse."""
        with self._lock:
            if not self._opened:
                self._pool.open(wait=False)
                self._opened = True
        invocation = self._request_lease.get()
        if invocation is not None:
            with invocation.borrow() as connection:
                yield connection
            return
        with self._pool.connection(timeout=1) as connection:
            yield connection

    @asynccontextmanager
    async def invocation(self) -> AsyncIterator[None]:
        """Reuse physical Identity transport, never authorization, within one call.

        Context propagates into both supported thread helpers. Every Identity
        operation retains its original SQL/transaction. Cleanup is completed
        through cancellation; the HTTP integration holds the terminal body until
        this scope exits, so Lambda cannot freeze an idle retained connection.
        """
        if self._retain_idle:
            raise ConfigurationError("Invocation cleanup requires a null pool")
        if self._request_lease.get() is not None:
            raise ConfigurationError("Nested Identity invocation scope")
        invocation = _InvocationConnection(self._pool)
        token = self._request_lease.set(invocation)
        try:
            yield
        finally:
            self._request_lease.reset(token)
            cleanup = asyncio.create_task(asyncio.to_thread(invocation.close))
            while True:
                try:
                    await asyncio.shield(cleanup)
                    break
                except asyncio.CancelledError:
                    if cleanup.cancelled():
                        raise
                    if cleanup.done():
                        cleanup.result()
                        break

    def close(self) -> None:
        """Close only this app's pool after request and worker shutdown."""
        with self._lock:
            self._pool.close()


def validate_database(
    connect: Callable[[], AbstractContextManager[Database]], keys: TemporaryKeys
) -> None:
    """Read-only startup audit of effective privileges, logging and stable keys.

    Reject elevated/wrong/session-switched roles, CREATE/TEMP, schema ownership,
    missing or extra table privileges and wrong key commitments. Empty first
    adoption remains the existing transaction's responsibility; no startup data
    mutation or credential/key regeneration is performed here.
    """
    phase = "connection"
    try:
        with connect() as c, c.transaction():
            c.execute("SET TRANSACTION READ ONLY")
            c.execute("SET LOCAL statement_timeout = '5s'")
            c.execute("SET LOCAL lock_timeout = '3s'")
            phase = "role"
            row = c.execute("""
                SELECT current_user, session_user, rolcanlogin, rolsuper,
                       rolcreatedb, rolcreaterole, rolinherit, rolreplication, rolbypassrls,
                       has_database_privilege(current_database(), 'CREATE'),
                       has_database_privilege(current_database(), 'TEMPORARY'),
                       EXISTS(SELECT 1 FROM pg_auth_members WHERE member=r.oid),
                       EXISTS(SELECT 1 FROM pg_namespace WHERE has_schema_privilege(oid,'CREATE'))
                FROM pg_roles r WHERE rolname=current_user
            """).fetchone()
            if row != (
                ROLE,
                ROLE,
                True,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
            ):
                raise ValueError
            phase = "logging"
            logging = c.execute("""
                SELECT current_setting('log_statement'), current_setting('log_min_duration_statement'),
                       current_setting('log_min_duration_sample'), current_setting('log_transaction_sample_rate'),
                       current_setting('log_min_error_statement'), current_setting('log_parameter_max_length_on_error'),
                       current_setting('pgaudit.log', true), current_setting('auto_explain.log_min_duration', true)
            """).fetchone()
            if logging is None or logging[:6] != (
                "none",
                "-1",
                "-1",
                "0",
                "panic",
                "0",
            ):
                raise ValueError
            if logging[6] not in (None, "", "none") or logging[7] not in (
                None,
                "",
                "-1",
            ):
                raise ValueError
            phase = "migration versions"
            versions = {
                r[0]
                for r in c.execute(
                    "SELECT version FROM public.schema_migrations"
                ).fetchall()
            }
            if (
                not {
                    "20261023173439",
                    "20261023192856",
                    "20261023202807",
                    "20261029133500",
                    "20261029182500",
                }
                <= versions
            ):
                raise ValueError
            phase = "required privileges"
            for table in RUNTIME_TABLES:
                expected = {"SELECT", "INSERT"}
                if table not in APPEND_ONLY:
                    expected.add("UPDATE")
                    if table != "users":
                        expected.add("DELETE")
                for privilege in PRIVILEGES:
                    result = c.execute(
                        "SELECT has_table_privilege(%s,%s)",
                        ("identity." + table, privilege),
                    ).fetchone()
                    if result is None or result[0] != (privilege in expected):
                        raise ValueError
            # No access to other owners' data, including future Identity tables.
            phase = "other table privileges"
            others = c.execute("""
                SELECT n.nspname,c.relname,c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE c.relkind IN ('r','p','v','m','S','f') AND n.nspname NOT IN ('pg_catalog','information_schema')
                  AND n.nspname NOT LIKE 'pg_toast%%' AND n.nspname NOT LIKE 'pg_temp%%'
            """).fetchall()
            for schema, table, oid in others:
                if schema == "identity" and table in RUNTIME_TABLES:
                    continue
                if schema == "public" and table == "schema_migrations":
                    allowed = {"SELECT"}
                else:
                    allowed = set()
                for privilege in PRIVILEGES:
                    result = c.execute(
                        "SELECT has_table_privilege(%s,%s)",
                        (oid, privilege),
                    ).fetchone()
                    if result is None or result[0] != (privilege in allowed):
                        raise ValueError
            phase = "key commitments"
            binding = c.execute(
                "SELECT key_version,lookup_fingerprint,verifier_fingerprint,encryption_fingerprint FROM identity.otp_key_binding WHERE singleton"
            ).fetchone()
            if binding is not None:
                if binding != (keys.version, *keys.fingerprints()):
                    raise ValueError
            else:
                occupied = c.execute("""
                    SELECT EXISTS(SELECT 1 FROM identity.temporary_credentials)
                    OR EXISTS(SELECT 1 FROM identity.temporary_enrollments)
                    OR EXISTS(SELECT 1 FROM identity.otp_challenges)
                    OR EXISTS(SELECT 1 FROM identity.auth_source_events)
                    OR EXISTS(SELECT 1 FROM identity.microsoft_login_attempts)
                    OR EXISTS(SELECT 1 FROM identity.sessions WHERE last_seen_at IS NOT NULL)
                """).fetchone()
                if occupied != (False,):
                    raise ValueError
    except Exception:
        raise ConfigurationError(
            "Identity database safety checks failed during " + phase
        ) from None
