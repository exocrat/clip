"""Identity-only connection/role/key checks; never creates roles or grants access.

The reviewed runtime uses its own login, separately from the Listings pool.
Only explicit bootstrap calls connect. All diagnostics are fixed/redacted; no
connection string, database error, fingerprint or key is returned or logged.
"""

from typing import Callable

import psycopg
from psycopg.conninfo import conninfo_to_dict
from pydantic import SecretStr

from app.core.config import ConfigurationError
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
            return psycopg.connect(
                raw,
                passfile="/dev/null",
                connect_timeout=3,
                application_name="clip-identity",
                autocommit=True,
            )
        except Exception:
            raise ConfigurationError("Identity database unavailable") from None

    return connect


def validate_database(connect: Callable[[], Database], keys: TemporaryKeys) -> None:
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
