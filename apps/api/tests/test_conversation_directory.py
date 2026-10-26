"""Real disposable-PostgreSQL checks; Identity contexts are test-only doubles."""

import asyncio
from base64 import b64encode
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.contracts.domain_types import (
    ConversationQuery,
    PreKeyBundleRequest,
    PublicKeyBundleRequest,
    PublicPreKeyBatchRequest,
    PublicPreKeyMaterial,
)
from app.core.auth import require_caller
from app.core.config import Settings
from app.core.errors import PublicError
from app.domains.conversations.key_directory import PostgresKeyDirectory
from app.domains.conversations.messages import PostgresMessageOperations
from app.domains.conversations.queries import PostgresConversationQueries
from app.main import create_app
from test_conversation_messages import (
    TEST_DATABASE_DSN,
    caller,
    message_request,
    run_scenario,
    seed_thread,
)


def public_bundle(**changes) -> PublicKeyBundleRequest:
    """Shape-valid synthetic public bytes; no private keys or crypto claims."""

    def encoded(value: bytes, length: int) -> str:
        return b64encode(value * length).decode("ascii")

    return PublicKeyBundleRequest(
        **{
            "protocol_id": "open-e2ee-signal",
            "protocol_version": "13.0.0",
            "registration_id": 1,
            "device_id": 1,
            "identity": {
                "version": 1,
                "x25519_public_key_base64": encoded(b"x", 32),
                "ed25519_public_key_base64": encoded(b"e", 32),
            },
            "ec_signed_prekey": {
                "key_id": 1,
                "public_key_base64": encoded(b"s", 32),
                "signature_base64": encoded(b"g", 64),
            },
            "kem_last_resort_prekey": {
                "key_id": 2,
                "public_key_base64": encoded(b"k", 1569),
                "signature_base64": encoded(b"g", 64),
            },
            "operation_id": uuid4(),
            **changes,
        }
    )


def prekey(key_id: int, *, kem: bool = False) -> PublicPreKeyMaterial:
    return PublicPreKeyMaterial(
        key_type="kemOneTimePreKey" if kem else "ecPreKey",
        key_id=key_id,
        public_key_base64=b64encode(b"p" * (1569 if kem else 32)).decode("ascii"),
        signature_base64=b64encode(b"g" * 64).decode("ascii") if kem else None,
    )


def test_own_key_lookup_distinguishes_first_use_rotation_and_retired_state():
    async def scenario(pool):
        from test_thread_creation import seed_users_and_listing

        alice, bob, _ = await seed_users_and_listing(pool)
        keys = PostgresKeyDirectory(pool)
        assert await keys.read_own_key(caller(alice)) is None
        registered = await keys.register_own_key(caller(alice), public_bundle())
        own = await keys.read_own_key(caller(alice))
        assert own.user_id == alice and own.key_version == registered.key_version == 1
        assert await keys.read_own_key(caller(bob)) is None
        from dataclasses import replace

        expired = replace(
            caller(alice), valid_until=datetime.now(UTC) - timedelta(seconds=1)
        )
        with pytest.raises(PublicError) as error:
            await keys.read_own_key(expired)
        assert error.value.spec.status == 401
        await keys.register_own_key(caller(alice), public_bundle(registration_id=2))
        assert (await keys.read_own_key(caller(alice))).registration_id == 2
        async with pool.connection() as connection:
            await connection.execute(
                "UPDATE conversations.public_key_versions SET retired_at = clock_timestamp() "
                "WHERE user_id = %s AND retired_at IS NULL",
                (alice,),
            )
        with pytest.raises(PublicError) as error:
            await keys.read_own_key(caller(alice))
        assert error.value.spec.status == 409

        # Even missing bundle rows cannot erase durable registration evidence.
        async with pool.connection() as connection:
            await connection.execute(
                "DELETE FROM conversations.public_key_versions WHERE user_id = %s",
                (alice,),
            )
        with pytest.raises(PublicError) as error:
            await keys.read_own_key(caller(alice))
        assert error.value.spec.status == 409

    run_scenario(scenario)


