"""Explicit, reversible RDS Proxy routing without changing stored credentials.

The source DSN remains authoritative for role/database/TLS. Only its host is
replaced, and only by an approved Mumbai proxy hostname. Removing the runtime
override restores the direct path. No connection is opened during routing.
"""

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import tuple_row

PROXY_HOST = re.compile(
    r"[a-z][a-z0-9-]*\.proxy-[a-z0-9]+\.ap-south-1\.rds\.amazonaws\.com\Z"
)
TIMEOUT_QUERY = "SELECT current_setting('statement_timeout'), current_setting('lock_timeout'), current_setting('idle_in_transaction_session_timeout')"
EXPECTED_TIMEOUTS = ("5s", "1s", "5s")


def route_database(conninfo: str, endpoint: str | None) -> str:
    """Keep role/password/database/TLS intact; reject socket or ambiguous overrides."""
    if endpoint is None:
        return conninfo
    try:
        parsed = urlsplit(conninfo)
        values = conninfo_to_dict(conninfo)
        if (
            not PROXY_HOST.fullmatch(endpoint)
            or parsed.scheme not in {"postgresql", "postgres"}
            or not parsed.hostname
            or parsed.fragment
            or parsed.port not in (None, 5432)
            or not parsed.username
            or not parsed.password
            or values.get("host") != parsed.hostname
            or "," in parsed.hostname
            or values.get("sslmode") != "verify-full"
            or values.get("sslrootcert") != "system"
            or set(values)
            - {"host", "port", "dbname", "user", "password", "sslmode", "sslrootcert"}
        ):
            raise ValueError
        authority = parsed.netloc.rsplit("@", 1)[0] + "@" + endpoint + ":5432"
        return urlunsplit((parsed.scheme, authority, parsed.path, parsed.query, ""))
    except Exception:
        raise ValueError("Invalid database proxy routing configuration") from None


def uses_proxy(conninfo: str) -> bool:
    """Identify only the constrained managed endpoint, never arbitrary host text."""
    return bool(PROXY_HOST.fullmatch(str(conninfo_to_dict(conninfo).get("host", ""))))


def connection_kwargs(conninfo: str, **kwargs: Any) -> dict[str, Any]:
    """Use proxy initialization defaults instead of unsupported startup options.

    Transaction-local deadlines in domain code stay intact. Disable automatic
    prepared statements on both proxy paths to avoid driver/session dependencies;
    direct connections retain their previous exact options and behavior.
    """
    if uses_proxy(conninfo):
        kwargs.pop("options", None)
        kwargs["prepare_threshold"] = None
        kwargs["connect_timeout"] = 3
        kwargs["passfile"] = "/dev/null"
    return kwargs


def check_proxy_connection(connection: Any) -> None:
    """Refuse a proxy missing bounded server deadlines; leave no transaction open."""
    if not PROXY_HOST.fullmatch(connection.info.host):
        return
    try:
        with connection.cursor(row_factory=tuple_row) as cursor:
            row = cursor.execute(TIMEOUT_QUERY).fetchone()
        if row != EXPECTED_TIMEOUTS:
            raise ValueError("Database proxy timeout configuration mismatch")
    finally:
        connection.rollback()


async def check_async_proxy_connection(connection: Any) -> None:
    """Async equivalent of the fail-closed timeout check for each new client."""
    if not PROXY_HOST.fullmatch(connection.info.host):
        return
    try:
        async with connection.cursor(row_factory=tuple_row) as cursor:
            await cursor.execute(TIMEOUT_QUERY)
            row = await cursor.fetchone()
        if row != EXPECTED_TIMEOUTS:
            raise ValueError("Database proxy timeout configuration mismatch")
    finally:
        await connection.rollback()
