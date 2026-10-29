"""Actual consumer flows with a distinct proposed Conversations SQL login.

Disposable database only; no shared grants/SSM or production credentials. This
proves the exercised API scope, not retention or every concurrency/recovery path.
"""

from psycopg.errors import InsufficientPrivilege
import pytest

from apps.api.tests.domains.identity.test_consumer_capability_matrix import (
    matrix_case,
    test_nonempty_reads_saved_wanted_and_profile_use_actual_providers as active_flow,
    test_actual_conversation_keys_prekeys_and_contact_share as key_flow,
    test_offer_revision_withdrawal_exact_retry_and_other_buyer_denial as offer_flow,
    test_wanted_response_class_replay_and_foreign_author_denial as wanted_flow,
)


@pytest.mark.parametrize(
    "matrix_case",
    ["regular-conversation-role", "temporary-conversation-role"],
    indirect=True,
)
def test_distinct_conversations_login_serves_actual_consumers(matrix_case):
    """The real tuple pool runs as the proposed login, preserving domain isolation."""
    case = matrix_case

    async def inspect_permissions():
        """Check the actual provider pool's principal and forbidden SQL operations."""
        async with case.app.state.database_pool.connection() as connection:
            row = await (
                await connection.execute("SELECT current_user,session_user")
            ).fetchone()
            assert row == ("clip_test_conversations_app", "clip_test_conversations_app")
            flags = await (
                await connection.execute(
                    "SELECT rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user"
                )
            ).fetchone()
            assert flags == (False, False, False, False, False, False)
            assert (
                await (
                    await connection.execute(
                        "SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)"
                    )
                ).fetchone()
            )[0] == 0
            assert (
                await (
                    await connection.execute(
                        "SELECT count(*) FROM pg_class WHERE relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)"
                    )
                ).fetchone()
            )[0] == 0
            assert (await (await connection.execute("SHOW log_statement")).fetchone())[
                0
            ] == "none"
            assert (
                await (
                    await connection.execute("SHOW log_min_error_statement")
                ).fetchone()
            )[0] == "panic"
            await connection.commit()
            for statement in (
                "SELECT * FROM identity.users LIMIT 0",
                "SELECT * FROM listings.sale_listings LIMIT 0",
                "SELECT * FROM search.wanted_requests LIMIT 0",
                "CREATE TABLE conversations.forbidden_probe(id integer)",
                "CREATE TEMP TABLE forbidden_probe(id integer)",
                "TRUNCATE conversations.threads",
                "DELETE FROM conversations.threads WHERE false",
            ):
                with pytest.raises(InsufficientPrivilege):
                    await connection.execute(statement)
                await connection.rollback()

    # TestClient owns the pool's event loop; inspect there, not asyncio.run().
    case.browser.portal.call(inspect_permissions)
    active_flow(case)
    key_flow(case)
    offer_flow(case)
    wanted_flow(case)
