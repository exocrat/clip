"""Real Listings/Conversations/Identity SQL and HTTP; synthetic request auth only.

Each thread is opened through the real Listings command. Key/note fixtures are
opaque synthetic material, not real SDK encryption or browser evidence.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from psycopg.errors import RaiseException
import pytest

from app.contracts.domain_types import EntryQuery
from app.core.auth import require_caller
from app.domains.conversations.cleanup import ConversationCleanup
from app.domains.conversations.messages import PostgresMessageOperations
from app.domains.conversations.routes import router as conversation_router
from test_conversation_directory import public_bundle
from test_conversation_messages import message_request
from test_conversation_offer_storage import append_revision
from test_listing_conversation_start import environment, close
from test_thread_creation import (
    TEST_DATABASE_DSN,
    run_scenario,
    caller,
    seed_users_and_listing,
)

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_DSN is None,
    reason="run through the disposable Conversations database harness",
)


@asynccontextmanager
async def offer_environment(pool, *, temporary=False):
    """Compose real routers and bind the actual request-scoped Identity provider."""
    async with environment(pool, temporary=temporary) as state:
        state.app.include_router(conversation_router)
        state.app.state.database_pool = pool
        opened = await state.client.post(
            f"/listings/{state.listing}/conversations",
            json={"operation_id": str(uuid4())},
        )
        assert opened.status_code == 201
        state.thread = UUID(opened.json()["conversation_id"])
        state.url = f"/listings/{state.listing}/conversations/{state.thread}"
        state.read_url = f"/conversations/{state.thread}/offer"
        yield state


def request(**changes):
    """Create a fresh synthetic intent unless a test deliberately reuses its key."""
    return {"amount_paise": 100, "operation_id": str(uuid4()), **changes}


async def register_members(state):
    """Use the real public registration route with reviewed synthetic public bytes."""
    for user in (state.owner, state.buyer):
        state.app.dependency_overrides[require_caller] = lambda user=user: caller(user)
        response = await state.client.put(
            "/me/conversation-key", json=public_bundle().model_dump(mode="json")
        )
        assert response.status_code == 200
    state.app.dependency_overrides[require_caller] = lambda: state.actor


async def snapshot(pool, thread):
    """Capture only counters/state for detecting partial writes and false activity."""
    async with pool.connection() as connection:
        return await (
            await connection.execute(
                "SELECT next_sequence,last_activity_at,"
                "(SELECT count(*) FROM conversations.entries WHERE conversation_id=t.id),"
                "(SELECT count(*) FROM conversations.offers WHERE conversation_id=t.id),"
                "(SELECT count(*) FROM conversations.notification_intents WHERE conversation_id=t.id) "
                "FROM conversations.threads t WHERE t.id=%s",
                (thread,),
            )
        ).fetchone()


@pytest.mark.parametrize("temporary", [False, True])
def test_real_offer_http_lifecycle_exact_retries_and_member_reads(temporary):
    async def scenario(pool):
        async with offer_environment(pool, temporary=temporary) as state:
            assert (await state.client.get(state.read_url)).json() is None
            first_body = request(amount_paise=0)
            first = await state.client.put(state.url + "/offer", json=first_body)
            assert first.status_code == 200
            first = first.json()
            head = await snapshot(pool, state.thread)
            assert (
                await state.client.put(state.url + "/offer", json=first_body)
            ).json() == first
            assert await snapshot(pool, state.thread) == head
            changed = await state.client.put(
                state.url + "/offer",
                json=request(expected_revision=1, amount_paise=200),
            )
            assert changed.status_code == 200 and changed.json()["revision"] == 2
            # A retry returns its original revision even after a later change.
            assert (
                await state.client.put(state.url + "/offer", json=first_body)
            ).json() == first
            withdrawal = {
                "offer_id": first["offer_id"],
                "expected_revision": 2,
                "operation_id": str(uuid4()),
            }
            withdrawn = await state.client.post(
                state.url + "/offer-withdrawals", json=withdrawal
            )
            assert (
                withdrawn.status_code == 200
                and withdrawn.json()["status"] == "withdrawn"
            )
            assert withdrawn.json()["amount_paise"] == 200
            assert (
                await state.client.post(
                    state.url + "/offer-withdrawals", json=withdrawal
                )
            ).json() == withdrawn.json()
            current = await state.client.put(
                state.url + "/offer",
                json=request(expected_revision=3, amount_paise=300),
            )
            assert current.status_code == 200 and current.json()["revision"] == 4
            assert current.json()["offer_id"] == first["offer_id"]
            state.app.dependency_overrides[require_caller] = lambda: caller(state.owner)
            assert (await state.client.get(state.read_url)).json() == current.json()
            summary = (await state.client.get(f"/conversations/{state.thread}")).json()
            assert (
                summary["current_offer"]["revision"] == 4
                and summary["unread_count"] == 0
            )
            entries = await state.client.get(f"/conversations/{state.thread}/entries")
            assert entries.status_code == 200 and entries.json()["items"] == []
            assert entries.json()["scanned_through_sequence"] == 4
            after = await snapshot(pool, state.thread)
            assert after[0] == 5 and after[-1] == head[-1] == 1

    run_scenario(scenario)


@pytest.mark.parametrize("change", ["amount", "expected_revision", "action", "note"])
def test_reused_operation_rejects_changed_intent_without_partial_writes(change):
    async def scenario(pool):
        async with offer_environment(pool) as state:
            body = request()
            first = (await state.client.put(state.url + "/offer", json=body)).json()
            before = await snapshot(pool, state.thread)
            if change == "action":
                result = await state.client.post(
                    state.url + "/offer-withdrawals",
                    json={
                        "offer_id": first["offer_id"],
                        "expected_revision": 1,
                        "operation_id": body["operation_id"],
                    },
                )
            else:
                if change == "note":
                    await register_members(state)
                    body["note_envelope"] = message_request().envelope.model_dump(
                        mode="json"
                    )
                else:
                    body[change if change != "amount" else "amount_paise"] = (
                        200 if change == "amount" else 1
                    )
                result = await state.client.put(state.url + "/offer", json=body)
            assert result.status_code == 409
            assert await snapshot(pool, state.thread) == before

    run_scenario(scenario)


def test_unavailable_retry_reports_state_preserves_history_and_allows_withdrawal():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            body = request()
            first = (await state.client.put(state.url + "/offer", json=body)).json()
            await close(state)
            before = await snapshot(pool, state.thread)
            for retry_body in (body, request(expected_revision=1)):
                result = await state.client.put(state.url + "/offer", json=retry_body)
                assert result.status_code == 409
                assert result.json()["error"]["details"] == [
                    {"field": "listing_id", "code": "unavailable"}
                ]
            assert (await state.client.get(state.read_url)).json() == first
            assert await snapshot(pool, state.thread) == before
            result = await state.client.post(
                state.url + "/offer-withdrawals",
                json={
                    "offer_id": first["offer_id"],
                    "expected_revision": 1,
                    "operation_id": str(uuid4()),
                },
            )
            assert result.status_code == 200 and result.json()["status"] == "withdrawn"

    run_scenario(scenario)


@pytest.mark.parametrize("same_key", [False, True])
def test_concurrent_first_offers_have_one_current_revision(same_key):
    async def scenario(pool):
        async with offer_environment(pool) as state:
            first = request()
            replies = await asyncio.gather(
                state.client.put(state.url + "/offer", json=first),
                state.client.put(
                    state.url + "/offer", json=first if same_key else request()
                ),
            )
            assert sorted(result.status_code for result in replies) == (
                [200, 200] if same_key else [200, 409]
            )
            head = await snapshot(pool, state.thread)
            assert head[0] == 2 and head[2:4] == (1, 1)

    run_scenario(scenario, max_size=4)


@pytest.mark.parametrize("committed", [False, True])
def test_ambiguous_dependency_timeout_retries_without_duplicate_offer(
    monkeypatch, committed
):
    """A lost reply may follow commit; only the original operation may be retried."""

    async def scenario(pool):
        async with offer_environment(pool) as state:
            original = state.provider.persist_listing_offer

            async def lost_reply(actor, command):
                if committed:
                    await original(actor, command)
                raise TimeoutError

            body = request()
            with monkeypatch.context() as patch:
                patch.setattr(state.provider, "persist_listing_offer", lost_reply)
                failed = await state.client.put(state.url + "/offer", json=body)
                assert failed.status_code == 503
            replay = await state.client.put(state.url + "/offer", json=body)
            assert replay.status_code == 200 and replay.json()["revision"] == 1
            head = await snapshot(pool, state.thread)
            assert head[0] == 2 and head[2:4] == (1, 1)

    run_scenario(scenario)


@pytest.mark.parametrize("role", ["seller", "stranger", "wrong_listing"])
def test_offer_owner_and_origin_checks_fail_closed(role):
    async def scenario(pool):
        async with offer_environment(pool) as state:
            before = await snapshot(pool, state.thread)
            if role == "seller":
                state.app.dependency_overrides[require_caller] = lambda: caller(
                    state.owner
                )
                result = await state.client.put(state.url + "/offer", json=request())
                assert result.status_code == 403
            else:
                _, stranger, other_listing = await seed_users_and_listing(pool)
                if role == "stranger":
                    state.app.dependency_overrides[require_caller] = lambda: caller(
                        stranger
                    )
                    assert (await state.client.get(state.read_url)).status_code == 404
                    result = await state.client.put(
                        state.url + "/offer", json=request()
                    )
                else:
                    result = await state.client.put(
                        f"/listings/{other_listing}/conversations/{state.thread}/offer",
                        json=request(),
                    )
                assert result.status_code == 404
            assert await snapshot(pool, state.thread) == before

    run_scenario(scenario)


@pytest.mark.parametrize("change", ["payload", "timestamp", "key", "sdk_id"])
def test_encrypted_note_exact_retry_and_changed_metadata(change):
    async def scenario(pool):
        async with offer_environment(pool) as state:
            await register_members(state)
            note = message_request().envelope.model_dump(mode="json") | {
                "envelope_version": 2,
                "sdk_client_message_id": str(uuid4()),
            }
            body = request(note_envelope=note)
            first = await state.client.put(state.url + "/offer", json=body)
            assert first.status_code == 200
            assert (await state.client.get(state.read_url)).json() == first.json()
            before = await snapshot(pool, state.thread)
            assert (
                await state.client.put(state.url + "/offer", json=body)
            ).json() == first.json()
            changes = {
                "payload": {"payload_base64": "b3RoZXI="},
                "timestamp": {"client_timestamp_ms": 2},
                "key": {"recipient_key_version": 99},
                "sdk_id": {"sdk_client_message_id": str(uuid4())},
            }
            body["note_envelope"] = note | changes[change]
            assert (
                await state.client.put(state.url + "/offer", json=body)
            ).status_code == 409
            assert await snapshot(pool, state.thread) == before

    run_scenario(scenario)


def test_bad_note_key_rolls_back_entire_offer_and_leaves_operation_retryable():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            note = message_request(recipient_version=99).envelope.model_dump(
                mode="json"
            )
            body = request(note_envelope=note)
            before = await snapshot(pool, state.thread)
            assert (
                await state.client.put(state.url + "/offer", json=body)
            ).status_code == 422
            assert await snapshot(pool, state.thread) == before
            # Failed writes did not reserve the operation or create a half-offer.
            body.pop("note_envelope")
            assert (
                await state.client.put(state.url + "/offer", json=body)
            ).status_code == 200

    run_scenario(scenario)


def test_retirement_marker_blocks_new_offers_and_withdrawals_but_keeps_reads():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            first = (
                await state.client.put(state.url + "/offer", json=request())
            ).json()
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE conversations.threads SET participant_writes_disabled_at=clock_timestamp() WHERE id=%s",
                    (state.thread,),
                )
            before = await snapshot(pool, state.thread)
            assert (
                await state.client.put(
                    state.url + "/offer", json=request(expected_revision=1)
                )
            ).status_code == 409
            assert (
                await state.client.post(
                    state.url + "/offer-withdrawals",
                    json={
                        "offer_id": first["offer_id"],
                        "expected_revision": 1,
                        "operation_id": str(uuid4()),
                    },
                )
            ).status_code == 409
            assert (await state.client.get(state.read_url)).json() == first
            assert await snapshot(pool, state.thread) == before

    run_scenario(scenario)


def test_purge_expires_retries_and_records_null_expected_revision_for_new_history():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            body = request()
            first = (await state.client.put(state.url + "/offer", json=body)).json()
            activity = (await snapshot(pool, state.thread))[1]
            await ConversationCleanup(pool, lambda: activity + timedelta(days=90)).run(
                apply=True, batch_size=1000
            )
            assert (await state.client.get(state.read_url)).json() is None
            expired = await state.client.put(state.url + "/offer", json=body)
            assert (
                expired.status_code == 409
                and expired.json()["error"]["details"][0]["code"] == "write_expired"
            )
            fresh = request(amount_paise=200)
            saved = await state.client.put(state.url + "/offer", json=fresh)
            assert (
                saved.status_code == 200
                and saved.json()["offer_id"] == first["offer_id"]
            )
            assert saved.json()["revision"] == 2
            assert (
                await state.client.put(state.url + "/offer", json=fresh)
            ).json() == saved.json()
            assert (
                await state.client.put(
                    state.url + "/offer", json=fresh | {"expected_revision": 1}
                )
            ).status_code == 409

    run_scenario(scenario)


def test_legacy_revision_is_readable_but_cannot_fabricate_exact_request_replay():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            offer, operation = uuid4(), uuid4()
            async with pool.connection() as connection, connection.transaction():
                await append_revision(
                    connection,
                    state.thread,
                    state.buyer,
                    offer,
                    100,
                    operation=operation,
                )
            assert (await state.client.get(state.read_url)).json()["offer_id"] == str(
                offer
            )
            assert (
                await state.client.put(
                    state.url + "/offer", json=request(operation_id=str(operation))
                )
            ).status_code == 409
            assert (
                await state.client.put(
                    state.url + "/offer", json=request(expected_revision=1)
                )
            ).status_code == 200

    run_scenario(scenario)


def test_offer_metadata_rollback_refuses_occupied_receipts():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            assert (
                await state.client.put(state.url + "/offer", json=request())
            ).status_code == 200
            migration = (
                Path(__file__).resolve().parents[3]
                / "database/migrations/20261027064000_conversation_offer_requests.sql"
            )
            down = migration.read_text().split("-- migrate:down", 1)[1]
            with pytest.raises(RaiseException, match="Rollback refused"):
                async with pool.connection() as connection, connection.transaction():
                    await connection.execute(down)
            assert (await state.client.get(state.read_url)).status_code == 200

    run_scenario(scenario)


def test_offer_entries_do_not_break_incremental_message_paging():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            assert (
                await state.client.put(state.url + "/offer", json=request())
            ).status_code == 200
            await register_members(state)
            message = await PostgresMessageOperations(pool).submit_message(
                state.actor, state.thread, message_request()
            )
            page = await PostgresMessageOperations(pool).read_entries(
                state.actor, state.thread, EntryQuery()
            )
            assert [item.entry_id for item in page.items] == [message.entry.entry_id]
            assert page.scanned_through_sequence == 2

    run_scenario(scenario)
