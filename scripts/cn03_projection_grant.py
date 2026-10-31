"""Guarded Conversations access to Identity's public participant projection.

Import does not connect; shared execution requires explicit operator approval.
"""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRANT = ROOT / "database/roles/conversations-identity-projection.sql.proposed"
GRANT_SHA256 = "14510d65e9187a745b592d66991224c2be433e05fb8ad37f76de532162e6ccb7"
HOST = "clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com"
ROLE = "clip_test_conversations_app"


class ProjectionGrantRefused(Exception):
    """Fixed error that reveals neither credentials nor SQL diagnostics."""


def grant_projection(connection, *, isolated: bool, approved_sha256: str):
    """Grant only public-view read access atomically after strict preflight.

    Isolated mode permits only the owned local fixture. A shared target requires
    the exact database/admin and hostname-verified TLS tunnel. On ambiguous
    commit the operator must inspect state before any retry.
    """
    try:
        if (
            approved_sha256 != GRANT_SHA256
            or hashlib.sha256(GRANT.read_bytes()).hexdigest() != GRANT_SHA256
        ):
            raise ValueError
        expected = (
            ("clip_test_identity", "clip_identity_ci")
            if isolated
            else ("clip_test", "clip_test_admin")
        )
        with connection.transaction():
            connection.execute("SET LOCAL lock_timeout='5s'")
            connection.execute("SET LOCAL statement_timeout='10s'")
            target = connection.execute(
                "SELECT current_database(), current_user, session_user"
            ).fetchone()
            if target != (expected[0], expected[1], expected[1]):
                raise ValueError
            if isolated:
                if not connection.info.host.startswith("/"):
                    raise ValueError
            elif (
                connection.info.host != HOST
                or connection.info.port != 15432
                or not connection.pgconn.ssl_in_use
                or connection.info.get_parameters().get("sslmode") != "verify-full"
            ):
                raise ValueError
            if connection.execute(
                "SELECT count(*),max(version) FROM public.schema_migrations"
            ).fetchone() != (32, "20261029182500"):
                raise ValueError
            if connection.execute(
                "SELECT has_schema_privilege(%s,'identity','USAGE'),has_table_privilege(%s,'identity.participant_profiles','SELECT')",
                (ROLE, ROLE),
            ).fetchone() != (False, False):
                raise ValueError
            connection.execute(GRANT.read_text(), prepare=False)
            actual = connection.execute(
                "SELECT has_schema_privilege(%s,'identity','USAGE'),has_table_privilege(%s,'identity.participant_profiles','SELECT'),has_table_privilege(%s,'identity.users','SELECT'),has_table_privilege(%s,'identity.notification_destinations','SELECT')",
                (ROLE, ROLE, ROLE, ROLE),
            ).fetchone()
            if actual != (True, True, False, False):
                raise ValueError
        return {
            "schema_usage": True,
            "public_projection_select": True,
            "private_identity_select": False,
        }
    except Exception:
        raise ProjectionGrantRefused(
            "Projection grant stopped; inspect state before retry"
        ) from None
