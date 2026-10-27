"""PostgreSQL implementation of the Listings-owned transactional store."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from psycopg import AsyncConnection, OperationalError
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.core.errors import ERRORS, FieldError, PublicError
from app.core.pagination import Page
from app.contracts.domain_types import (
    AvailabilityChange,
    CategoryCode,
    Category,
    CatalogueView,
    ConfirmedImage,
    CreateListingRequest,
    ExistingListingImage,
    ImageId,
    ImageUploadRequest,
    ListingDetail,
    ListingId,
    ListingManagementView,
    ListingSummary,
    ListingQuery,
    ListingReplacement,
    NewListingImage,
    PageQuery,
    SelectionChange,
    UserId,
)
from app.domains.listings.service import (
    AbandonedImageUpload,
    ListingImageDeliveryTarget,
    PendingImageUpload,
    PendingListingRetirement,
    RetiredListingImage,
)
from app.domains.listings.browse_store import (
    read_browse_page,
    validate_catalogue_filters,
)
from app.domains.listings.browse_validation import normalize_query
from app.domains.listings.embedding_client import SemanticHelper
from app.domains.listings.hybrid_read import search_hybrid_page

# This projection keeps list/detail reads to one SQL query per request. The
# threshold is injected from typed API settings so every read uses the same
# approved, configurable Listings value.
_RETAINED_VIEW_QUERY = """
SELECT
    listing.id AS listing_id,
    listing.owner_id,
    listing.title,
    listing.description,
    category.code AS category_code,
    category.label AS category_label,
    listing_condition.code AS condition_code,
    listing_condition.label AS condition_label,
    listing.asking_price_paise,
    listing.negotiable,
    listing.pickup_area,
    listing.available_from,
    listing.available_until,
    listing.availability,
    (category.sensitive_category OR listing.asking_price_paise > %s)
        AS sensitive_purchase,
    COALESCE(
        (SELECT array_agg(image.id ORDER BY image.position, image.id)
         FROM listings.images AS image
         WHERE image.listing_id = listing.id AND image.retired_at IS NULL),
        ARRAY[]::uuid[]
    ) AS image_ids,
    listing.proof_available,
    listing.revision,
    listing.selected_buyer_id,
    listing.selected_conversation_id,
    listing.created_at,
    listing.updated_at
FROM listings.sale_listings AS listing
JOIN listings.categories AS category ON category.id = listing.category_id
JOIN listings.conditions AS listing_condition
    ON listing_condition.code = listing.condition_code
WHERE listing.retired_at IS NULL
"""

# Public reads and command guards hide an origin once a retirement request is
# pending. The owner's management list uses the retained-only query above so a
# still-retained listing does not disappear from My Listings during recovery.
_VIEW_QUERY = (
    _RETAINED_VIEW_QUERY + " AND listing.retirement_pending_operation_id IS NULL"
)

_PRIVATE_DETAIL_FIELDS = (
    "owner_id",
    "revision",
    "selected_buyer_id",
    "selected_conversation_id",
    "created_at",
    "updated_at",
)


def _field_error(field: str, code: str) -> PublicError:
    """Build safe validation metadata without echoing a database value."""
    return PublicError(ERRORS[422], (FieldError(field, code),))


def _conflict() -> PublicError:
    """Return the contract's fixed revision/idempotency conflict."""
    return PublicError(ERRORS[409])


def _management_view(row: dict[str, Any]) -> ListingManagementView:
    """Validate a SQL projection against the generated owner-view contract."""
    return ListingManagementView.model_validate(row)


def _public_detail(view: ListingManagementView) -> ListingDetail:
    """Remove selection, owner and revision fields from create receipts."""
    values = view.model_dump()
    for field in _PRIVATE_DETAIL_FIELDS:
        values.pop(field)
    return ListingDetail.model_validate(values)


