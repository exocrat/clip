"""Exercise Listings persistence against the isolated migrated PostgreSQL schema.

Run through ``scripts/check_database.py``. Its test-only Identity and
Conversations doubles avoid claiming those upstream implementations are ready;
the Listings rows, image references and retry receipts are real PostgreSQL data.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import os
from typing import Any
from uuid import UUID, uuid4

import pytest
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import (
    AvailabilityChange,
    CreateListingRequest,
    ListingOfferCommand,
    ListingReplacement,
    ListingThreadParticipantCheck,
    OfferView,
    PageQuery,
    ParticipantCheck,
    SelectionChange,
)
from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.service import ListingsService, RetiredListingImage


class _EligibleIdentity:
    """Test-only Identity boundary for a fixed set of synthetic accounts."""

    def __init__(self, eligible_users: set[UUID]) -> None:
        self._eligible_users = eligible_users

    async def account_is_eligible(self, user_id: UUID) -> bool:
        """Return the fixed eligibility result without reading Identity tables."""
        return user_id in self._eligible_users


class _ConversationsDouble:
    """Test-only participant check; it never reads Conversations-owned tables."""

    def __init__(self, buyer_id: UUID, conversation_id: UUID) -> None:
        self._buyer_id = buyer_id
        self._conversation_id = conversation_id
        self._listing_id: UUID | None = None
        self.calls = 0

    def bind_listing(self, listing_id: UUID) -> None:
        """Bind the double to the listing created in this isolated workflow."""
        self._listing_id = listing_id

    async def check_listing_thread_participant(
        self, caller: CallerContext, request: ListingThreadParticipantCheck
    ) -> ParticipantCheck:
        """Approve only the exact synthetic listing, thread and buyer tuple."""
        self.calls += 1
        return ParticipantCheck(
            is_participant=(
                request.listing_id == self._listing_id
                and request.conversation_id == self._conversation_id
                and request.candidate_user_id == self._buyer_id
            )
        )

    async def persist_listing_offer(
        self, caller: CallerContext, request: ListingOfferCommand
    ) -> OfferView:
        """Offer persistence is outside this database adapter checkpoint."""
        raise AssertionError("This check does not invoke Conversations offer writes")


def test_postgres_store_persists_listing_and_owner_command_workflow() -> None:
    """Verify create, edit, buyer selection and availability against real SQL."""
    conninfo = os.environ.get("LISTINGS_TEST_DATABASE_URL")
    if not conninfo:
        pytest.skip("Run scripts/check_database.py to provide isolated PostgreSQL")

    asyncio.run(_exercise_postgres_listing_workflow(conninfo))


async def _exercise_postgres_listing_workflow(conninfo: str) -> None:
    """Seed synthetic boundaries, call the store, and inspect committed rows."""
    pool: AsyncConnectionPool[dict[str, Any]] = AsyncConnectionPool(
        conninfo=conninfo,
        kwargs={"row_factory": dict_row},
        min_size=1,
        max_size=4,
        open=False,
    )
    await pool.open()
    try:
        await pool.wait(timeout=5)
        now = datetime.now(UTC)
        owner_id, buyer_id, outsider_id = uuid4(), uuid4(), uuid4()
        first_upload_id, replacement_upload_id = uuid4(), uuid4()
        conversation_id = uuid4()
        owner = CallerContext(owner_id, "regular", now + timedelta(days=1))
        outsider = CallerContext(outsider_id, "regular", now + timedelta(days=1))

        async with pool.connection() as connection:
            identity = await connection.execute(
                "SELECT current_database() AS name, inet_server_addr() IS NULL AS local_socket"
            )
            target = await identity.fetchone()
            assert target == {"name": "clip_test_ci", "local_socket": True}

            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO identity.users (id, account_class, status, display_name)
                    VALUES (%s, 'regular', 'active', 'Synthetic owner'),
                           (%s, 'regular', 'active', 'Synthetic buyer'),
                           (%s, 'regular', 'active', 'Synthetic outsider')
                    """,
                    (owner_id, buyer_id, outsider_id),
                )
                created_at = now - timedelta(minutes=1)
                for upload_id in (first_upload_id, replacement_upload_id):
                    await connection.execute(
                        """
                        INSERT INTO listings.image_uploads (
                            id, owner_id, object_key, state, created_at, expires_at,
                            confirmed_at, confirmed_media_type, confirmed_size_bytes
                        ) VALUES (%s, %s, %s, 'confirmed', %s, %s, %s, 'image/jpeg', 2048)
                        """,
                        (
                            upload_id,
                            owner_id,
                            f"test/listings/{upload_id}",
                            created_at,
                            created_at + timedelta(hours=24),
                            now,
                        ),
                    )

        identity = _EligibleIdentity({owner_id, buyer_id, outsider_id})
        conversations = _ConversationsDouble(buyer_id, conversation_id)
        store = PostgresListingsStore(pool)
        service = ListingsService(
            store,
            identity,
            clock=lambda: now,
            conversations=conversations,
        )

        create_request = CreateListingRequest(
            title="Synthetic textbook",
            description="A database-only test listing",
            category_code="books",
            condition_code="good",
            asking_price_paise=0,
            negotiable=True,
            pickup_area="Synthetic pickup area",
            available_from=now,
            image_upload_ids=[first_upload_id],
            operation_id=uuid4(),
        )
        created = await service.create(owner, create_request)
        stored = await store.read_listing(created.listing_id)
        assert stored is not None
        assert stored.owner_id == owner_id
        assert stored.title == "Synthetic textbook"
        assert stored.asking_price_paise == 0
        assert len(stored.image_ids) == 1

        # The same create key returns its original response, even after later edits.
        replacement = ListingReplacement(
            expected_revision=1,
            title="Revised synthetic textbook",
            description="The listing was edited in PostgreSQL",
            category_code="books",
            condition_code="good",
            asking_price_paise=1_000,
            negotiable=True,
            pickup_area="Updated synthetic pickup area",
            available_from=now,
            available_until=None,
            proof_available=True,
            image_upload_ids=[replacement_upload_id],
            operation_id=uuid4(),
        )
        edited = await service.replace(owner, created.listing_id, replacement)
        assert edited.title == "Revised synthetic textbook"
        assert (
            await service.create(owner, create_request)
        ).model_dump() == created.model_dump()

        with pytest.raises(PublicError) as changed_create:
            await service.create(
                owner,
                create_request.model_copy(update={"title": "Different intent"}),
            )
        assert changed_create.value.spec.status == 409

        async with pool.connection() as connection:
            images = await connection.execute(
                """
                SELECT count(*) AS total,
                    count(*) FILTER (WHERE retired_at IS NULL) AS live
                FROM listings.images WHERE listing_id = %s
                """,
                (created.listing_id,),
            )
            image_counts = await images.fetchone()
            assert image_counts == {"total": 2, "live": 1}

            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO conversations.threads (
                        id, listing_id, initiator_id, counterparty_id,
                        created_at, last_activity_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        conversation_id,
                        created.listing_id,
                        buyer_id,
                        owner_id,
                        now,
                        now,
                    ),
                )
                await connection.execute(
                    """
                    INSERT INTO conversations.members (conversation_id, user_id)
                    VALUES (%s, %s), (%s, %s)
                    """,
                    (conversation_id, buyer_id, conversation_id, owner_id),
                )

        # Bind the test double to the persisted listing and exact buyer/thread.
        conversations.bind_listing(created.listing_id)
        selection = SelectionChange(
            buyer_id=buyer_id,
            conversation_id=conversation_id,
            expected_revision=2,
            operation_id=uuid4(),
        )
        selected = await service.set_selected_buyer(
            owner, created.listing_id, selection
        )
        assert selected.selected_buyer_id == buyer_id
        assert selected.selected_conversation_id == conversation_id
        assert conversations.calls == 1

        unavailable_request = AvailabilityChange(
            expected_revision=3,
            availability="unavailable",
            operation_id=uuid4(),
        )
        unavailable = await service.change_availability(
            owner, created.listing_id, unavailable_request
        )
        assert unavailable.availability == "unavailable"
        unavailable_owner_view = await store.read_listing(created.listing_id)
        assert unavailable_owner_view is not None
        assert unavailable_owner_view.selected_buyer_id == buyer_id

        # Retrying the old selection returns its saved response, not a new write.
        replayed_selection = await service.set_selected_buyer(
            owner, created.listing_id, selection
        )
        assert replayed_selection.revision == selected.revision
        assert replayed_selection.selected_buyer_id == buyer_id

        with pytest.raises(PublicError) as changed_selection:
            await service.set_selected_buyer(
                owner,
                created.listing_id,
                selection.model_copy(update={"buyer_id": outsider_id}),
            )
        assert changed_selection.value.spec.status == 409

        # A seller can clear the selected buyer after making the listing unavailable.
        clear_selection = SelectionChange(
            buyer_id=None,
            conversation_id=None,
            expected_revision=4,
            operation_id=uuid4(),
        )
        cleared = await service.set_selected_buyer(
            owner, created.listing_id, clear_selection
        )
        assert cleared.selected_buyer_id is None
        assert cleared.selected_conversation_id is None

        mine = await service.list_mine(owner, PageQuery(page=1, page_size=20))
        assert len(mine.items) == 1
        assert mine.items[0].listing_id == created.listing_id
        assert mine.items[0].availability == "unavailable"

        with pytest.raises(PublicError) as wrong_owner:
            await service.change_availability(
                outsider,
                created.listing_id,
                AvailabilityChange(
                    expected_revision=5,
                    availability="available",
                    operation_id=uuid4(),
                ),
            )
        assert wrong_owner.value.spec.status == 403

        async with pool.connection() as connection:
            saved = await connection.execute(
                """
                SELECT listing.title, listing.availability, listing.revision,
                    listing.selected_buyer_id, listing.selected_conversation_id,
                    count(DISTINCT image.id) FILTER (WHERE image.retired_at IS NULL)
                        AS live_images,
                    count(DISTINCT created.operation_id) AS create_receipts,
                    count(DISTINCT owner_result.operation_id) AS owner_receipts
                FROM listings.sale_listings AS listing
                LEFT JOIN listings.images AS image ON image.listing_id = listing.id
                LEFT JOIN listings.create_command_results AS created
                    ON created.listing_id = listing.id
                LEFT JOIN listings.owner_command_results AS owner_result
                    ON owner_result.listing_id = listing.id
                WHERE listing.id = %s
                GROUP BY listing.id
                """,
                (created.listing_id,),
            )
            final_row = await saved.fetchone()
        assert final_row == {
            "title": "Revised synthetic textbook",
            "availability": "unavailable",
            "revision": 5,
            "selected_buyer_id": None,
            "selected_conversation_id": None,
            "live_images": 1,
            "create_receipts": 1,
            "owner_receipts": 3,
        }

        pending_operation_id = uuid4()
        saved_cutoff = now - timedelta(days=90)
        async with pool.connection() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    UPDATE listings.sale_listings
                    SET retirement_pending_operation_id = %s,
                        retirement_pending_cutoff_utc = %s
                    WHERE id = %s
                    """,
                    (pending_operation_id, saved_cutoff, created.listing_id),
                )

        # Pending rows disappear from normal reads and command guards, but stay
        # in the seller's management list while the listing content is retained.
        assert await store.read_listing(created.listing_id) is None
        with pytest.raises(PublicError) as pending_create_retry:
            await store.previous_create_command_result(owner_id, create_request)
        assert pending_create_retry.value.spec.status == 409
        pending_owner_page = await store.list_owned_listings(
            owner_id, PageQuery(page=1, page_size=20)
        )
        assert [item.listing_id for item in pending_owner_page.items] == [
            created.listing_id
        ]
        async with store.listing_offer_guard(created.listing_id) as pending_listing:
            assert pending_listing is None
        with pytest.raises(PublicError) as pending_edit:
            await service.change_availability(
                owner,
                created.listing_id,
                AvailabilityChange(
                    expected_revision=5,
                    availability="available",
                    operation_id=uuid4(),
                ),
            )
        assert pending_edit.value.spec.status == 404

        # A retry receives the original cutoff, even when the process clock moves.
        resumed = await store.begin_listing_retirement(
            created.listing_id,
            pending_operation_id,
            now + timedelta(days=30),
        )
        assert resumed is not None
        assert resumed.operation_id == pending_operation_id
        assert resumed.cutoff_utc == saved_cutoff

        await store.clear_listing_retirement_pending(
            created.listing_id, pending_operation_id
        )
        visible_again = await store.read_listing(created.listing_id)
        assert visible_again is not None

        # Use a separate old listing so the real database guard sees the full
        # 180-day local eligibility period during finalization.
        old_listing_id, old_upload_id, old_image_id = uuid4(), uuid4(), uuid4()
        old_operation_id = uuid4()
        old_created = now - timedelta(days=200)
        old_available_from = now - timedelta(days=201)
        old_available_until = now - timedelta(days=190)
        old_object_key = f"test/listings/{old_upload_id}"
        async with pool.connection() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO listings.sale_listings (
                        id, owner_id, title, description, category_id,
                        condition_code, asking_price_paise, negotiable,
                        pickup_area, available_from, available_until,
                        availability, proof_available, created_at, updated_at
                    ) VALUES (
                        %s, %s, 'Old synthetic listing', 'For retirement test',
                        (SELECT id FROM listings.categories WHERE code = 'books'),
                        'good', 10000, TRUE, 'Synthetic area', %s, %s,
                        'unavailable', FALSE, %s, %s
                    )
                    """,
                    (
                        old_listing_id,
                        owner_id,
                        old_available_from,
                        old_available_until,
                        old_created,
                        old_created,
                    ),
                )
                await connection.execute(
                    """
                    INSERT INTO listings.image_uploads (
                        id, owner_id, object_key, state, created_at, expires_at,
                        confirmed_at, confirmed_media_type, confirmed_size_bytes
                    ) VALUES (%s, %s, %s, 'confirmed', %s, %s, %s, 'image/jpeg', 2048)
                    """,
                    (
                        old_upload_id,
                        owner_id,
                        old_object_key,
                        now - timedelta(minutes=1),
                        now + timedelta(hours=23, minutes=59),
                        now - timedelta(minutes=1),
                    ),
                )
                await connection.execute(
                    """
                    INSERT INTO listings.images (
                        id, listing_id, upload_id, object_key, position,
                        media_type, size_bytes, created_at
                    ) VALUES (%s, %s, %s, %s, 0, 'image/jpeg', 2048, %s)
                    """,
                    (
                        old_image_id,
                        old_listing_id,
                        old_upload_id,
                        old_object_key,
                        now,
                    ),
                )
                await connection.execute(
                    """
                    INSERT INTO listings.create_command_results (
                        owner_id, operation_id, listing_id, request_payload, result_payload
                    ) VALUES (%s, %s, %s, '{"title":"private"}', '{"title":"private"}')
                    """,
                    (owner_id, old_operation_id, old_listing_id),
                )
                await connection.execute(
                    """
                    INSERT INTO listings.owner_command_results (
                        listing_id, command_kind, operation_id, request_payload, result_payload
                    ) VALUES (%s, 'availability', %s, '{}', '{}')
                    """,
                    (old_listing_id, uuid4()),
                )

        old_pending = await store.begin_listing_retirement(
            old_listing_id, old_operation_id, now
        )
        assert old_pending is not None
        await store.finalize_listing_retirement(old_listing_id, old_pending, now)
        assert await store.read_listing(old_listing_id) is None
        retired_images = await store.list_retired_images_for_cleanup(10)
        assert len(retired_images) == 1
        assert (
            RetiredListingImage(image_id=old_image_id, object_key=old_object_key)
            in retired_images
        )

        async with pool.connection() as connection:
            retired = await connection.execute(
                """
                SELECT title, description, asking_price_paise, pickup_area,
                    selected_buyer_id, selected_conversation_id, retired_at,
                    retirement_pending_operation_id, retirement_pending_cutoff_utc
                FROM listings.sale_listings WHERE id = %s
                """,
                (old_listing_id,),
            )
            retired_row = await retired.fetchone()
            receipts = await connection.execute(
                """
                SELECT request_payload, result_payload
                FROM listings.create_command_results WHERE listing_id = %s
                """,
                (old_listing_id,),
            )
            receipt_row = await receipts.fetchone()
            owner_receipts = await connection.execute(
                """SELECT count(*) AS count FROM listings.owner_command_results
                WHERE listing_id = %s""",
                (old_listing_id,),
            )
            owner_receipt_count = await owner_receipts.fetchone()
        assert retired_row["title"] is None
        assert retired_row["description"] is None
        assert retired_row["asking_price_paise"] is None
        assert retired_row["pickup_area"] is None
        assert retired_row["selected_buyer_id"] is None
        assert retired_row["selected_conversation_id"] is None
        assert retired_row["retired_at"] is not None
        assert retired_row["retirement_pending_operation_id"] is None
        assert retired_row["retirement_pending_cutoff_utc"] is None
        assert receipt_row == {"request_payload": None, "result_payload": None}
        assert owner_receipt_count == {"count": 0}

        for queued_image in retired_images:
            await store.finish_retired_image_cleanup(
                queued_image.image_id, queued_image.object_key
            )
        assert await store.list_retired_images_for_cleanup(10) == ()
        async with pool.connection() as connection:
            rows = await connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM listings.images WHERE listing_id = %s) AS images,
                    (SELECT count(*) FROM listings.image_uploads WHERE id = %s) AS uploads
                """,
                (old_listing_id, old_upload_id),
            )
            cleanup_counts = await rows.fetchone()
        assert cleanup_counts == {"images": 0, "uploads": 0}
    finally:
        await pool.close()