def test_own_key_lookup_never_maps_corrupt_or_misbound_material_to_absence():
    async def scenario(pool):
        alice, bob, *_ = await seed_thread(pool)
        keys = PostgresKeyDirectory(pool)
        with pytest.raises(PublicError) as error:
            await keys.read_own_key(caller(alice))
        assert error.value.spec.status == 503
        await keys.register_own_key(caller(alice), public_bundle())
        own = await keys.read_own_key(caller(alice))
        # Simulate corrupt imported storage, not an application registration path.
        async with pool.connection() as connection:
            await connection.execute(
                "UPDATE conversations.public_key_versions SET retired_at = clock_timestamp() "
                "WHERE user_id = %s AND retired_at IS NULL",
                (bob,),
            )
            await connection.execute(
                "INSERT INTO conversations.public_key_versions "
                "(id, user_id, version, protocol_id, public_key_material) VALUES (%s, %s, 2, %s, %s)",
                (uuid4(), bob, own.protocol_id, own.model_dump_json().encode()),
            )
        with pytest.raises(PublicError) as error:
            await keys.read_own_key(caller(bob))
        assert error.value.spec.status == 503

    run_scenario(scenario)


def test_own_key_lookup_is_coherent_during_registration():
    async def scenario(pool):
        alice, *_ = await seed_thread(pool)
        keys = PostgresKeyDirectory(pool)
        await keys.register_own_key(caller(alice), public_bundle())
        rotation, *reads = await asyncio.gather(
            keys.register_own_key(caller(alice), public_bundle()),
            *(keys.read_own_key(caller(alice)) for _ in range(3)),
        )
        assert rotation.key_version == 3
        assert all(
            value is not None and value.user_id == alice and value.key_version in (2, 3)
            for value in reads
        )
        assert (await keys.read_own_key(caller(alice))).key_version == 3

    run_scenario(scenario)


def test_inbox_membership_filters_unread_and_summary_privacy():
    async def scenario(pool):
        alice, bob, origin, thread, *_ = await seed_thread(pool)
        service = PostgresConversationQueries(pool)
        messages = PostgresMessageOperations(pool)
        await messages.submit_message(caller(alice), thread, message_request())
        page = await service.list_mine(caller(bob), ConversationQuery(origin_id=origin))
        assert len(page.items) == 1 and not page.has_next
        summary = page.items[0]
        assert summary.caller_role == "initiator" and summary.unread_count == 1
        assert summary.counterparty_user_id == alice
        assert summary.origin_kind == "wanted_request"
        assert summary == await service.read_summary(caller(bob), thread)
        assert not (
            await service.list_mine(caller(bob), ConversationQuery(view="origin_owner"))
        ).items
        assert (
            await service.list_mine(
                caller(alice), ConversationQuery(view="origin_owner", origin_id=origin)
            )
        ).items
        assert not (
            await service.list_mine(caller(bob), ConversationQuery(offer_min_paise=0))
        ).items
        assert not (
            await service.list_mine(
                caller(bob), ConversationQuery(counterparty_user_id=bob)
            )
        ).items
        for target in (thread, uuid4()):
            with pytest.raises(PublicError) as error:
                await service.read_summary(caller(uuid4()), target)
            assert error.value.spec.status == 404
        with pytest.raises(PublicError) as error:
            await service.list_mine(
                caller(bob), ConversationQuery(offer_min_paise=200, offer_max_paise=100)
            )
        assert error.value.spec.status == 422

    run_scenario(scenario)


def test_inbox_pagination_and_deterministic_ties():
    async def scenario(pool):
        bob = uuid4()
        threads = []
        for _ in range(21):
            _, _, _, thread, *_ = await seed_thread(pool, responder_id=bob)
            threads.append(thread)
        async with pool.connection() as connection:
            await connection.execute(
                "UPDATE conversations.threads SET last_activity_at = %s WHERE id = ANY(%s)",
                (datetime.now(UTC) + timedelta(seconds=1), threads),
            )
        service = PostgresConversationQueries(pool)
        first = await service.list_mine(caller(bob), ConversationQuery())
        second = await service.list_mine(caller(bob), ConversationQuery(page=2))
        assert first.has_next and len(first.items) == 20
        assert not second.has_next and len(second.items) == 1
        assert [item.conversation_id for item in first.items + second.items] == sorted(
            threads, reverse=True
        )

    run_scenario(scenario)


