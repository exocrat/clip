"""Read-only operator diagnostics; no provider, secrets, migrations or role writes.

Missing schema objects are findings, not query errors. A later SQL/connection
failure returns only completed safe fields and a code-owned phase label. This is
not an authorization gate: the existing setup/runtime validators still apply.
"""

from dataclasses import dataclass, field
from typing import Callable

from app.domains.identity.database_setup import LOGGING, VERSIONS
from app.domains.identity.runtime_database import ROLE, TABLES
from app.domains.identity.temporary_challenges import Database

MetadataValue = bool | int | list[str] | dict[str, bool]


@dataclass
class DatabaseMetadata:
    """Serializable allowlisted findings; never raw SQL exceptions or row dumps."""

    complete: bool = False
    failed_phase: str | None = None
    checks: dict[str, MetadataValue] = field(default_factory=dict)


def collect_database_metadata(
    connect: Callable[[], Database], *, expected_database: str, expected_admin: str
) -> DatabaseMetadata:
    """Collect a bounded repeatable read-only snapshot, retaining safe partial data.

    Connections/credentials/TLS and total process time remain the approved caller's
    responsibility. This neither reads secrets nor retries or fixes any failure.
    No relation content is read except known migration-version identifiers.
    """
    result = DatabaseMetadata()
    phase = "target"
    try:
        if (
            expected_database not in {"clip_test", "clip_test_identity"}
            or not expected_admin
        ):
            raise ValueError
        phase = "connection"
        with connect() as c, c.transaction():
            c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            c.execute("SET LOCAL statement_timeout='5s'")
            c.execute("SET LOCAL lock_timeout='3s'")
            phase = "target"
            matched = c.execute(
                "SELECT current_database(),current_user,session_user"
            ).fetchone() == (expected_database, expected_admin, expected_admin)
            result.checks["target_matches"] = matched
            if not matched:
                raise ValueError
            phase = "migration relation"
            relation = c.execute("""
                SELECT c.relkind, EXISTS (
                  SELECT 1 FROM pg_attribute a WHERE a.attrelid=c.oid
                    AND a.attname='version' AND NOT a.attisdropped
                ) FROM pg_class c WHERE c.oid=to_regclass('public.schema_migrations')
            """).fetchone()
            result.checks["migration_relation_exists"] = relation is not None
            readable = (
                relation is not None and relation[0] in {"r", "p"} and relation[1]
            )
            result.checks["migration_relation_supported"] = bool(readable)
            phase = "migration versions"
            versions = set()
            if readable:
                versions = {
                    r[0]
                    for r in c.execute(
                        "SELECT version FROM public.schema_migrations WHERE version=ANY(%s)",
                        (sorted(VERSIONS),),
                    )
                }
            result.checks["required_migrations"] = {
                v: v in versions for v in sorted(VERSIONS)
            }
            phase = "Identity inventory"
            tables = {r[0] for r in c.execute("""
                SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='identity' AND c.relkind IN ('r','p')
            """)}
            result.checks["identity_table_count"] = len(tables)
            result.checks["identity_table_inventory_matches"] = tables == TABLES
            result.checks["missing_identity_tables"] = sorted(TABLES - tables)
            phase = "role collision"
            result.checks["identity_role_exists"] = (
                c.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,)).fetchone()
                is not None
            )
            phase = "logging"
            safe = {}
            permissions = {}
            for name, expected in LOGGING.items():
                safe[name] = c.execute(
                    "SELECT current_setting(%s)", (name,)
                ).fetchone() == (expected,)
                permissions[name] = c.execute(
                    "SELECT has_parameter_privilege(current_user,%s,'SET')", (name,)
                ).fetchone() == (True,)
            result.checks["safe_logging"] = safe
            result.checks["can_set_logging"] = permissions
            for name, allowed, label in (
                ("pgaudit.log", {None, "", "none"}, "audit_disabled"),
                (
                    "auto_explain.log_min_duration",
                    {None, "", "-1"},
                    "auto_explain_disabled",
                ),
            ):
                row = c.execute("SELECT current_setting(%s,true)", (name,)).fetchone()
                result.checks[label] = row is not None and row[0] in allowed
            phase = "PUBLIC grants"
            for label, query in (
                (
                    "public_database_grant_count",
                    """
                    SELECT count(*) FROM pg_database d,
                    LATERAL aclexplode(coalesce(d.datacl,acldefault('d',d.datdba))) a
                    WHERE d.datname=current_database() AND a.grantee=0
                      AND a.privilege_type IN ('CONNECT','CREATE','TEMPORARY')
                """,
                ),
                (
                    "public_schema_create_count",
                    """
                    SELECT count(*) FROM pg_namespace n,
                    LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a
                    WHERE a.grantee=0 AND a.privilege_type='CREATE'
                """,
                ),
                (
                    "public_relation_grant_count",
                    """
                    SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
                    LATERAL aclexplode(c.relacl) a
                    WHERE a.grantee=0 AND n.nspname NOT IN ('pg_catalog','information_schema')
                      AND n.nspname NOT LIKE 'pg_%%'
                """,
                ),
                (
                    "public_default_relation_grant_count",
                    """
                    SELECT count(*) FROM pg_default_acl d,LATERAL aclexplode(d.defaclacl) a
                    WHERE a.grantee=0 AND d.defaclobjtype IN ('r','S')
                """,
                ),
            ):
                row = c.execute(query).fetchone()
                if row is None:
                    raise ValueError
                result.checks[label] = int(row[0])
            phase = "transaction completion"
        result.complete = True
    except Exception:
        result.failed_phase = phase
    return result
