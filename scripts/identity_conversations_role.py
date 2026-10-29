"""Explicit role-only operator helper; import never connects or calls AWS.

Live invocation requires its own exact target/SQL/credential/cloud approval.
The caller privately supplies connections and a newly generated password, then
stores the returned login's DSN through the separately approved SSM procedure.
There is no schema migration, existing-role rotation, PUBLIC ACL repair, cleanup
worker permission, automatic retry or parameter creation here.
"""

from pathlib import Path
import hashlib
from typing import Callable
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

from psycopg import sql
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = (
    ROOT / "docs/evaluation/identity/id-01-step-14/conversations-runtime.sql.proposed"
)
APPROVED_SQL_SHA256 = "6822fd82bc1d75c262d55227a385c8ca63a7aca155c8dc1b4df3c19dd73eee13"
ROLE = "clip_test_conversations_app"
HOST = "clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com"
LOGGING = {
    "log_statement": "none",
    "log_min_duration_statement": "-1",
    "log_min_duration_sample": "-1",
    "log_transaction_sample_rate": "0",
    "log_min_error_statement": "panic",
    "log_parameter_max_length_on_error": "0",
}
TABLES = {
    name: (
        {"SELECT", "INSERT", "UPDATE"}
        if name
        in {
            "threads",
            "members",
            "public_key_versions",
            "entries",
            "offers",
            "public_prekeys",
            "notification_intents",
        }
        else {"SELECT", "INSERT"}
    )
    for name in (
        "threads",
        "members",
        "public_key_versions",
        "entries",
        "offers",
        "public_prekeys",
        "notification_intents",
        "encrypted_payloads",
        "offer_revisions",
        "contact_shares",
        "recovery_families",
        "key_directory_operations",
        "origin_retirement_operations",
    )
}


class RoleSetupFailure(Exception):
    """Fixed safe failure; never serialize nested SQL/DSN/credential diagnostics."""


def require(condition: bool) -> None:
    """Reject unexpected state before applying or committing any role changes."""
    if not condition:
        raise RoleSetupFailure(
            "Conversations role setup refused; inspect approved target/state"
        )


def _target(connection, *, isolated: bool) -> None:
    """Verify real connection identity/transport, version and inherited privileges."""
    expected = (
        ("clip_test_identity", "clip_identity_ci")
        if isolated
        else ("clip_test", "clip_test_admin")
    )
    row = connection.execute(
        "SELECT current_database(),current_user,session_user,inet_server_addr() IS NULL"
    ).fetchone()
    require(row[:3] == (expected[0], expected[1], expected[1]))
    if isolated:
        require(row[3] is True and connection.info.host.startswith("/"))
    else:
        require(connection.info.host == HOST and connection.info.port == 5432)
        require(
            connection.pgconn.ssl_in_use
            and connection.info.get_parameters().get("sslmode") == "verify-full"
        )
    require(
        connection.execute(
            "SELECT count(*),max(version) FROM public.schema_migrations"
        ).fetchone()
        == (23, "20261027112205")
    )
    require(
        not connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,)
        ).fetchone()
    )
    for name in ("pgaudit.log", "auto_explain.log_min_duration"):
        value = connection.execute(
            "SELECT current_setting(%s,true)", (name,)
        ).fetchone()[0]
        require(value in (None, "", "none", "-1"))
    # NOINHERIT does not remove PUBLIC rights. Refuse; never repair shared ACLs.
    require(connection.execute("""
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
          SELECT 1 FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace,
          LATERAL aclexplode(t.relacl) a
          WHERE a.grantee=0 AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%%'
        ) OR EXISTS (
          SELECT 1 FROM pg_default_acl d,LATERAL aclexplode(d.defaclacl) a
          WHERE a.grantee=0 AND d.defaclobjtype IN ('r','S')
        )
    """).fetchone() == (False,))