class PostgresListingsStore:
    """Run Listings reads and writes through one injected async PostgreSQL pool."""

    def __init__(
        self,
        pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]],
        sensitive_price_threshold_paise: int,
        isolated_listing_limit: int | None = None,
        *,
        hybrid_helper: SemanticHelper | None = None,
        hybrid_pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] | None = None,
    ) -> None:
        """Bind the pool, price threshold, and optional isolated-demo limit."""
        if (
            type(sensitive_price_threshold_paise) is not int
            or sensitive_price_threshold_paise < 0
            or sensitive_price_threshold_paise % 100 != 0
        ):
            raise ValueError("The sensitive-purchase threshold must be whole rupees")
        # Explicit injection only: construction never starts a helper. Hybrid
        # also requires an idle autocommit pool connection; its reader fails
        # closed rather than changing a caller-owned transaction configuration.
        self._hybrid_helper = hybrid_helper
        self._hybrid_pool = hybrid_pool
        self._pool = pool
        self._threshold = sensitive_price_threshold_paise
        if isolated_listing_limit is not None and (
            type(isolated_listing_limit) is not int or isolated_listing_limit < 1
        ):
            raise ValueError("The isolated listing limit must be a positive integer")
        self._isolated_listing_limit = isolated_listing_limit

    async def browse_available_listings(
        self, request: ListingQuery, now: datetime
    ) -> Page[ListingSummary]:
        """Dispatch validated modes after the service authorizes the caller.

        Blank text always browses without semantic dependencies. Nonblank Hybrid
        needs an explicitly managed helper and idle autocommit connection; absent
        capability returns503 without falling back. Keyword never uses the helper.
        """
        request = normalize_query(request)
        hybrid = request.search_mode == "hybrid" and request.q is not None
        if hybrid and self._hybrid_helper is None:
            if request.category_code is not None or request.condition_code is not None:
                async with self._connection() as connection:
                    await validate_catalogue_filters(connection, request)
            raise PublicError(ERRORS[503])
        # Only Hybrid borrows the lifecycle-owned autocommit pool. Keyword and
        # commands retain their original pool and transaction configuration.
        connections = (
            self._connection(self._hybrid_pool)
            if hybrid and self._hybrid_pool is not None
            else self._connection()
        )
        async with connections as connection:
            if hybrid:
                assert self._hybrid_helper is not None
                return await search_hybrid_page(
                    connection,
                    self._hybrid_helper,
                    request,
                    now,
                    self._threshold,
                    relevance=request.sort == "relevance",
                )
            return await read_browse_page(
                connection,
                request,
                now,
                self._threshold,
                expanded_search=True,
                keyword_relevance=request.sort == "relevance",
            )

    async def read_catalogue(self) -> CatalogueView:
        """Read active form choices from Listings tables in one ordered query."""
        async with self._connection() as connection:
            cursor = await connection.execute("""
                SELECT 'category' AS kind, code, label
                FROM listings.categories WHERE active
                UNION ALL
                SELECT 'condition' AS kind, code, label
                FROM listings.conditions WHERE active
                ORDER BY kind, code
                """)
            rows = await cursor.fetchall()
        return CatalogueView(
            categories=[
                Category(code=r["code"], label=r["label"])
                for r in rows
                if r["kind"] == "category"
            ],
            conditions=[
                Category(code=r["code"], label=r["label"])
                for r in rows
                if r["kind"] == "condition"
            ],
        )

    async def create_image_upload(
        self,
        owner_id: UserId,
        request: ImageUploadRequest,
        upload_id: ImageId,
        object_key: str,
        now: datetime,
    ) -> PendingImageUpload:
        """Create or replay one immutable owner-scoped upload intent."""
        async with self._connection() as connection:
            async with connection.transaction():
                await connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                    (str(owner_id), str(request.operation_id)),
                )
                cursor = await connection.execute(
                    """
                    SELECT id, owner_id, object_key, operation_id,
                        requested_media_type, requested_size_bytes, state,
                        created_at, expires_at, confirmed_media_type,
                        confirmed_size_bytes
                    FROM listings.image_uploads
                    WHERE owner_id = %s AND operation_id = %s
                    FOR UPDATE
                    """,
                    (owner_id, request.operation_id),
                )
                row = await cursor.fetchone()
                if row is not None:
                    intent = self._image_upload(row)
                    if (
                        intent.requested_media_type != request.media_type
                        or intent.requested_size_bytes != request.size_bytes
                    ):
                        raise _conflict()
                    return intent

                expires_at = now + timedelta(hours=24)
                cursor = await connection.execute(
                    """
                    INSERT INTO listings.image_uploads (
                        id, owner_id, object_key, operation_id,
                        requested_media_type, requested_size_bytes, state,
                        created_at, expires_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s)
                    RETURNING id, owner_id, object_key, operation_id,
                        requested_media_type, requested_size_bytes, state,
                        created_at, expires_at, confirmed_media_type,
                        confirmed_size_bytes
                    """,
                    (
                        upload_id,
                        owner_id,
                        object_key,
                        request.operation_id,
                        request.media_type,
                        request.size_bytes,
                        now,
                        expires_at,
                    ),
                )
                created = await cursor.fetchone()
        if created is None:
            raise PublicError(ERRORS[503])
        return self._image_upload(created)

    async def read_image_upload(
        self, owner_id: UserId, upload_id: ImageId
    ) -> PendingImageUpload | None:
        """Return an upload only to the owner recorded in Listings storage."""
        async with self._connection() as connection:
            cursor = await connection.execute(
                """
                SELECT id, owner_id, object_key, operation_id,
                    requested_media_type, requested_size_bytes, state,
                    created_at, expires_at, confirmed_media_type,
                    confirmed_size_bytes
                FROM listings.image_uploads
                WHERE id = %s AND owner_id = %s
                """,
                (upload_id, owner_id),
            )
            row = await cursor.fetchone()
        return self._image_upload(row) if row is not None else None

    async def confirm_image_upload(
        self,
        owner_id: UserId,
        upload_id: ImageId,
        media_type: Literal["image/jpeg", "image/png", "image/webp"],
        size_bytes: int,
        now: datetime,
    ) -> ConfirmedImage:
        """Serialize storage confirmation and persist its verified metadata."""
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    SELECT state, expires_at, confirmed_media_type,
                        confirmed_size_bytes, requested_media_type,
                        requested_size_bytes
                    FROM listings.image_uploads
                    WHERE id = %s AND owner_id = %s
                    FOR UPDATE
                    """,
                    (upload_id, owner_id),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise PublicError(ERRORS[404])
                if row["state"] == "confirmed":
                    if (
                        row["confirmed_media_type"] != media_type
                        or row["confirmed_size_bytes"] != size_bytes
                    ):
                        raise _conflict()
                    return ConfirmedImage(
                        upload_id=upload_id,
                        media_type=media_type,
                        size_bytes=size_bytes,
                    )
                if (
                    row["state"] != "pending"
                    or row["expires_at"] <= now
                    or row["requested_media_type"] != media_type
                    or row["requested_size_bytes"] != size_bytes
                ):
                    raise _conflict()
                await connection.execute(
                    """
                    UPDATE listings.image_uploads
                    SET state = 'confirmed', confirmed_at = %s,
                        confirmed_media_type = %s, confirmed_size_bytes = %s,
                        failure_code = NULL
                    WHERE id = %s AND owner_id = %s
                    """,
                    (now, media_type, size_bytes, upload_id, owner_id),
                )
        return ConfirmedImage(
            upload_id=upload_id, media_type=media_type, size_bytes=size_bytes
        )

    async def reject_image_upload(
        self, owner_id: UserId, upload_id: ImageId, now: datetime
    ) -> bool:
        """Record invalid content or expiry without discarding its cleanup key."""
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    SELECT state, expires_at FROM listings.image_uploads
                    WHERE id = %s AND owner_id = %s FOR UPDATE
                    """,
                    (upload_id, owner_id),
                )
                row = await cursor.fetchone()
                if row is None:
                    return False
                if row["state"] in ("failed", "expired"):
                    return True
                if row["state"] != "pending":
                    raise _conflict()
                attached_cursor = await connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM listings.images WHERE upload_id = %s) AS attached",
                    (upload_id,),
                )
                attached = await attached_cursor.fetchone()
                if attached is not None and attached["attached"]:
                    raise _conflict()
                expired = row["expires_at"] <= now
                await connection.execute(
                    """
                    UPDATE listings.image_uploads
                    SET state = %s, confirmed_at = NULL,
                        confirmed_media_type = NULL,
                        confirmed_size_bytes = NULL, failure_code = %s
                    WHERE id = %s AND owner_id = %s AND state = 'pending'
                    """,
                    (
                        "expired" if expired else "failed",
                        "upload_expired" if expired else "invalid_content",
                        upload_id,
                        owner_id,
                    ),
                )
        return True

    async def cancel_image_upload(
        self, owner_id: UserId, upload_id: ImageId, now: datetime
    ) -> bool:
        """Mark an unattached intent failed and preserve its key for cleanup retry."""
        del now  # Keep the original intent deadline unchanged for audit/recovery.
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    SELECT state FROM listings.image_uploads
                    WHERE id = %s AND owner_id = %s FOR UPDATE
                    """,
                    (upload_id, owner_id),
                )
                row = await cursor.fetchone()
                if row is None:
                    return False
                cursor = await connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM listings.images WHERE upload_id = %s) AS attached",
                    (upload_id,),
                )
                attached = await cursor.fetchone()
                if attached is not None and attached["attached"]:
                    raise _conflict()
                if row["state"] not in ("failed", "expired"):
                    await connection.execute(
                        """
                        UPDATE listings.image_uploads
                        SET state = 'failed', confirmed_at = NULL,
                            confirmed_media_type = NULL,
                            confirmed_size_bytes = NULL,
                            failure_code = 'cancelled'
                        WHERE id = %s AND owner_id = %s
                        """,
                        (upload_id, owner_id),
                    )
        return True

    @staticmethod
    def _image_upload(row: dict[str, Any]) -> PendingImageUpload:
        """Translate private upload columns into the service's typed record."""
        return PendingImageUpload(
            upload_id=row["id"],
            owner_id=row["owner_id"],
            object_key=row["object_key"],
            operation_id=row["operation_id"],
            requested_media_type=row["requested_media_type"],
            requested_size_bytes=row["requested_size_bytes"],
            state=row["state"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            confirmed_media_type=row["confirmed_media_type"],
            confirmed_size_bytes=row["confirmed_size_bytes"],
        )

    async def confirmed_images_belong_to(
        self, owner_id: UserId, image_ids: tuple[ImageId, ...]
    ) -> bool:
        """Check owned, unexpired, confirmed, metadata-complete unattached uploads."""
        if not image_ids or len(set(image_ids)) != len(image_ids):
            return False
        async with self._connection() as connection:
            cursor = await connection.execute(
                """
                SELECT count(*) AS matching
                FROM listings.image_uploads AS upload
                WHERE upload.id = ANY(%s)
                    AND upload.owner_id = %s
                    AND upload.state = 'confirmed'
                    AND upload.confirmed_at IS NOT NULL
                    AND upload.expires_at > statement_timestamp()
                    AND upload.confirmed_media_type IS NOT NULL
                    AND upload.confirmed_size_bytes IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM listings.images AS image
                        WHERE image.upload_id = upload.id
                    )
                """,
                (list(image_ids), owner_id),
            )
            row = await cursor.fetchone()
        return row is not None and row["matching"] == len(image_ids)

    async def category_and_condition_are_active(
        self, category_code: CategoryCode, condition_code: str
    ) -> bool:
        """Check both catalogue values without reading another domain's tables."""
        async with self._connection() as connection:
            cursor = await connection.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM listings.categories AS category
                    CROSS JOIN listings.conditions AS listing_condition
                    WHERE category.code = %s AND category.active
                        AND listing_condition.code = %s AND listing_condition.active
                ) AS active
                """,
                (category_code, condition_code),
            )
            row = await cursor.fetchone()
        return row is not None and bool(row["active"])

    async def previous_create_command_result(
        self, owner_id: UserId, request: CreateListingRequest
    ) -> ListingDetail | None:
        """Replay a matching live create result or conflict on reuse/retirement."""
        async with self._connection() as connection:
            return await self._create_result_on_connection(
                connection, owner_id, request
            )

    async def create_listing(
        self,
        owner_id: UserId,
        request: CreateListingRequest,
        normalized_title: str,
        normalized_description: str,
        normalized_pickup_area: str | None,
        now: datetime,
    ) -> ListingDetail:
        """Create listing, attach verified uploads and save its retry receipt atomically."""
        async with self._connection() as connection:
            async with connection.transaction():
                # This transaction lock serializes concurrent retries even when
                # neither request found an earlier receipt in the service check.
                await connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                    (str(owner_id), str(request.operation_id)),
                )
                previous = await self._create_result_on_connection(
                    connection, owner_id, request
                )
                if previous is not None:
                    return previous

                if self._isolated_listing_limit is not None:
                    # Serialize demo creates before counting so concurrent
                    # requests cannot exceed the isolated profile's hard cap.
                    await connection.execute("SELECT pg_advisory_xact_lock(1202, 10)")
                    cursor = await connection.execute(
                        "SELECT count(*) AS listing_count "
                        "FROM listings.sale_listings",
                    )
                    row = await cursor.fetchone()
                    if (
                        row is None
                        or row["listing_count"] >= self._isolated_listing_limit
                    ):
                        raise PublicError(
                            ERRORS[409],
                            (FieldError("listings", "demo_listing_limit_reached"),),
                        )

                category_id = await self._active_category_id(
                    connection, request.category_code
                )
                if category_id is None:
                    raise _field_error(
                        "category_code", "active_category_and_condition_required"
                    )
                if not await self._condition_is_active(
                    connection, request.condition_code
                ):
                    raise _field_error(
                        "condition_code", "active_category_and_condition_required"
                    )
                uploads = await self._lock_confirmed_uploads(
                    connection, owner_id, tuple(request.image_upload_ids), now
                )

                listing_id = uuid4()
                available_from = request.available_from or now
                await connection.execute(
                    """
                    INSERT INTO listings.sale_listings (
                        id, owner_id, title, description, category_id,
                        condition_code, asking_price_paise, negotiable,
                        pickup_area, available_from, available_until,
                        availability, proof_available, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        'available', %s, %s, %s
                    )
                    """,
                    (
                        listing_id,
                        owner_id,
                        normalized_title,
                        normalized_description,
                        category_id,
                        request.condition_code,
                        request.asking_price_paise,
                        request.negotiable,
                        normalized_pickup_area,
                        available_from,
                        request.available_until,
                        request.proof_available,
                        now,
                        now,
                    ),
                )
                await self._attach_uploads(connection, listing_id, uploads)
                view = await self._get_view(connection, listing_id)
                if view is None:
                    raise PublicError(ERRORS[503])
                detail = _public_detail(view)
                await connection.execute(
                    """
                    INSERT INTO listings.create_command_results (
                        owner_id, operation_id, listing_id,
                        request_payload, result_payload
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        owner_id,
                        request.operation_id,
                        listing_id,
                        Jsonb(self._create_request_payload(request)),
                        Jsonb(detail.model_dump(mode="json")),
                    ),
                )
                return detail

    async def read_listing(self, listing_id: ListingId) -> ListingManagementView | None:
        """Read one retained listing and its ordered, non-retired image references."""
        async with self._connection() as connection:
            return await self._get_view(connection, listing_id)

    async def read_image_for_delivery(
        self, image_id: ImageId
    ) -> ListingImageDeliveryTarget | None:
        """Find an attached image through one currently readable listing snapshot."""
        query = f"""
            WITH authorized_listing AS (
                {_VIEW_QUERY}
            )
            SELECT authorized_listing.*, image.object_key
            FROM authorized_listing
            JOIN listings.images AS image
                ON image.listing_id = authorized_listing.listing_id
            WHERE image.id = %s AND image.retired_at IS NULL
        """
        async with self._connection() as connection:
            cursor = await connection.execute(query, (self._threshold, image_id))
            row = await cursor.fetchone()
        if row is None:
            return None
        object_key = row.pop("object_key")
        return ListingImageDeliveryTarget(
            listing=_management_view(row), object_key=object_key
        )

    async def list_owned_listings(
        self, owner_id: UserId, query: PageQuery
    ) -> Page[ListingManagementView]:
        """List all retained owner listings, including ordinary unavailable rows."""
        async with self._connection() as connection:
            cursor = await connection.execute(
                _RETAINED_VIEW_QUERY
                + " AND listing.owner_id = %s"
                + " ORDER BY listing.created_at DESC, listing.id DESC"
                + " LIMIT %s OFFSET %s",
                (
                    self._threshold,
                    owner_id,
                    query.page_size + 1,
                    (query.page - 1) * query.page_size,
                ),
            )
            rows = await cursor.fetchall()
        views = tuple(_management_view(row) for row in rows[: query.page_size])
        return Page(
            items=views,
            page=query.page,
            page_size=query.page_size,
            has_next=len(rows) > query.page_size,
        )

    async def replace_listing(
        self,
        owner_id: UserId,
        listing_id: ListingId,
        request: ListingReplacement,
        normalized_title: str,
        normalized_description: str,
        normalized_pickup_area: str | None,
        now: datetime,
    ) -> ListingManagementView:
        """Replace the full listing and image references under one revision lock."""
        async with self._connection() as connection:
            async with connection.transaction():
                current = await self._get_view(connection, listing_id, for_update=True)
                self._require_owner(current, owner_id)
                assert current is not None
                if current.revision != request.expected_revision:
                    raise _conflict()
                category_id = await self._active_category_id(
                    connection, request.category_code
                )
                if category_id is None:
                    raise _field_error(
                        "category_code", "active_category_and_condition_required"
                    )
                if not await self._condition_is_active(
                    connection, request.condition_code
                ):
                    raise _field_error(
                        "condition_code", "active_category_and_condition_required"
                    )
                current_image_ids = set(current.image_ids)
                requested_existing_ids = {
                    selection.image_id
                    for selection in request.images
                    if isinstance(selection, ExistingListingImage)
                }
                if not requested_existing_ids.issubset(current_image_ids):
                    raise _field_error(
                        "images", "existing_images_must_belong_to_listing"
                    )
                upload_ids = tuple(
                    selection.upload_id
                    for selection in request.images
                    if isinstance(selection, NewListingImage)
                )
                uploads = (
                    await self._lock_confirmed_uploads(
                        connection, owner_id, upload_ids, now, error_field="images"
                    )
                    if upload_ids
                    else []
                )
                uploads_by_id = {upload["id"]: upload for upload in uploads}
                retained_ids = {
                    selection.image_id
                    for selection in request.images
                    if isinstance(selection, ExistingListingImage)
                }
                for image_id in current.image_ids:
                    if image_id not in retained_ids:
                        await connection.execute(
                            """
                            UPDATE listings.images SET retired_at = %s
                            WHERE id = %s AND listing_id = %s AND retired_at IS NULL
                            """,
                            (now, image_id, listing_id),
                        )
                retained_order = [
                    selection.image_id
                    for selection in request.images
                    if isinstance(selection, ExistingListingImage)
                ]
                for temporary_position, image_id in enumerate(
                    retained_order, start=100
                ):
                    await connection.execute(
                        """
                        UPDATE listings.images SET position = %s
                        WHERE id = %s AND listing_id = %s AND retired_at IS NULL
                        """,
                        (temporary_position, image_id, listing_id),
                    )
                cursor = await connection.execute(
                    """
                    UPDATE listings.sale_listings
                    SET title = %s, description = %s, category_id = %s,
                        condition_code = %s, asking_price_paise = %s,
                        negotiable = %s, pickup_area = %s,
                        available_from = %s, available_until = %s,
                        proof_available = %s, updated_at = %s,
                        revision = revision + 1
                    WHERE id = %s AND owner_id = %s AND revision = %s
                    """,
                    (
                        normalized_title,
                        normalized_description,
                        category_id,
                        request.condition_code,
                        request.asking_price_paise,
                        request.negotiable,
                        normalized_pickup_area,
                        request.available_from,
                        request.available_until,
                        request.proof_available,
                        now,
                        listing_id,
                        owner_id,
                        request.expected_revision,
                    ),
                )
                if cursor.rowcount != 1:
                    raise _conflict()
                for position, selection in enumerate(request.images):
                    if isinstance(selection, ExistingListingImage):
                        image_cursor = await connection.execute(
                            """
                            UPDATE listings.images SET position = %s
                            WHERE id = %s AND listing_id = %s AND retired_at IS NULL
                            """,
                            (position, selection.image_id, listing_id),
                        )
                        if image_cursor.rowcount != 1:
                            raise _field_error(
                                "images", "existing_images_must_belong_to_listing"
                            )
                    else:
                        await self._attach_uploads(
                            connection,
                            listing_id,
                            [uploads_by_id[selection.upload_id]],
                            position_offset=position,
                        )
                result = await self._get_view(connection, listing_id)
                if result is None:
                    raise PublicError(ERRORS[503])
                return result

    async def previous_owner_command_result(
        self,
        owner_id: UserId,
        listing_id: ListingId,
        command_kind: Literal["availability", "selection"],
        request: AvailabilityChange | SelectionChange,
    ) -> ListingManagementView | None:
        """Replay the saved owner response before a stale-revision check."""
        async with self._connection() as connection:
            return await self._owner_result_on_connection(
                connection, owner_id, listing_id, command_kind, request
            )

    async def change_availability(
        self,
        owner_id: UserId,
        listing_id: ListingId,
        request: AvailabilityChange,
        now: datetime,
    ) -> ListingManagementView:
        """Change availability/window and save its exact retry result atomically."""
        async with self._connection() as connection:
            async with connection.transaction():
                current = await self._get_view(connection, listing_id, for_update=True)
                self._require_owner(current, owner_id)
                assert current is not None
                prior = await self._owner_result_on_connection(
                    connection, owner_id, listing_id, "availability", request
                )
                if prior is not None:
                    return prior
                if current.revision != request.expected_revision:
                    raise _conflict()
                available_from = request.available_from or current.available_from
                if (
                    request.available_until is not None
                    and request.available_until <= available_from
                ):
                    raise _field_error(
                        "available_until", "must_be_after_available_from"
                    )
                cursor = await connection.execute(
                    """
                    UPDATE listings.sale_listings
                    SET availability = %s, available_from = %s,
                        available_until = %s, updated_at = %s,
                        revision = revision + 1
                    WHERE id = %s AND owner_id = %s AND revision = %s
                    """,
                    (
                        request.availability,
                        available_from,
                        request.available_until,
                        now,
                        listing_id,
                        owner_id,
                        request.expected_revision,
                    ),
                )
                if cursor.rowcount != 1:
                    raise _conflict()
                result = await self._get_view(connection, listing_id)
                if result is None:
                    raise PublicError(ERRORS[503])
                await self._save_owner_result(
                    connection,
                    listing_id,
                    "availability",
                    request,
                    result,
                )
                return result

    async def set_selected_buyer(
        self,
        owner_id: UserId,
        listing_id: ListingId,
        request: SelectionChange,
        now: datetime,
    ) -> ListingManagementView:
        """Set/clear selection atomically with its availability effect.

        Setting requires a currently available/in-window listing and marks it
        unavailable in the same revision-guarded transaction. Clearing leaves
        availability unchanged. Both forms preserve the existing time window.
        """
        async with self._connection() as connection:
            async with connection.transaction():
                current = await self._get_view(connection, listing_id, for_update=True)
                self._require_owner(current, owner_id)
                assert current is not None
                prior = await self._owner_result_on_connection(
                    connection, owner_id, listing_id, "selection", request
                )
                if prior is not None:
                    return prior
                if current.revision != request.expected_revision:
                    raise _conflict()
                if (request.buyer_id is None) != (request.conversation_id is None):
                    raise _field_error(
                        "buyer_id", "buyer_and_conversation_must_both_be_set_or_cleared"
                    )
                if request.buyer_id is not None and (
                    current.availability != "available"
                    or current.available_from > now
                    or (
                        current.available_until is not None
                        and current.available_until <= now
                    )
                ):
                    raise _conflict()
                if request.buyer_id is None:
                    cursor = await connection.execute(
                        """
                        UPDATE listings.sale_listings
                        SET selected_buyer_id = NULL, selected_conversation_id = NULL,
                            updated_at = %s, revision = revision + 1
                        WHERE id = %s AND owner_id = %s AND revision = %s
                        """,
                        (now, listing_id, owner_id, request.expected_revision),
                    )
                else:
                    # The local origin trigger validates a changed selection
                    # while the listing is available. Stage that field update
                    # inside this transaction, then close the listing before
                    # commit. Other transactions can observe neither half.
                    cursor = await connection.execute(
                        """
                        UPDATE listings.sale_listings
                        SET selected_buyer_id = %s, selected_conversation_id = %s
                        WHERE id = %s AND owner_id = %s AND revision = %s
                        """,
                        (
                            request.buyer_id,
                            request.conversation_id,
                            listing_id,
                            owner_id,
                            request.expected_revision,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise _conflict()
                    cursor = await connection.execute(
                        """
                        UPDATE listings.sale_listings
                        SET availability = 'unavailable', updated_at = %s,
                            revision = revision + 1
                        WHERE id = %s AND owner_id = %s AND revision = %s
                        """,
                        (now, listing_id, owner_id, request.expected_revision),
                    )
                if cursor.rowcount != 1:
                    raise _conflict()
                result = await self._get_view(connection, listing_id)
                if result is None:
                    raise PublicError(ERRORS[503])
                await self._save_owner_result(
                    connection, listing_id, "selection", request, result
                )
                return result

    @asynccontextmanager
    async def listing_offer_guard(
        self, listing_id: ListingId
    ) -> AsyncIterator[ListingManagementView | None]:
        """Serialize offers with owner changes without blocking thread FK checks.

        Conversations updates its thread activity in a separate transaction;
        PostgreSQL may recheck that thread's listing FK during the write. NO KEY
        UPDATE excludes concurrent owner mutations while permitting FK key-share,
        just like the listing-conversation guard. No key is changed here.
        """
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    _VIEW_QUERY + " AND listing.id=%s FOR NO KEY UPDATE OF listing",
                    (self._threshold, listing_id),
                )
                row = await cursor.fetchone()
                yield _management_view(row) if row is not None else None

    @asynccontextmanager
    async def listing_conversation_guard(
        self, listing_id: ListingId
    ) -> AsyncIterator[ListingManagementView | None]:
        """Serialize state without blocking the remote thread's FK key-share.

        FOR UPDATE would deadlock creation's independent transaction: the
        thread FK must key-share this row. NO KEY UPDATE still serializes
        availability, edits and retirement while permitting that FK check.
        """
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    _VIEW_QUERY + " AND listing.id=%s FOR NO KEY UPDATE OF listing",
                    (self._threshold, listing_id),
                )
                row = await cursor.fetchone()
                yield _management_view(row) if row is not None else None

    async def clear_listing_retirement_pending(
        self, listing_id: ListingId, operation_id: UUID
    ) -> None:
        """Clear the paired request only after Conversations confirms it was blocked."""
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    UPDATE listings.sale_listings
                    SET retirement_pending_operation_id = NULL,
                        retirement_pending_cutoff_utc = NULL
                    WHERE id = %s AND retirement_pending_operation_id = %s
                    """,
                    (listing_id, operation_id),
                )
                if cursor.rowcount != 1:
                    raise PublicError(ERRORS[503])

    async def begin_listing_retirement(
        self, listing_id: ListingId, operation_id: UUID, now: datetime
    ) -> PendingListingRetirement | None:
        """Commit one stable operation/cutoff after checking local eligibility."""
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    SELECT availability, available_until, created_at,
                        retirement_eligible_since, retired_at,
                        retirement_pending_operation_id,
                        retirement_pending_cutoff_utc
                    FROM listings.sale_listings
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (listing_id,),
                )
                current = await cursor.fetchone()
                if current is None or current["retired_at"] is not None:
                    return None

                pending_id = current["retirement_pending_operation_id"]
                pending_cutoff = current["retirement_pending_cutoff_utc"]
                if pending_id is not None:
                    if pending_id != operation_id or pending_cutoff is None:
                        raise _conflict()
                    return PendingListingRetirement(pending_id, pending_cutoff)

                available_until = current["available_until"]
                expired_window = available_until is not None and available_until <= now
                unavailable = current["availability"] == "unavailable" or expired_window
                eligible_since = current["retirement_eligible_since"]
                if eligible_since is None and expired_window:
                    eligible_since = max(available_until, current["created_at"])
                if (
                    not unavailable
                    or eligible_since is None
                    or eligible_since > now - timedelta(hours=4320)
                ):
                    return None

                cutoff_utc = now - timedelta(hours=2160)
                cursor = await connection.execute(
                    """
                    UPDATE listings.sale_listings
                    SET retirement_pending_operation_id = %s,
                        retirement_pending_cutoff_utc = %s
                    WHERE id = %s AND retirement_pending_operation_id IS NULL
                    """,
                    (operation_id, cutoff_utc, listing_id),
                )
                if cursor.rowcount != 1:
                    raise _conflict()
                return PendingListingRetirement(operation_id, cutoff_utc)

    async def finalize_listing_retirement(
        self, listing_id: ListingId, pending: PendingListingRetirement, now: datetime
    ) -> None:
        """Scrub a marked listing and queue image objects atomically."""
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    SELECT retired_at, retirement_pending_operation_id,
                        retirement_pending_cutoff_utc
                    FROM listings.sale_listings
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (listing_id,),
                )
                current = await cursor.fetchone()
                if current is None:
                    raise PublicError(ERRORS[404])
                if current["retired_at"] is not None:
                    return
                if (
                    current["retirement_pending_operation_id"] != pending.operation_id
                    or current["retirement_pending_cutoff_utc"] != pending.cutoff_utc
                ):
                    raise _conflict()

                await connection.execute(
                    """
                    UPDATE listings.images
                    SET retired_at = %s
                    WHERE listing_id = %s AND retired_at IS NULL
                    """,
                    (now, listing_id),
                )
                await connection.execute(
                    """
                    UPDATE listings.sale_listings
                    SET title = NULL, description = NULL, category_id = NULL,
                        condition_code = NULL, asking_price_paise = NULL,
                        negotiable = NULL, pickup_area = NULL,
                        available_until = NULL, availability = 'unavailable',
                        proof_available = NULL, selected_buyer_id = NULL,
                        selected_conversation_id = NULL,
                        retirement_eligible_since = NULL, retired_at = %s,
                        retirement_pending_operation_id = NULL,
                        retirement_pending_cutoff_utc = NULL,
                        updated_at = %s
                    WHERE id = %s AND retired_at IS NULL
                    """,
                    (now, now, listing_id),
                )

    async def list_retired_images_for_cleanup(
        self, limit: int
    ) -> tuple[RetiredListingImage, ...]:
        """Read due retired images first, preserving failed work for retry."""
        async with self._connection() as connection:
            cursor = await connection.execute(
                """
                SELECT image.id, image.object_key,
                    upload.object_key AS upload_object_key,
                    listing.owner_id AS listing_owner_id,
                    upload.owner_id AS upload_owner_id
                FROM listings.images AS image
                JOIN listings.image_uploads AS upload ON upload.id = image.upload_id
                JOIN listings.sale_listings AS listing ON listing.id = image.listing_id
                WHERE image.retired_at IS NOT NULL
                    AND (image.cleanup_retry_after IS NULL
                        OR image.cleanup_retry_after <= statement_timestamp())
                ORDER BY image.retired_at, image.id
                LIMIT %s
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
        if any(
            row["object_key"] != row["upload_object_key"]
            or row["listing_owner_id"] != row["upload_owner_id"]
            for row in rows
        ):
            raise PublicError(ERRORS[503])
        return tuple(
            RetiredListingImage(image_id=row["id"], object_key=row["object_key"])
            for row in rows
        )

    async def defer_retired_image_cleanup(
        self, image_id: ImageId, object_key: str
    ) -> None:
        """Set a five-minute cooldown after an unknown or failed S3 delete."""
        async with self._connection() as connection:
            await connection.execute(
                """
                UPDATE listings.images AS image
                SET cleanup_retry_after = statement_timestamp() + INTERVAL '5 minutes'
                WHERE image.id = %s AND image.object_key = %s
                    AND image.retired_at IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM listings.image_uploads AS upload
                        JOIN listings.sale_listings AS listing
                            ON listing.id = image.listing_id
                        WHERE upload.id = image.upload_id
                            AND upload.object_key = image.object_key
                            AND upload.owner_id = listing.owner_id
                    )
                """,
                (image_id, object_key),
            )

    async def list_abandoned_uploads_for_cleanup(
        self, limit: int
    ) -> tuple[AbandonedImageUpload, ...]:
        """Expire then claim due unlinked uploads without racing confirmation."""
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    SELECT upload.id, upload.object_key, upload.state
                    FROM listings.image_uploads AS upload
                    WHERE upload.expires_at <= statement_timestamp()
                            - INTERVAL '5 minutes'
                        AND (upload.cleanup_retry_after IS NULL
                            OR upload.cleanup_retry_after <= statement_timestamp())
                        AND upload.state IN ('pending', 'confirmed', 'failed', 'expired')
                        AND NOT EXISTS (
                            SELECT 1 FROM listings.images AS image
                            WHERE image.upload_id = upload.id
                        )
                    ORDER BY upload.expires_at, upload.id
                    LIMIT %s
                    FOR UPDATE OF upload SKIP LOCKED
                    """,
                    (limit,),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    if row["state"] not in ("pending", "confirmed"):
                        continue
                    reason = (
                        "upload_expired"
                        if row["state"] == "pending"
                        else "unattached_upload_expired"
                    )
                    await connection.execute(
                        """
                        UPDATE listings.image_uploads AS upload
                        SET state = 'expired', confirmed_at = NULL,
                            confirmed_media_type = NULL,
                            confirmed_size_bytes = NULL,
                            failure_code = %s
                        WHERE upload.id = %s AND upload.object_key = %s
                            AND upload.state = %s
                            AND NOT EXISTS (
                                SELECT 1 FROM listings.images AS image
                                WHERE image.upload_id = upload.id
                            )
                        """,
                        (reason, row["id"], row["object_key"], row["state"]),
                    )
        return tuple(
            AbandonedImageUpload(upload_id=row["id"], object_key=row["object_key"])
            for row in rows
        )

    async def defer_abandoned_upload_cleanup(
        self, upload_id: ImageId, object_key: str
    ) -> None:
        """Set a five-minute cooldown while retaining the unlinked upload row."""
        async with self._connection() as connection:
            await connection.execute(
                """
                UPDATE listings.image_uploads AS upload
                SET cleanup_retry_after = statement_timestamp() + INTERVAL '5 minutes'
                WHERE upload.id = %s AND upload.object_key = %s
                    AND upload.state IN ('failed', 'expired')
                    AND upload.expires_at <= statement_timestamp()
                            - INTERVAL '5 minutes'
                    AND NOT EXISTS (
                        SELECT 1 FROM listings.images AS image
                        WHERE image.upload_id = upload.id
                    )
                """,
                (upload_id, object_key),
            )

    async def finish_abandoned_upload_cleanup(
        self, upload_id: ImageId, object_key: str
    ) -> None:
        """Remove only a due, terminal, unattached upload after S3 confirms absence."""
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    SELECT state, object_key,
                        expires_at <= statement_timestamp() - INTERVAL '5 minutes'
                            AS grace_elapsed
                    FROM listings.image_uploads
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (upload_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return
                attached_cursor = await connection.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM listings.images WHERE upload_id = %s
                    ) AS attached
                    """,
                    (upload_id,),
                )
                attached = await attached_cursor.fetchone()
                if (
                    row["object_key"] != object_key
                    or row["state"] not in ("failed", "expired")
                    or not row["grace_elapsed"]
                    or (attached is not None and attached["attached"])
                ):
                    raise PublicError(ERRORS[503])
                await connection.execute(
                    """
                    DELETE FROM listings.image_uploads
                    WHERE id = %s AND object_key = %s
                        AND state IN ('failed', 'expired')
                    """,
                    (upload_id, object_key),
                )

    async def finish_retired_image_cleanup(
        self, image_id: ImageId, object_key: str
    ) -> None:
        """Delete image/upload rows only after storage confirms the key is absent."""
        async with self._connection() as connection:
            async with connection.transaction():
                cursor = await connection.execute(
                    """
                    SELECT image.upload_id, image.object_key,
                        upload.object_key AS upload_object_key,
                        upload.owner_id AS upload_owner_id,
                        listing.owner_id AS listing_owner_id
                    FROM listings.images AS image
                    JOIN listings.image_uploads AS upload ON upload.id = image.upload_id
                    JOIN listings.sale_listings AS listing ON listing.id = image.listing_id
                    WHERE image.id = %s AND image.retired_at IS NOT NULL
                    FOR UPDATE OF image, upload
                    """,
                    (image_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return
                if (
                    row["object_key"] != object_key
                    or row["upload_object_key"] != object_key
                    or row["upload_owner_id"] != row["listing_owner_id"]
                ):
                    raise PublicError(ERRORS[503])
                await connection.execute(
                    "DELETE FROM listings.images WHERE id = %s", (image_id,)
                )
                cursor = await connection.execute(
                    """
                    DELETE FROM listings.image_uploads
                    WHERE id = %s AND object_key = %s
                    """,
                    (row["upload_id"], object_key),
                )
                if cursor.rowcount != 1:
                    raise PublicError(ERRORS[503])

    async def _get_view(
        self,
        connection: AsyncConnection[dict[str, Any]],
        listing_id: ListingId,
        *,
        for_update: bool = False,
    ) -> ListingManagementView | None:
        """Fetch one retained listing, optionally locking its row for a write."""
        query = _VIEW_QUERY + " AND listing.id = %s"
        if for_update:
            query += " FOR UPDATE OF listing"
        cursor = await connection.execute(query, (self._threshold, listing_id))
        row = await cursor.fetchone()
        return _management_view(row) if row is not None else None

    @asynccontextmanager
    async def _connection(
        self,
        pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] | None = None,
    ) -> AsyncIterator[AsyncConnection[dict[str, Any]]]:
        """Map pool/connectivity failures to a safe dependency-unavailable error."""
        try:
            async with (
                self._pool if pool is None else pool
            ).connection() as connection:
                yield connection
        except OperationalError, PoolTimeout, TimeoutError:
            raise PublicError(ERRORS[503]) from None

    async def _create_result_on_connection(
        self,
        connection: AsyncConnection[dict[str, Any]],
        owner_id: UserId,
        request: CreateListingRequest,
    ) -> ListingDetail | None:
        """Read a create receipt; return 409 for changed intent or a tombstone."""
        cursor = await connection.execute(
            """
            SELECT saved.request_payload, saved.result_payload, listing.retired_at,
                listing.retirement_pending_operation_id
            FROM listings.create_command_results AS saved
            JOIN listings.sale_listings AS listing ON listing.id = saved.listing_id
            WHERE saved.owner_id = %s AND saved.operation_id = %s
            FOR SHARE OF listing
            """,
            (owner_id, request.operation_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        if (
            row["retired_at"] is not None
            or row["retirement_pending_operation_id"] is not None
            or row["request_payload"] is None
            or row["result_payload"] is None
            or row["request_payload"] != self._create_request_payload(request)
        ):
            raise _conflict()
        return ListingDetail.model_validate(row["result_payload"])

    async def _owner_result_on_connection(
        self,
        connection: AsyncConnection[dict[str, Any]],
        owner_id: UserId,
        listing_id: ListingId,
        command_kind: Literal["availability", "selection"],
        request: AvailabilityChange | SelectionChange,
    ) -> ListingManagementView | None:
        """Find and compare a saved owner command without exposing another owner's result."""
        cursor = await connection.execute(
            """
            SELECT saved.request_payload, saved.result_payload
            FROM listings.owner_command_results AS saved
            JOIN listings.sale_listings AS listing ON listing.id = saved.listing_id
            WHERE listing.owner_id = %s AND saved.listing_id = %s
                AND saved.command_kind = %s AND saved.operation_id = %s
                AND listing.retirement_pending_operation_id IS NULL
            FOR SHARE OF listing
            """,
            (owner_id, listing_id, command_kind, request.operation_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        payload = request.model_dump(mode="json", exclude={"operation_id"})
        if row["request_payload"] != payload:
            raise _conflict()
        return _management_view(row["result_payload"])

    async def _active_category_id(
        self, connection: AsyncConnection[dict[str, Any]], code: CategoryCode
    ) -> UUID | None:
        """Lock and return an active Listings category within the write transaction."""
        cursor = await connection.execute(
            "SELECT id FROM listings.categories WHERE code = %s AND active FOR SHARE",
            (code,),
        )
        row = await cursor.fetchone()
        return row["id"] if row is not None else None

    async def _condition_is_active(
        self, connection: AsyncConnection[dict[str, Any]], code: str
    ) -> bool:
        """Lock an active Listings condition while the new listing is written."""
        cursor = await connection.execute(
            "SELECT code FROM listings.conditions WHERE code = %s AND active FOR SHARE",
            (code,),
        )
        return await cursor.fetchone() is not None

    async def _lock_confirmed_uploads(
        self,
        connection: AsyncConnection[dict[str, Any]],
        owner_id: UserId,
        image_ids: tuple[ImageId, ...],
        now: datetime,
        error_field: str = "image_upload_ids",
    ) -> list[dict[str, Any]]:
        """Lock confirmed uploads and require verifier-recorded actual object metadata."""
        if not image_ids or len(set(image_ids)) != len(image_ids):
            raise _field_error(error_field, "confirmed_owned_images_required")
        cursor = await connection.execute(
            """
            SELECT upload.id, upload.object_key, upload.state, upload.confirmed_at,
                upload.expires_at, upload.confirmed_media_type,
                upload.confirmed_size_bytes
            FROM listings.image_uploads AS upload
            WHERE upload.id = ANY(%s) AND upload.owner_id = %s
            ORDER BY upload.id
            FOR UPDATE OF upload
            """,
            (list(image_ids), owner_id),
        )
        rows = await cursor.fetchall()
        if len(rows) != len(image_ids):
            raise _field_error("image_upload_ids", "confirmed_owned_images_required")
        for upload in rows:
            if (
                upload["state"] != "confirmed"
                or upload["confirmed_at"] is None
                or upload["expires_at"] <= now
            ):
                raise _field_error(error_field, "confirmed_owned_images_required")
            if (
                upload["confirmed_media_type"] is None
                or upload["confirmed_size_bytes"] is None
            ):
                # Historical confirmed rows may predate verifier metadata. Do
                # not invent facts or publish an image with unknown details.
                raise PublicError(ERRORS[503])
            attached_cursor = await connection.execute(
                "SELECT EXISTS (SELECT 1 FROM listings.images WHERE upload_id = %s) AS attached",
                (upload["id"],),
            )
            attached = await attached_cursor.fetchone()
            if attached is not None and attached["attached"]:
                raise _field_error(error_field, "confirmed_owned_images_required")
        indexed = {upload["id"]: upload for upload in rows}
        return [indexed[image_id] for image_id in image_ids]

    async def _attach_uploads(
        self,
        connection: AsyncConnection[dict[str, Any]],
        listing_id: ListingId,
        uploads: Sequence[dict[str, Any]],
        position_offset: int = 0,
    ) -> None:
        """Create controlled image references from verified upload metadata."""
        for offset, upload in enumerate(uploads):
            position = position_offset + offset
            await connection.execute(
                """
                INSERT INTO listings.images (
                    id, listing_id, upload_id, object_key, position,
                    media_type, size_bytes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    listing_id,
                    upload["id"],
                    upload["object_key"],
                    position,
                    upload["confirmed_media_type"],
                    upload["confirmed_size_bytes"],
                ),
            )

    async def _save_owner_result(
        self,
        connection: AsyncConnection[dict[str, Any]],
        listing_id: ListingId,
        command_kind: Literal["availability", "selection"],
        request: AvailabilityChange | SelectionChange,
        result: ListingManagementView,
    ) -> None:
        """Persist command intent and response in the listing-update transaction."""
        await connection.execute(
            """
            INSERT INTO listings.owner_command_results (
                listing_id, command_kind, operation_id, request_payload, result_payload
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                listing_id,
                command_kind,
                request.operation_id,
                Jsonb(request.model_dump(mode="json", exclude={"operation_id"})),
                Jsonb(result.model_dump(mode="json")),
            ),
        )

    @staticmethod
    def _create_request_payload(request: CreateListingRequest) -> dict[str, Any]:
        """Encode normalized create intent without its idempotency key."""
        return request.model_dump(mode="json", exclude={"operation_id"})

    @staticmethod
    def _require_owner(current: ListingManagementView | None, owner_id: UserId) -> None:
        """Reject missing rows and non-owners before changing a listing."""
        if current is None:
            raise PublicError(ERRORS[404])
        if current.owner_id != owner_id:
            raise PublicError(ERRORS[403])
