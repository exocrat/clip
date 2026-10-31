"""Create-only NEXT-06 isolated database preparation, never an app startup path.

The caller separately owns exact cloud approval, fixed admin access and stopped
closeout. New loader/runtime roles remain NOLOGIN with no password. Credential
publication/activation, data/media loading and runtime grants are later gates.
Failure retains the exact created artifacts for reviewed recovery; no drop/reset,
resume, adoption, shared database ACL repair or credential rotation is provided.
"""

import hashlib
from pathlib import Path

from scripts.evaluation.reference_admin_inventory import ADMIN, HOST, LOGGING, PORT

ROOT = Path(__file__).resolve().parents[2]
DATABASE = "clip_next06_reference"
LOADER = "clip_next06_loader"
RUNTIME = "clip_next06_runtime"
TABLES = (
    "identity.users",
    "listings.sale_listings",
    "listings.image_uploads",
    "listings.images",
)
READ_TABLES = (
    "listings.categories",
    "listings.conditions",
    "listings.embedding_pipelines",
    "public.schema_migrations",
)


class SetupRefused(Exception):
    """A fixed failure code; raw SQL/provider errors must never reach evidence."""


def migration_sources(binding):
    """Re-read exactly the corpus-pinned migration bytes; return reviewed UP SQL.

    This uses dbmate's UP/DOWN sections and version tracker format, executing only
    the complete UP sections in sorted order. Unsupported marker/options fail;
    no source rewriting, DOWN execution or automatic schema reconciliation.
    """
    entries = [
        e for e in binding["files"] if e["path"].startswith("database/migrations/")
    ]
    paths = sorted((ROOT / "database/migrations").glob("*.sql"))
    if len(entries) != 29 or [e["path"] for e in entries] != [
        str(p.relative_to(ROOT)) for p in paths
    ]:
        raise SetupRefused("migration_set_changed")
    result = []
    for entry, path in zip(entries, paths, strict=True):
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise SetupRefused("migration_content_changed")
        text = raw.decode()
        if text.count("-- migrate:up") != 1 or text.count("-- migrate:down") != 1:
            raise SetupRefused("unsupported_migration_markers")
        up, down = text.split("-- migrate:up", 1)[1].split("-- migrate:down", 1)
        if not up.startswith("\n") or "-- migrate:" in up or "-- migrate:" in down:
            raise SetupRefused("unsupported_migration_options")
        result.append((path.name.split("_", 1)[0], up))
    if [v for v, _ in result] != binding["migration_versions"]:
        raise SetupRefused("migration_versions_changed")
    return result


def guard(connection, database, *, owned_socket=None):
    """Bind exact admin/session/version/privacy/transport before DDL or migration.

    The explicit native socket route is restricted to the fresh rehearsal's
    private directory. Production never accepts a socket or TLS downgrade.
    """
    if connection.autocommit is not True:
        raise SetupRefused("autocommit_required_for_create_database")
    row = connection.execute(
        "SELECT current_database(),current_user,session_user,current_setting('server_version_num')"
    ).fetchone()
    if row != (database, ADMIN, ADMIN, "180006"):
        raise SetupRefused("admin_target_changed")
    if owned_socket is None:
        params = connection.info.get_parameters()
        if (
            connection.info.host != HOST
            or connection.info.port != PORT
            or params.get("hostaddr") != "127.0.0.1"
            or params.get("sslmode") != "verify-full"
            or not connection.pgconn.ssl_in_use
        ):
            raise SetupRefused("private_tls_required")
    elif (
        not isinstance(owned_socket, Path)
        or not owned_socket.is_absolute()
        or not str(owned_socket).startswith("/private/tmp/clip-next06-reference-")
        or owned_socket.name != "pgsocket"
        or connection.info.host != str(owned_socket)
        or connection.info.port != 55438
        or owned_socket.is_symlink()
    ):
        raise SetupRefused("owned_native_socket_required")
    for name, expected in LOGGING.items():
        if connection.execute("SELECT current_setting(%s)", (name,)).fetchone() != (
            expected,
        ):
            raise SetupRefused("privacy_settings_changed")
    for name in ("pgaudit.log", "auto_explain.log_min_duration"):
        if connection.execute("SELECT current_setting(%s,true)", (name,)).fetchone()[
            0
        ] not in (None, "", "none", "-1"):
            raise SetupRefused("extended_logging_enabled")


