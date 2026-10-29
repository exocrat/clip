"""Guarded, operator-only restoration of the two approved catalogue grants.

Import does not connect. Live use requires a separate exact cloud/SQL approval;
this helper never creates roles, changes rows, migrations or other grants.
"""

from psycopg import sql
from scripts.identity_conversations_role import HOST, LOGGING

ROLE = "clip_test_marketplace_app"
GRANTS = {"listings.categories": "created_at", "listings.conditions": "label"}


class GrantRestoreFailure(Exception):
    """Fixed safe failure with no raw DSN, SQL or exception data."""


def restore(connect, *, isolated=False):
    """Restore only missing approved column grants atomically and verify scope."""
    try:
        with connect() as c, c.transaction():
            for name, value in LOGGING.items():
                c.execute(
                    sql.SQL("SET LOCAL {} = {}").format(
                        sql.Identifier(name), sql.Literal(value)
                    )
                )
            c.execute("SET LOCAL lock_timeout='5s'")
            c.execute("SET LOCAL statement_timeout='10s'")
            database, admin = (
                ("clip_test_identity", "clip_identity_ci")
                if isolated
                else ("clip_test", "clip_test_admin")
            )
            if c.execute(
                "SELECT current_database(),current_user,session_user"
            ).fetchone() != (database, admin, admin):
                raise ValueError
            if isolated:
                if not c.info.host.startswith("/"):
                    raise ValueError
            elif (
                c.info.host != HOST
                or c.info.port != 5432
                or not c.pgconn.ssl_in_use
                or c.info.get_parameters().get("sslmode") != "verify-full"
            ):
                raise ValueError
            if c.execute(
                "SELECT count(*),max(version) FROM public.schema_migrations"
            ).fetchone() != (23, "20261027112205"):
                raise ValueError
            if not c.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,)
            ).fetchone():
                raise ValueError
            for name, allowed in (
                ("pgaudit.log", (None, "", "none")),
                ("auto_explain.log_min_duration", (None, "", "-1")),
            ):
                if (
                    c.execute("SELECT current_setting(%s,true)", (name,)).fetchone()[0]
                    not in allowed
                ):
                    raise ValueError
            changed = []
            for table, column in GRANTS.items():
                select, table_update = c.execute(
                    "SELECT has_table_privilege(%s,%s,'SELECT'),has_table_privilege(%s,%s,'UPDATE')",
                    (ROLE, table, ROLE, table),
                ).fetchone()
                if not select or table_update:
                    raise ValueError
                actual = {
                    r[0]
                    for r in c.execute(
                        "SELECT attname FROM pg_attribute WHERE attrelid=to_regclass(%s) AND attnum>0 AND NOT attisdropped AND has_column_privilege(%s,attrelid,attname,'UPDATE')",
                        (table, ROLE),
                    )
                }
                if actual - {column}:
                    raise ValueError
                if column not in actual:
                    c.execute(
                        sql.SQL("GRANT UPDATE ({}) ON TABLE {} TO {}").format(
                            sql.Identifier(column),
                            sql.Identifier(*table.split(".")),
                            sql.Identifier(ROLE),
                        )
                    )
                    changed.append(table + "." + column)
                if not c.execute(
                    "SELECT has_column_privilege(%s,%s,%s,'UPDATE')",
                    (ROLE, table, column),
                ).fetchone()[0]:
                    raise ValueError
        return {"role": ROLE, "changed": changed, "schema_or_data_changed": False}
    except Exception:
        raise GrantRestoreFailure(
            "Catalogue grant restoration refused; inspect approved target/state"
        ) from None