def test_sale_inbox_offer_sorting_filters_and_no_offer_rows():
    async def scenario(pool):
        from test_thread_creation import seed_users_and_listing

        owner, buyer, listing = await seed_users_and_listing(pool)
        expected = []
        async with pool.connection() as connection:
            async with connection.transaction():
                for index, amount in enumerate((100, 300, None)):
                    participant = buyer if index == 0 else uuid4()
                    if index:
                        await connection.execute(
                            "INSERT INTO identity.users (id, account_class, status) VALUES (%s, 'regular', 'active')",
                            (participant,),
                        )
                    thread = uuid4()
                    expected.append(thread)
                    await connection.execute(
                        "INSERT INTO conversations.threads (id, listing_id, initiator_id, counterparty_id) VALUES (%s, %s, %s, %s)",
                        (thread, listing, participant, owner),
                    )
                    await connection.execute(
                        "INSERT INTO conversations.members (conversation_id, user_id) VALUES (%s, %s), (%s, %s)",
                        (thread, participant, thread, owner),
                    )
                    if amount is not None:
                        entry, offer = uuid4(), uuid4()
                        await connection.execute(
                            "INSERT INTO conversations.entries (id, conversation_id, sender_id, client_operation_id, kind) VALUES (%s, %s, %s, %s, 'offer')",
                            (entry, thread, participant, uuid4()),
                        )
                        await connection.execute(
                            "INSERT INTO conversations.offers (id, conversation_id, buyer_id, current_revision, next_revision) VALUES (%s, %s, %s, 1, 2)",
                            (offer, thread, participant),
                        )
                        await connection.execute(
                            "INSERT INTO conversations.offer_revisions (offer_id, revision, entry_id, amount_paise, status) VALUES (%s, 1, %s, %s, 'submitted')",
                            (offer, entry, amount),
                        )
        service = PostgresConversationQueries(pool)
        for sort, order in (
            ("offer_amount_asc", expected),
            ("offer_amount_desc", [expected[1], expected[0], expected[2]]),
        ):
            page = await service.list_mine(
                caller(owner), ConversationQuery(origin_id=listing, sort=sort)
            )
            assert [item.conversation_id for item in page.items] == order
            assert all(
                item.origin_kind == "sale_listing"
                and item.caller_role == "origin_owner"
                for item in page.items
            )
            assert page.items[-1].current_offer is None
        page = await service.list_mine(
            caller(owner),
            ConversationQuery(
                origin_id=listing,
                offer_min_paise=200,
                offer_max_paise=400,
                offer_status="submitted",
            ),
        )
        assert [item.conversation_id for item in page.items] == [expected[1]]
        assert page.items[0].current_offer.amount_paise == 300
        assert not (
            await service.list_mine(
                caller(owner),
                ConversationQuery(origin_kind="wanted_request", origin_id=listing),
            )
        ).items

    run_scenario(scenario)


def test_registration_retry_conflict_rotation_and_historical_thread_keys():
    async def scenario(pool):
        alice, bob, _, thread, *_ = await seed_thread(pool)
        keys = PostgresKeyDirectory(pool)
        request = public_bundle()
        registered = await keys.register_own_key(caller(alice), request)
        assert registered.key_version == 2
        assert await keys.register_own_key(caller(alice), request) == registered
        with pytest.raises(PublicError) as error:
            await keys.register_own_key(
                caller(alice), request.model_copy(update={"registration_id": 2})
            )
        assert error.value.spec.status == 409
        await keys.register_own_key(caller(bob), public_bundle())
        await PostgresMessageOperations(pool).submit_message(
            caller(alice),
            thread,
            message_request(sender_version=2, recipient_version=2),
        )
        rotated = await keys.register_own_key(caller(alice), public_bundle())
        assert rotated.key_version == 3
        members = await keys.read_member_keys(caller(bob), thread)
        assert {(key.user_id, key.key_version) for key in members.members} == {
            (alice, 2),
            (alice, 3),
            (bob, 2),
        }
        assert "private" not in members.model_dump_json()
        with pytest.raises(PublicError) as error:
            await keys.read_member_keys(caller(uuid4()), thread)
        assert error.value.spec.status == 404

    run_scenario(scenario)


