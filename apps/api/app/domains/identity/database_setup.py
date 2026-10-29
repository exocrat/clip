"""Explicit operator-only Identity login setup; never imported by API startup.

Local tests exercise this procedure. Live use requires separately reviewed private
execution, exact target/credentials and cloud/database approval. It reads catalog
metadata only and never repairs PUBLIC grants, migrates schemas or touches users.
"""

from typing import Callable

from psycopg import sql
from pydantic import SecretStr

from app.core.config import ConfigurationError
from app.domains.identity.runtime_database import APPEND_ONLY, ROLE, RUNTIME_TABLES
from app.domains.identity.temporary_challenges import Database

VERSIONS = frozenset(
    {
        "20261023173439",
        "20261023192856",
        "20261023202807",
        "20261029133500",
        "20261029182500",
    }
)
LOGGING = {
    "log_statement": "none",
    "log_min_duration_statement": "-1",
    "log_min_duration_sample": "-1",
    "log_transaction_sample_rate": "0",
    "log_min_error_statement": "panic",
    "log_parameter_max_length_on_error": "0",
}


def _preflight(c: Database, expected_database: str, expected_admin: str) -> None:
    """Check this bounded session before any credential or role SQL is submitted."""
    if expected_database not in {"clip_test", "clip_test_identity"}:
        raise ValueError
    if c.execute("SELECT current_database(),current_user,session_user").fetchone() != (
        expected_database,
        expected_admin,
        expected_admin,
    ):
        raise ValueError
    for name, expected in LOGGING.items():
        if c.execute("SELECT current_setting(%s)", (name,)).fetchone() != (expected,):
            raise ValueError
    for name, allowed in (
        ("pgaudit.log", {None, "", "none"}),
        ("auto_explain.log_min_duration", {None, "", "-1"}),
    ):
        row = c.execute("SELECT current_setting(%s,true)", (name,)).fetchone()
        if row is None or row[0] not in allowed:
            raise ValueError
    if c.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,)).fetchone():
        raise ValueError
    # PUBLIC privileges are inherited even by NOINHERIT roles. Never revoke them
    # automatically: they may be supporting another contributor's workload.
    if c.execute("""
        SELECT EXISTS (
          SELECT 1 FROM pg_database d,
          LATERAL aclexplode(coalesce(d.datacl,acldefault('d',d.datdba))) a
          WHERE d.datname=current_database() AND a.grantee=0
            AND a.privilege_type IN ('CONNECT','CREATE','TEMPORARY')
        ) OR EXISTS (
          SELECT 1 FROM pg_namespace n,
          LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a
          WHERE a.grantee=0 AND a.privilege_type='CREATE'
        ) OR EXISTS (
          SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
          LATERAL aclexplode(c.relacl) a
          WHERE a.grantee=0 AND n.nspname NOT IN ('pg_catalog','information_schema')
            AND n.nspname NOT LIKE 'pg_%%'
        ) OR EXISTS (
          SELECT 1 FROM pg_default_acl d,LATERAL aclexplode(d.defaclacl) a
          WHERE a.grantee=0 AND d.defaclobjtype IN ('r','S')
        )
    """).fetchone() != (False,):
        raise ValueError
    versions = {
        row[0] for row in c.execute("SELECT version FROM public.schema_migrations")
    }
    if not VERSIONS <= versions:
        raise ValueError
    tables = {row[0] for row in c.execute("""
            SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='identity' AND c.relkind IN ('r','p')
        """)}
    if tables != RUNTIME_TABLES:
        raise ValueError


def inspect_identity_database(
    connect: Callable[[], Database], *, expected_database: str, expected_admin: str
) -> None:
    """Read-only metadata preflight; emit only fixed errors, not database details."""
    try:
        with connect() as c, c.transaction():
            c.execute("SET TRANSACTION READ ONLY")
            c.execute("SET LOCAL statement_timeout='5s'")
            c.execute("SET LOCAL lock_timeout='3s'")
            _preflight(c, expected_database, expected_admin)
    except Exception:
        raise ConfigurationError("Identity database setup preflight rejected") from None


def create_identity_role(
    connect: Callable[[], Database],
    password: SecretStr,
    *,
    expected_database: str,
    expected_admin: str,
) -> None:
    """Create one role/grants atomically; no overwrite, secret persistence or retry.

    The caller retains the generated password privately until separately approved
    publication, and must handle an ambiguous commit by inspecting metadata before
    any retry. SCRAM is computed client-side; plaintext never enters SQL. Safe
    effective logging is required before even the verifier can be submitted.
    A failure rolls back role/password/grants together when the outcome is known.
    """
    try:
        raw = password.get_secret_value()
        if len(raw) < 32 or len(raw) > 256 or not raw.isascii() or not raw.isalnum():
            raise ValueError
        with connect() as c, c.transaction():
            c.execute("SET LOCAL statement_timeout='5s'")
            c.execute("SET LOCAL lock_timeout='3s'")
            c.execute("SELECT pg_advisory_xact_lock(8736241101)")
            _preflight(c, expected_database, expected_admin)
            verifier = c.pgconn.encrypt_password(
                raw.encode("ascii"), ROLE.encode("ascii"), b"scram-sha-256"
            ).decode("ascii")
            role = sql.Identifier(ROLE)
            c.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10 PASSWORD {}"
                ).format(role, sql.Literal(verifier))
            )
            for name, value in LOGGING.items():
                c.execute(
                    sql.SQL("ALTER ROLE {} SET {} = {}").format(
                        role, sql.Identifier(name), sql.Literal(value)
                    )
                )
            c.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(expected_database), role
                )
            )
            c.execute(
                sql.SQL("GRANT USAGE ON SCHEMA identity,public TO {}").format(role)
            )
            c.execute(
                sql.SQL("GRANT SELECT ON public.schema_migrations TO {}").format(role)
            )
            for table in sorted(RUNTIME_TABLES):
                privileges = ["SELECT", "INSERT"]
                if table not in APPEND_ONLY:
                    privileges.append("UPDATE")
                    if table != "users":
                        privileges.append("DELETE")
                c.execute(
                    sql.SQL("GRANT {} ON {} TO {}").format(
                        sql.SQL(",").join(map(sql.SQL, privileges)),
                        sql.Identifier("identity", table),
                        role,
                    )
                )
    except Exception:
        raise ConfigurationError("Identity database role setup failed") from None