def prepare(control, connect_target, binding, *, owned_socket=None, record):
    """Prepare only absent fixed names and the new empty target; keep roles inactive.

    Database creation cannot be in a transaction: durable stage evidence records
    its attempt before dispatch and confirmation after dispatch. Any uncertain
    outcome stops without retry. ALLOW_CONNECTIONS false closes PUBLIC's initial
    default-access window; only the new database ACL is changed before opening.
    All migration/catalogue/grant work then commits in one transaction.
    """
    sources = migration_sources(binding)
    guard(control, "clip_test", owned_socket=owned_socket)
    if control.execute(
        "SELECT rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user"
    ).fetchone() != (True, True):
        raise SetupRefused("setup_authority_missing")
    if (
        control.execute(
            "SELECT datname FROM pg_database WHERE datname=%s", (DATABASE,)
        ).fetchone()
        or control.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN (%s,%s)", (LOADER, RUNTIME)
        ).fetchall()
    ):
        raise SetupRefused("existing_target_or_role_refused")
    # NOINHERIT does not eliminate PUBLIC rights. Refuse rather than repair a
    # different application database with PUBLIC CONNECT. System catalogs remain
    # PostgreSQL's normal system access, not an application-data boundary claim.
    if control.execute("""SELECT d.datname FROM pg_database d,
        LATERAL aclexplode(coalesce(d.datacl,acldefault('d',d.datdba))) a
        WHERE d.datname NOT IN ('postgres','template0','template1','rdsadmin')
          AND a.grantee=0 AND a.privilege_type='CONNECT' LIMIT 1""").fetchone():
        raise SetupRefused("other_application_database_public_connect")
    record(stage="preflight_passed")
    with control.transaction():
        for role in (LOADER, RUNTIME):
            control.execute(
                f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2"
            )
            for name, value in LOGGING.items():
                # Both strings come only from fixed code-owned constants.
                control.execute(f"ALTER ROLE {role} SET {name} TO '{value}'")
    record(stage="inactive_roles_committed")
    record(stage="database_create_attempt")
    control.execute(
        f"CREATE DATABASE {DATABASE} OWNER {ADMIN} TEMPLATE template0 ENCODING 'UTF8' LOCALE 'C' ALLOW_CONNECTIONS false"
    )
    record(stage="database_created_connections_disabled")
    with control.transaction():
        control.execute(f"REVOKE ALL ON DATABASE {DATABASE} FROM PUBLIC")
        control.execute(f"GRANT CONNECT ON DATABASE {DATABASE} TO {LOADER}")
    control.execute(f"ALTER DATABASE {DATABASE} ALLOW_CONNECTIONS true")
    record(stage="database_opened_with_private_acl")
    with connect_target() as target:
        guard(target, DATABASE, owned_socket=owned_socket)
        if target.execute(
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%%'"
        ).fetchone() != (0,):
            raise SetupRefused("new_target_not_empty")
        with target.transaction():
            target.execute("SET LOCAL statement_timeout='60s'")
            target.execute("SET LOCAL lock_timeout='5s'")
            target.execute(
                "CREATE TABLE public.schema_migrations (version varchar NOT NULL PRIMARY KEY)"
            )
            for version, sql in sources:
                target.execute(sql, prepare=False)
                target.execute(
                    "INSERT INTO public.schema_migrations(version) VALUES(%s)",
                    (version,),
                )
            target.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
            target.execute(
                f"GRANT USAGE ON SCHEMA public,identity,listings TO {LOADER}"
            )
            for table in TABLES:
                # UPDATE is needed for the loader's ACCESS EXCLUSIVE locks and
                # trigger row locks. No DELETE/TRUNCATE/ownership/schema CREATE.
                target.execute(f"GRANT SELECT,INSERT,UPDATE ON {table} TO {LOADER}")
            # The existing listing invalidation trigger issues DELETE/INSERT
            # even with an empty pipeline registry; keep it enabled and grant
            # only its actual generation-table operations, never all-table DML.
            target.execute(
                f"GRANT SELECT,INSERT,DELETE ON listings.embedding_generations TO {LOADER}"
            )
            for table in READ_TABLES:
                target.execute(f"GRANT SELECT ON {table} TO {LOADER}")
            versions = [
                r[0]
                for r in target.execute(
                    "SELECT version FROM public.schema_migrations ORDER BY version"
                )
            ]
            if versions != [v for v, _ in sources]:
                raise SetupRefused("actual_migrations_differ")
            for role in (LOADER, RUNTIME):
                flags = target.execute(
                    "SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s",
                    (role,),
                ).fetchone()
                if (
                    flags != (False,) * 7
                    or target.execute(
                        "SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s)",
                        (role,),
                    ).fetchone()
                ):
                    raise SetupRefused("role_privilege_drift")
        record(stage="schema_and_loader_grants_committed", migrations=len(sources))
    return {
        "state": "isolated_database_prepared_roles_inactive",
        "database": DATABASE,
        "migrations": len(sources),
        "loader": LOADER,
        "runtime": RUNTIME,
        "credential_created": False,
        "data_loaded": False,
        "data_ready": False,
    }