def test_prekey_batches_atomic_retry_reservation_depletion_and_target_conflict():
    async def scenario(pool):
        alice, bob, _, thread, *_ = await seed_thread(pool)
        keys = PostgresKeyDirectory(pool)
        await keys.register_own_key(caller(alice), public_bundle())
        batch = PublicPreKeyBatchRequest(
            key_version=2,
            prekeys=[prekey(1), prekey(2, kem=True)],
            operation_id=uuid4(),
        )
        result = await keys.publish_own_prekeys(caller(alice), batch)
        assert result.ec_one_time_count == result.kem_one_time_count == 1
        assert await keys.publish_own_prekeys(caller(alice), batch) == result
        # A new key before a duplicate must roll back with the whole rejected batch.
        with pytest.raises(PublicError) as error:
            await keys.publish_own_prekeys(
                caller(alice),
                PublicPreKeyBatchRequest(
                    key_version=2, prekeys=[prekey(9), prekey(1)], operation_id=uuid4()
                ),
            )
        assert error.value.spec.status == 409
        assert (await keys.read_own_inventory(caller(alice))).ec_one_time_count == 1
        reservation = PreKeyBundleRequest(operation_id=uuid4())
        selected = await keys.consume_member_prekeys(caller(bob), thread, reservation)
        assert selected.ec_one_time_prekey.key_id == 1
        assert selected.kem_one_time_prekey.key_id == 2
        assert (
            await keys.consume_member_prekeys(caller(bob), thread, reservation)
            == selected
        )
        depleted = await keys.consume_member_prekeys(
            caller(bob), thread, PreKeyBundleRequest(operation_id=uuid4())
        )
        assert (
            depleted.ec_one_time_prekey is None and depleted.kem_one_time_prekey is None
        )
        assert (await keys.read_own_inventory(caller(alice))).ec_one_time_count == 0
        # Replaying publication returns its original result, not today's depleted count.
        assert await keys.publish_own_prekeys(caller(alice), batch) == result
        _, _, _, other, *_ = await seed_thread(pool, responder_id=bob)
        with pytest.raises(PublicError) as error:
            await keys.consume_member_prekeys(caller(bob), other, reservation)
        assert error.value.spec.status == 409

    run_scenario(scenario)


def test_concurrent_prekey_consumers_never_reserve_the_same_key():
    async def scenario(pool):
        alice, bob, _, thread, *_ = await seed_thread(pool)
        keys = PostgresKeyDirectory(pool)
        await keys.register_own_key(caller(alice), public_bundle())
        await keys.publish_own_prekeys(
            caller(alice),
            PublicPreKeyBatchRequest(
                key_version=2, prekeys=[prekey(1), prekey(2)], operation_id=uuid4()
            ),
        )
        results = await asyncio.gather(
            *(
                keys.consume_member_prekeys(
                    caller(bob), thread, PreKeyBundleRequest(operation_id=uuid4())
                )
                for _ in range(3)
            )
        )
        ids = [
            result.ec_one_time_prekey.key_id
            for result in results
            if result.ec_one_time_prekey
        ]
        assert sorted(ids) == [1, 2]
        assert (await keys.read_own_inventory(caller(alice))).ec_one_time_count == 0

    run_scenario(scenario)


