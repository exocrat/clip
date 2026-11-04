"""Routing and timeout safety checks; no credentials, DNS or AWS access."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlsplit

import pytest
from psycopg.conninfo import conninfo_to_dict
from pydantic import ValidationError

from app.core.config import Settings
from app.core.database_transport import (
    EXPECTED_TIMEOUTS,
    check_async_proxy_connection,
    check_proxy_connection,
    connection_kwargs,
    route_database,
)

ENDPOINT = "clip-shared-test-pool.proxy-example.ap-south-1.rds.amazonaws.com"
DSN = "postgresql://clip_test_identity_app:synthetic%40value@source.example:5432/clip_next06_reference?sslmode=verify-full&sslrootcert=system"


def test_override_preserves_everything_except_host_and_is_reversible():
    before = conninfo_to_dict(DSN)
    routed = route_database(DSN, ENDPOINT)
    assert conninfo_to_dict(routed) == before | {"host": ENDPOINT}
    assert route_database(DSN, None) == DSN
    assert urlsplit(routed).password == urlsplit(DSN).password


@pytest.mark.parametrize(
    "bad", ["localhost", "https://" + ENDPOINT, ENDPOINT + ".evil", "a,b", ""]
)
def test_wrong_proxy_endpoint_rejected(bad):
    with pytest.raises(ValueError, match="proxy routing"):
        route_database(DSN, bad)
    with pytest.raises(ValidationError):
        Settings(database_proxy_endpoint=bad)


@pytest.mark.parametrize(
    "bad",
    [
        DSN.replace("verify-full", "require"),
        DSN.replace("5432", "6432"),
        DSN + "&host=another.example",
        DSN + "&options=-c%20statement_timeout=0",
        "dbname=clip_test host=/tmp",
    ],
)
def test_routing_does_not_bypass_source_dsn_guards(bad):
    with pytest.raises(ValueError, match="proxy routing"):
        route_database(bad, ENDPOINT)


def test_proxy_uses_server_defaults_but_direct_options_unchanged():
    original = {"options": "-c statement_timeout=5000", "autocommit": True}
    assert connection_kwargs(DSN, **original) == original
    proxy = connection_kwargs(route_database(DSN, ENDPOINT), **original)
    assert "options" not in proxy
    assert proxy["prepare_threshold"] is None
    assert proxy["autocommit"] is True


def test_restore_cannot_inherit_source_proxy():
    with pytest.raises(ValidationError, match="restore smoke"):
        Settings(database_proxy_endpoint=ENDPOINT, nfr07_restore_smoke_enabled=True)


@pytest.mark.parametrize("row", [EXPECTED_TIMEOUTS, ("0", "1s", "5s"), None])
def test_sync_proxy_connection_requires_timeouts_and_rolls_back(row):
    conn = MagicMock()
    conn.info.host = ENDPOINT
    conn.cursor.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (
        row
    )
    if row == EXPECTED_TIMEOUTS:
        check_proxy_connection(conn)
    else:
        with pytest.raises(ValueError, match="timeout configuration"):
            check_proxy_connection(conn)
    conn.rollback.assert_called_once()


@pytest.mark.parametrize("row", [EXPECTED_TIMEOUTS, ("5s", "0", "5s"), None])
def test_async_proxy_connection_requires_timeouts_and_rolls_back(row):
    cursor = AsyncMock()
    cursor.fetchone.return_value = row
    conn = MagicMock()
    conn.info.host = ENDPOINT
    conn.cursor.return_value.__aenter__ = AsyncMock(return_value=cursor)
    conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
    conn.rollback = AsyncMock()
    if row == EXPECTED_TIMEOUTS:
        asyncio.run(check_async_proxy_connection(conn))
    else:
        with pytest.raises(ValueError, match="timeout configuration"):
            asyncio.run(check_async_proxy_connection(conn))
    conn.rollback.assert_awaited_once()


def test_direct_connections_do_not_add_a_validation_query():
    conn = SimpleNamespace(info=SimpleNamespace(host="source.example", port=5432))
    check_proxy_connection(conn)