def provision(
    connect: Callable,
    password: SecretStr,
    *,
    approved_sql_sha256: str,
    isolated: bool = False,
) -> dict:
    """Create one absent login/grants atomically; caller owns secret storage/recovery.

    Connection failure/uncertain commit is never retried. On ambiguous outcome,
    stop and inspect the exact role/SSM state under the approved recovery plan.
    Password remains only in caller/process memory and protected SQL transport.
    """
    try:
        source = PROPOSAL.read_bytes()
        require(
            approved_sql_sha256
            == APPROVED_SQL_SHA256
            == hashlib.sha256(source).hexdigest()
        )
        require(len(password.get_secret_value()) >= 32)
        with connect() as connection, connection.transaction():
            # Apply privacy before any statement containing the new credential.
            for name, value in LOGGING.items():
                connection.execute(
                    sql.SQL("SET LOCAL {} = {}").format(
                        sql.Identifier(name), sql.Literal(value)
                    )
                )
            connection.execute("SET LOCAL lock_timeout='5s'")
            connection.execute("SET LOCAL statement_timeout='10s'")
            _target(connection, isolated=isolated)
            connection.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2 PASSWORD {}"
                ).format(sql.Identifier(ROLE), sql.Literal(password.get_secret_value()))
            )
            connection.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(connection.info.dbname), sql.Identifier(ROLE)
                )
            )
            connection.execute(source.decode(), prepare=False)
            # Check every effective privilege on project tables, not only direct ACLs.
            for schema, table, kind in connection.execute(
                "SELECT n.nspname,c.relname,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p','v','m','S') AND n.nspname IN ('identity','listings','search','conversations','public')"
            ):
                expected = (
                    TABLES.get(table, set()) if schema == "conversations" else set()
                )
                for privilege in (
                    "SELECT",
                    "INSERT",
                    "UPDATE",
                    "DELETE",
                    "TRUNCATE",
                    "REFERENCES",
                    "TRIGGER",
                    "MAINTAIN",
                ):
                    # Sequences have their own privilege vocabulary; no grants allowed.
                    if kind == "S":
                        require(
                            not connection.execute(
                                "SELECT has_sequence_privilege(%s,%s,'USAGE,SELECT,UPDATE')",
                                (ROLE, schema + "." + table),
                            ).fetchone()[0]
                        )
                        break
                    allowed = connection.execute(
                        "SELECT has_table_privilege(%s,%s,%s)",
                        (ROLE, schema + "." + table, privilege),
                    ).fetchone()[0]
                    require(allowed == (privilege in expected))
        return {
            "role": ROLE,
            "sql_sha256": APPROVED_SQL_SHA256,
            "role_created": True,
            "ssm_written": False,
        }
    except Exception:
        raise RoleSetupFailure(
            "Conversations role setup stopped; no automatic retry; inspect approved target/state"
        ) from None


def credential_uri(base: SecretStr, password: SecretStr) -> SecretStr:
    """Build the new private runtime URI while retaining reviewed TLS/CA options.

    Never returns plaintext through repr/print; callers must not serialize the
    SecretStr value to logs, CLI arguments or ordinary Terraform input/state.
    """
    try:
        parts = urlsplit(base.get_secret_value())
        require(
            parts.scheme == "postgresql"
            and parts.hostname == HOST
            and parts.port in (None, 5432)
            and parts.path == "/clip_test"
        )
        query = parse_qs(parts.query)
        require(
            query.get("sslmode") == ["verify-full"] and bool(query.get("sslrootcert"))
        )
        require(
            set(query)
            <= {"sslmode", "sslrootcert", "connect_timeout", "application_name"}
        )
        require(all(len(values) == 1 for values in query.values()))
        require(
            (
                query["sslrootcert"][0] == "system"
                or query["sslrootcert"][0].startswith("/")
            )
            and "\x00" not in query["sslrootcert"][0]
        )
        require(not parts.fragment and len(password.get_secret_value()) >= 32)
        authority = (
            quote(ROLE, safe="")
            + ":"
            + quote(password.get_secret_value(), safe="")
            + "@"
            + HOST
            + ":5432"
        )
        return SecretStr(urlunsplit(parts._replace(netloc=authority)))
    except Exception:
        raise RoleSetupFailure("Conversations credential URI refused") from None
