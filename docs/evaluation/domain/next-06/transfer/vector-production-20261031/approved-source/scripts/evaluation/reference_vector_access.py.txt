"""Dedicated ephemeral vector-producer role for the isolated NEXT-06 target.

Inert import: caller owns explicit cloud/DDL approval, private admin connection,
expiry and verified stopped closeout. No app/runtime/loader role is activated.
Only the fixed new producer is created/granted; no adoption/drop/automatic retry.
"""

from datetime import datetime, UTC
import secrets

from psycopg import sql
from psycopg.conninfo import make_conninfo

from scripts.evaluation.reference_load_access import guard_admin, LoadAccessRefused
from scripts.evaluation.reference_admin_inventory import ADMIN, HOST, LOGGING
from scripts.evaluation.reference_database_setup import DATABASE, LOADER, RUNTIME

ROLE = "clip_next06_embeddings"


class VectorAccess:
    """One create/activation attempt with role-OID-bound password revocation.

    Creation/grants commit with NOLOGIN before activation. Partial failures retain
    the inactive role or existing building pipeline for reviewed recovery, never
    broader privileges/reset. No credential enters an object attribute or report.
    """

    def __init__(self):
        self.create_attempted = False
        self.role_oid = None
        self.attempted = False
        self.closed = False

    def activate(self, connection, *, expires, record, owned_socket=None):
        """Create only absent producer and grant actual operator/worker operations.

        UPDATE(id) is solely the PostgreSQL row-lock privilege. Listing identity
        triggers still forbid changing id; no description/price/data CRUD grant.
        Pipeline registry DELETE and chunk UPDATE/DELETE are deliberately absent.
        """
        if self.create_attempted or self.attempted:
            raise LoadAccessRefused("vector_access_already_attempted")
        guard_admin(connection, owned_socket=owned_socket)
        now = datetime.now(UTC)
        if (
            not isinstance(expires, datetime)
            or expires.tzinfo is None
            or not 300 <= (expires - now).total_seconds() <= 2700
        ):
            raise LoadAccessRefused("bounded_aware_expiry_required")
        if connection.execute(
            "SELECT oid FROM pg_roles WHERE rolname=%s", (ROLE,)
        ).fetchone():
            raise LoadAccessRefused("existing_vector_role_refused")
        if connection.execute(
            "SELECT count(*) FROM pg_roles WHERE rolname IN (%s,%s) AND NOT rolcanlogin",
            (LOADER, RUNTIME),
        ).fetchone() != (2,):
            raise LoadAccessRefused("loader_and_runtime_must_be_inactive")
        if connection.execute(
            "SELECT (SELECT count(*) FROM listings.sale_listings WHERE retired_at IS NULL AND retirement_pending_operation_id IS NULL),(SELECT count(*) FROM listings.embedding_pipelines),(SELECT count(*) FROM listings.embedding_generations),(SELECT count(*) FROM listings.embedding_chunks)"
        ).fetchone() != (1000, 0, 0, 0):
            raise LoadAccessRefused("fresh_complete_source_and_empty_pipeline_required")
        if connection.execute("""SELECT d.datname FROM pg_database d,
            LATERAL aclexplode(coalesce(d.datacl,acldefault('d',d.datdba))) a
            WHERE d.datname NOT IN ('postgres','template0','template1','rdsadmin')
              AND a.grantee=0 AND a.privilege_type='CONNECT' LIMIT 1""").fetchone():
            raise LoadAccessRefused("other_application_database_public_connect")
        self.create_attempted = True
        record(stage="vector_role_create_attempt")
        with connection.transaction():
            connection.execute(
                f"CREATE ROLE {ROLE} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2"
            )
            for name, value in LOGGING.items():
                connection.execute(f"ALTER ROLE {ROLE} SET {name} TO '{value}'")
            connection.execute(f"GRANT CONNECT ON DATABASE {DATABASE} TO {ROLE}")
            connection.execute(f"GRANT USAGE ON SCHEMA public,listings TO {ROLE}")
            connection.execute(
                f"GRANT SELECT ON public.schema_migrations,listings.sale_listings,listings.categories,listings.conditions,listings.images TO {ROLE}"
            )
            connection.execute(f"GRANT UPDATE(id) ON listings.sale_listings TO {ROLE}")
            connection.execute(
                f"GRANT SELECT,INSERT,UPDATE ON listings.embedding_pipelines TO {ROLE}"
            )
            connection.execute(
                f"GRANT SELECT,INSERT,UPDATE,DELETE ON listings.embedding_generations TO {ROLE}"
            )
            connection.execute(
                f"GRANT SELECT,INSERT ON listings.embedding_chunks TO {ROLE}"
            )
            row = connection.execute(
                "SELECT oid,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s",
                (ROLE,),
            ).fetchone()
            if (
                row is None
                or row[1:] != (False,) * 7
                or connection.execute(
                    "SELECT 1 FROM pg_auth_members WHERE member=%s", (row[0],)
                ).fetchone()
            ):
                raise LoadAccessRefused("vector_role_privilege_drift")
            self.role_oid = row[0]
        record(stage="vector_inactive_role_grants_committed", role_oid=self.role_oid)
        password = secrets.token_urlsafe(32)
        self.attempted = True
        record(
            stage="vector_activation_attempt",
            role_oid=self.role_oid,
            expires_utc=expires.astimezone(UTC).isoformat(),
        )
        with connection.transaction():
            connection.execute("SET LOCAL password_encryption='scram-sha-256'")
            connection.execute(
                sql.SQL("ALTER ROLE {} LOGIN PASSWORD {} VALID UNTIL {}").format(
                    sql.Identifier(ROLE),
                    sql.Literal(password),
                    sql.Literal(expires.isoformat()),
                )
            )
        record(stage="vector_role_activated", role_oid=self.role_oid)
        return make_conninfo(
            host=HOST,
            port=5432,
            dbname=DATABASE,
            user=ROLE,
            password=password,
            sslmode="verify-full",
            sslrootcert="system",
        )

    def close(self, connection, *, record, owned_socket=None):
        """Disable/clear only the same attempted producer; never modify app roles."""
        if not self.attempted or self.closed:
            return
        guard_admin(connection, owned_socket=owned_socket)
        row = connection.execute(
            "SELECT oid,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s",
            (ROLE,),
        ).fetchone()
        if (
            row != (self.role_oid, False, False, False, False, False, False)
            or connection.execute(
                "SELECT 1 FROM pg_auth_members WHERE member=%s", (self.role_oid,)
            ).fetchone()
        ):
            raise LoadAccessRefused("vector_cleanup_ownership_or_privilege_drift")
        record(stage="vector_revoke_attempt", role_oid=self.role_oid)
        with connection.transaction():
            connection.execute(
                sql.SQL(
                    "ALTER ROLE {} NOLOGIN PASSWORD NULL VALID UNTIL 'epoch'"
                ).format(sql.Identifier(ROLE))
            )
            if connection.execute(
                "SELECT rolcanlogin FROM pg_roles WHERE oid=%s", (self.role_oid,)
            ).fetchone() != (False,):
                raise LoadAccessRefused("vector_disable_not_verified")
        self.closed = True
        record(stage="vector_disabled_password_cleared", role_oid=self.role_oid)
