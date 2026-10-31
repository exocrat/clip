"""Fixed read-only NEXT-06 admin inventory over a separately approved SSM tunnel.

Import is inert. The caller owns approval, one memory-only credential read,
exclusive resource window, tunnel ownership and stopped closeout. This module
cannot create databases/roles, change grants, load rows or call AWS.
"""

import re

import psycopg

from scripts.evaluation.reference_db_inventory import HOST

DATABASE = "clip_test"
ADMIN = "clip_test_admin"
PORT = 15432
LOGGING = {
    "log_statement": "none",
    "log_min_duration_statement": "-1",
    "log_min_duration_sample": "-1",
    "log_transaction_sample_rate": "0",
    "log_min_error_statement": "panic",
    "log_parameter_max_length_on_error": "0",
}
QUERIES = {
    "migrations": "SELECT version FROM public.schema_migrations ORDER BY version LIMIT 101",
    "schemas": "SELECT nspname FROM pg_namespace WHERE nspname IN ('identity','listings','search','conversations') ORDER BY nspname",
    "roles": "SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls FROM pg_roles WHERE rolname IN ('clip_next06_loader','clip_next06_runtime') ORDER BY rolname",
    "database": "SELECT datname FROM pg_database WHERE datname='clip_next06_reference'",
}


class InventoryRefused(Exception):
    """Only a fixed stage is exposed; nested SQL diagnostics remain private."""


def inspect(connection):
    """Return bounded catalog metadata only after exact session/privacy checks.

    A privileged setup login is intentional here, and never supplied to the app.
    Every statement stays in one READ ONLY transaction with bounded timeouts.
    Missing tracker/table/permission aborts; there is no repair or fallback.
    """
    stage = "session"
    try:
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            identity = connection.execute(
                "SELECT current_database(),current_user,session_user,current_setting('server_version_num'),current_setting('transaction_read_only')"
            ).fetchone()
            params = connection.info.get_parameters()
            if (
                identity != (DATABASE, ADMIN, ADMIN, "180006", "on")
                or connection.info.host != HOST
                or connection.info.port != PORT
                or params.get("hostaddr") != "127.0.0.1"
                or params.get("sslmode") != "verify-full"
                or not connection.pgconn.ssl_in_use
            ):
                raise InventoryRefused
            stage = "privacy"
            for name, expected in LOGGING.items():
                if connection.execute(
                    "SELECT current_setting(%s)", (name,)
                ).fetchone() != (expected,):
                    raise InventoryRefused
            for name in ("pgaudit.log", "auto_explain.log_min_duration"):
                if connection.execute(
                    "SELECT current_setting(%s,true)", (name,)
                ).fetchone()[0] not in (None, "", "none", "-1"):
                    raise InventoryRefused
            report = {}
            for stage, statement in QUERIES.items():
                rows = connection.execute(statement).fetchall()
                if stage == "migrations":
                    if len(rows) > 100 or any(
                        len(r) != 1
                        or not isinstance(r[0], str)
                        or re.fullmatch(r"[0-9]{1,20}", r[0]) is None
                        for r in rows
                    ):
                        raise InventoryRefused
                elif stage == "schemas":
                    if len(rows) > 4 or any(
                        len(r) != 1
                        or r[0]
                        not in {"identity", "listings", "search", "conversations"}
                        for r in rows
                    ):
                        raise InventoryRefused
                elif stage == "roles":
                    if len(rows) > 2 or any(
                        len(r) != 8
                        or r[0] not in {"clip_next06_loader", "clip_next06_runtime"}
                        or any(type(v) is not bool for v in r[1:])
                        for r in rows
                    ):
                        raise InventoryRefused
                elif rows not in ([], [("clip_next06_reference",)]):
                    raise InventoryRefused
                report[stage] = rows
            return {"state": "readonly_admin_metadata_passed", "metadata": report}
    except Exception as error:
        code = getattr(error, "sqlstate", None)
        if not isinstance(code, str) or re.fullmatch(r"[0-9A-Z]{5}", code) is None:
            code = None
        return {"state": "refused_or_failed", "stage": stage, "sqlstate": code}


def connect_and_inspect(password, ca_path):
    """Use an already owned loopback15432 tunnel, fixed login and verified CA.

    Password stays in the connection keyword argument. Startup options make
    readonly/time/privacy settings effective before catalog statements. No DSN
    or raw connection exception is returned, including authentication failures.
    """
    if not isinstance(password, str) or not 0 < len(password) <= 4096:
        return {
            "state": "refused_or_failed",
            "stage": "credential_bound",
            "sqlstate": None,
        }
    options = {
        **LOGGING,
        "default_transaction_read_only": "on",
        "statement_timeout": "5000",
        "lock_timeout": "1000",
        "idle_in_transaction_session_timeout": "5000",
    }
    try:
        with psycopg.connect(
            host=HOST,
            hostaddr="127.0.0.1",
            port=PORT,
            dbname=DATABASE,
            user=ADMIN,
            password=password,
            sslmode="verify-full",
            sslrootcert=str(ca_path),
            connect_timeout=5,
            autocommit=True,
            application_name="clip-next06-admin-readonly-inventory",
            options=" ".join(f"-c {k}={v}" for k, v in options.items()),
        ) as connection:
            return inspect(connection)
    except Exception:
        return {"state": "refused_or_failed", "stage": "connect", "sqlstate": None}