def test_concurrent_registration_and_reservation_retries_are_exact():
    async def scenario(pool):
        alice, bob, _, thread, *_ = await seed_thread(pool)
        keys = PostgresKeyDirectory(pool)
        registration = public_bundle()
        first, second = await asyncio.gather(
            *(keys.register_own_key(caller(alice), registration) for _ in range(2))
        )
        assert first == second and first.key_version == 2
        await keys.publish_own_prekeys(
            caller(alice),
            PublicPreKeyBatchRequest(
                key_version=2, prekeys=[prekey(1), prekey(2)], operation_id=uuid4()
            ),
        )
        request = PreKeyBundleRequest(operation_id=uuid4())
        left, right = await asyncio.gather(
            *(
                keys.consume_member_prekeys(caller(bob), thread, request)
                for _ in range(2)
            )
        )
        assert left == right and left.ec_one_time_prekey.key_id == 1
        assert (await keys.read_own_inventory(caller(alice))).ec_one_time_count == 1
        versions = await asyncio.gather(
            *(keys.register_own_key(caller(alice), public_bundle()) for _ in range(2))
        )
        assert sorted(value.key_version for value in versions) == [3, 4]
        # A completed reservation keeps its old public bundle across key rotation.
        assert await keys.consume_member_prekeys(caller(bob), thread, request) == left

    run_scenario(scenario)


def test_missing_stale_incompatible_and_expired_keys_fail_closed():
    async def scenario(pool):
        alice, bob, _, thread, *_ = await seed_thread(pool)
        keys = PostgresKeyDirectory(pool)
        # The old test fixture intentionally contains opaque, non-SDK legacy keys.
        with pytest.raises(PublicError) as error:
            await keys.read_member_keys(caller(alice), thread)
        assert error.value.spec.status == 503
        with pytest.raises(PublicError) as error:
            await keys.read_own_inventory(caller(uuid4()))
        assert error.value.spec.status == 409
        with pytest.raises(PublicError) as error:
            await keys.register_own_key(
                caller(alice), public_bundle(protocol_version="unsupported")
            )
        assert error.value.spec.status == 422
        await keys.register_own_key(caller(alice), public_bundle())
        with pytest.raises(PublicError) as error:
            await keys.publish_own_prekeys(
                caller(alice),
                PublicPreKeyBatchRequest(
                    key_version=1, prekeys=[prekey(1)], operation_id=uuid4()
                ),
            )
        assert error.value.spec.status == 409
        expired = caller(bob)
        from dataclasses import replace

        expired = replace(expired, valid_until=datetime.now(UTC) - timedelta(seconds=1))
        with pytest.raises(PublicError) as error:
            await keys.consume_member_prekeys(
                expired, thread, PreKeyBundleRequest(operation_id=uuid4())
            )
        assert error.value.spec.status == 401
        with pytest.raises(PublicError) as error:
            await keys.consume_member_prekeys(
                caller(uuid4()), thread, PreKeyBundleRequest(operation_id=uuid4())
            )
        assert error.value.spec.status == 404

    run_scenario(scenario)


def test_directory_rollback_refuses_to_erase_durable_state():
    async def scenario(pool):
        from pathlib import Path
        from psycopg import errors

        alice, *_ = await seed_thread(pool)
        await PostgresKeyDirectory(pool).register_own_key(
            caller(alice), public_bundle()
        )
        migration = Path(
            "database/migrations/20261026090200_conversation_public_key_directory.sql"
        ).read_text()
        down = migration.split("-- migrate:down", 1)[1]
        async with pool.connection() as connection:
            with pytest.raises(errors.RaiseException):
                async with connection.transaction():
                    await connection.execute(down)
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.key_directory_operations WHERE user_id = %s",
                (alice,),
            )
            assert (await cursor.fetchone())[0] == 1

    run_scenario(scenario)


@pytest.mark.parametrize(
    "path",
    [
        "/conversations",
        "/conversations/{id}",
        "/conversations/{id}/keys",
        "/me/conversation-prekeys",
        "/me/conversation-key",
    ],
)
def test_directory_http_reads_require_trusted_auth_and_a_database(path):
    path = path.format(id=uuid4())
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        assert client.get(path).status_code == 401
    app.dependency_overrides[require_caller] = lambda: caller(uuid4())
    with TestClient(app) as client:
        assert client.get(path).status_code == 503


