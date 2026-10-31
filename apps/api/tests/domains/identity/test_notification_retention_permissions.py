"""Offline least-privilege rehearsal; never connects to the retained database."""

from pathlib import Path

from psycopg import errors
import pytest

ROOT = Path(__file__).resolve().parents[5]
ROLE = "clip_test_notification_retention"


def test_retention_role_can_lock_and_cannot_modify_unrelated_fields(
    disposable_database,
):
    """Check PostgreSQL row-lock and delete rights, and deny broader writes.

    All role and ACL changes are confined to the fixture's disposable database.
    Key-column UPDATE remains a documented residual permission for row locking.
    """
    with disposable_database() as connection:
        connection.execute(f"CREATE ROLE {ROLE} NOLOGIN NOINHERIT")
        try:
            connection.execute(
                (
                    ROOT
                    / "database/roles/conversations-notification-retention.sql.proposed"
                ).read_text(),
                prepare=False,
            )
            connection.execute(f"SET ROLE {ROLE}")
            for table in ("threads", "members", "notification_intents"):
                connection.execute(
                    f"SELECT * FROM conversations.{table} WHERE false FOR UPDATE"
                )
            connection.execute(
                "DELETE FROM conversations.notification_intents WHERE false"
            )
            for statement in (
                "DELETE FROM conversations.threads WHERE false",
                "DELETE FROM conversations.members WHERE false",
                "UPDATE conversations.members SET last_read_sequence=0 WHERE false",
                "UPDATE conversations.notification_intents SET state='sent' WHERE false",
                "SELECT * FROM identity.users WHERE false",
            ):
                with pytest.raises(errors.InsufficientPrivilege):
                    connection.execute(statement)
        finally:
            connection.execute("RESET ROLE")
            connection.execute(f"DROP OWNED BY {ROLE}")
            connection.execute(f"DROP ROLE {ROLE}")
