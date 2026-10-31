"""Verify the Conversations role can read the public projection only."""

from psycopg import errors
import pytest
from scripts.cn03_projection_grant import (
    GRANT_SHA256,
    ProjectionGrantRefused,
    grant_projection,
)

ROLE = "clip_test_conversations_app"


def test_projection_grant_allows_view_but_not_identity_users(disposable_database):
    """An owned role gains view access without access to private Identity rows."""
    with disposable_database() as c:
        c.execute(f"CREATE ROLE {ROLE} NOLOGIN NOINHERIT")
        try:
            c.execute(f"SET ROLE {ROLE}")
            with pytest.raises(errors.InsufficientPrivilege):
                c.execute("SELECT * FROM identity.participant_profiles LIMIT 0")
            c.execute("RESET ROLE")
            with pytest.raises(ProjectionGrantRefused):
                grant_projection(c, isolated=True, approved_sha256="incorrect")
            assert grant_projection(c, isolated=True, approved_sha256=GRANT_SHA256)[
                "public_projection_select"
            ]
            with pytest.raises(ProjectionGrantRefused):
                grant_projection(c, isolated=True, approved_sha256=GRANT_SHA256)
            c.execute(f"SET ROLE {ROLE}")
            c.execute("SELECT * FROM identity.participant_profiles LIMIT 0")
            with pytest.raises(errors.InsufficientPrivilege):
                c.execute("SELECT * FROM identity.users LIMIT 0")
            with pytest.raises(errors.InsufficientPrivilege):
                c.execute("SELECT * FROM identity.notification_destinations LIMIT 0")
        finally:
            c.execute("RESET ROLE")
            c.execute(f"DROP OWNED BY {ROLE}")
            c.execute(f"DROP ROLE {ROLE}")