def test_directory_http_writes_have_no_client_identity_bypass():
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        for method, path, body in (
            ("put", "/me/conversation-key", public_bundle().model_dump(mode="json")),
            (
                "post",
                "/me/conversation-prekeys",
                {
                    "key_version": 1,
                    "prekeys": [prekey(1).model_dump()],
                    "operation_id": str(uuid4()),
                },
            ),
            (
                "post",
                f"/conversations/{uuid4()}/prekey-bundle",
                {"operation_id": str(uuid4())},
            ),
        ):
            response = getattr(client, method)(
                path, json=body, headers={"X-User-ID": str(uuid4())}
            )
            assert response.status_code == 401


def test_http_own_key_lookup_is_account_scoped_without_a_conversation():
    async def scenario(pool):
        from test_thread_creation import seed_users_and_listing

        alice, bob, _ = await seed_users_and_listing(pool)
        actor = [caller(alice)]
        app = create_app(Settings(environment="test", database_dsn=TEST_DATABASE_DSN))
        app.dependency_overrides[require_caller] = lambda: actor[0]
        with TestClient(app) as client:
            fresh = client.get("/me/conversation-key")
            assert fresh.status_code == 200 and fresh.json() is None
            assert fresh.headers["cache-control"] == "no-store"
            assert (
                client.put(
                    "/me/conversation-key", json=public_bundle().model_dump(mode="json")
                ).status_code
                == 200
            )
            own = client.get("/me/conversation-key")
            assert own.status_code == 200
            assert own.json()["user_id"] == str(alice)
            assert own.json()["key_version"] == 1
            assert set(own.json()) == {
                "user_id",
                "key_version",
                "protocol_id",
                "protocol_version",
                "registration_id",
                "device_id",
                "identity",
                "ec_signed_prekey",
                "kem_last_resort_prekey",
            }
            actor[0] = caller(bob)
            assert (
                client.get(
                    f"/me/conversation-key?user_id={alice}",
                    headers={"X-User-ID": str(alice)},
                ).json()
                is None
            )

    run_scenario(scenario)


def test_http_endpoints_round_trip_through_real_postgres_with_test_identity():
    """Exercise mounted handlers and wire models; only Identity is overridden."""

    async def scenario(pool):
        alice, bob, _, thread, *_ = await seed_thread(pool)
        actor = [caller(alice)]
        app = create_app(Settings(environment="test", database_dsn=TEST_DATABASE_DSN))
        app.dependency_overrides[require_caller] = lambda: actor[0]
        with TestClient(app) as client:
            for user_id in (alice, bob):
                actor[0] = caller(user_id)
                response = client.put(
                    "/me/conversation-key", json=public_bundle().model_dump(mode="json")
                )
                assert response.status_code == 200
                assert response.json()["user_id"] == str(user_id)
            response = client.get(
                "/conversations", params={"origin_kind": "wanted_request"}
            )
            assert response.status_code == 200
            assert response.json()["items"][0]["conversation_id"] == str(thread)
            assert client.get(f"/conversations/{thread}").status_code == 200
            assert (
                len(client.get(f"/conversations/{thread}/keys").json()["members"]) == 2
            )
            batch = PublicPreKeyBatchRequest(
                key_version=2, prekeys=[prekey(1)], operation_id=uuid4()
            )
            assert (
                client.post(
                    "/me/conversation-prekeys", json=batch.model_dump(mode="json")
                ).status_code
                == 200
            )
            assert (
                client.get("/me/conversation-prekeys").json()["ec_one_time_count"] == 1
            )
            actor[0] = caller(alice)
            reservation = client.post(
                f"/conversations/{thread}/prekey-bundle",
                json={"operation_id": str(uuid4())},
            )
            assert reservation.status_code == 200
            assert reservation.json()["ec_one_time_prekey"]["key_id"] == 1
            assert (
                client.get(
                    "/conversations",
                    params={"offer_min_paise": 200, "offer_max_paise": 100},
                ).status_code
                == 422
            )
            assert (
                client.get("/conversations", params={"unknown": "field"}).status_code
                == 422
            )
            actor[0] = caller(uuid4())
            assert client.get(f"/conversations/{thread}").status_code == 404
            assert client.get(f"/conversations/{thread}/keys").status_code == 404

    run_scenario(scenario)
