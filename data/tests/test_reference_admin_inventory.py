"""Bounded admin-inventory refusal/transport tests, never live cloud acceptance."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from scripts.evaluation import reference_admin_inventory as inventory


def connection(failure=None):
    calls = []

    def execute(statement, args=None):
        calls.append(statement)
        if statement == "SET TRANSACTION READ ONLY":
            return None
        if "current_database()" in statement:
            return SimpleNamespace(
                fetchone=lambda: (
                    inventory.DATABASE,
                    "wrong" if failure == "role" else inventory.ADMIN,
                    inventory.ADMIN,
                    "180006",
                    "on",
                )
            )
        if "current_setting" in statement:
            return SimpleNamespace(
                fetchone=lambda: (
                    (
                        "unsafe"
                        if failure == "privacy"
                        else inventory.LOGGING.get(args[0])
                    ),
                )
            )
        if statement == inventory.QUERIES["migrations"]:
            if failure == "denied":
                raise PermissionError("private-database-text")
            rows = (
                [("private-database-text",)]
                if failure == "unexpected"
                else [("20261001",)]
            )
        else:
            rows = []
        return SimpleNamespace(fetchall=lambda: rows)

    return (
        SimpleNamespace(
            transaction=lambda: nullcontext(),
            execute=execute,
            info=SimpleNamespace(
                host=inventory.HOST,
                port=inventory.PORT,
                get_parameters=lambda: {
                    "hostaddr": "127.0.0.1",
                    "sslmode": "disable" if failure == "tls" else "verify-full",
                },
            ),
            pgconn=SimpleNamespace(ssl_in_use=True),
        ),
        calls,
    )


@pytest.mark.parametrize(
    "failure,stage",
    [
        ("role", "session"),
        ("tls", "session"),
        ("privacy", "privacy"),
        ("denied", "migrations"),
        ("unexpected", "migrations"),
    ],
)
def test_refusal_is_bounded_and_no_later_queries(failure, stage):
    conn, calls = connection(failure)
    result = inventory.inspect(conn)
    assert result == {"state": "refused_or_failed", "stage": stage, "sqlstate": None}
    assert "private-database-text" not in str(result)
    assert inventory.QUERIES["database"] not in calls


def test_exact_query_allowlist_and_readonly_first():
    conn, calls = connection()
    result = inventory.inspect(conn)
    assert result["state"] == "readonly_admin_metadata_passed"
    assert calls[0] == "SET TRANSACTION READ ONLY"
    assert calls[-4:] == list(inventory.QUERIES.values())
    assert all(
        not any(
            word in sql
            for word in ("GRANT ", "CREATE ", "INSERT ", "ALTER ", "DELETE ")
        )
        for sql in calls
    )


def test_fixed_tls_tunnel_and_memory_only_password(monkeypatch):
    def connect(**kwargs):
        assert kwargs["hostaddr"] == "127.0.0.1"
        assert kwargs["port"] == 15432
        assert kwargs["sslmode"] == "verify-full"
        assert kwargs["password"] == "synthetic-private-value"
        assert "default_transaction_read_only=on" in kwargs["options"]
        assert "log_min_error_statement=panic" in kwargs["options"]
        raise RuntimeError("synthetic-private-value")

    monkeypatch.setattr(inventory.psycopg, "connect", connect)
    result = inventory.connect_and_inspect(
        "synthetic-private-value", "/approved/ca.pem"
    )
    assert result == {
        "state": "refused_or_failed",
        "stage": "connect",
        "sqlstate": None,
    }
