"""Conversations-owned offer history and exact retries behind Listings' gate."""

import base64
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import UUID, uuid4

from psycopg import AsyncConnection, Error as PsycopgError
from psycopg.errors import IntegrityError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    AccountClass,
    AccountEligibility,
    CipherEnvelope,
    ListingOfferCommand,
    OfferView,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError
from app.domains.conversations.messages import PostgresMessageOperations
from app.domains.identity.public import check_account_eligibility

EligibilityCheck = Callable[[UUID, AccountClass | None], Awaitable[AccountEligibility]]


class PostgresOfferOperations:
    """Persist one logical buyer offer with append-only revisions.

    Listings owns availability serialization before invoking the write port.
    This service checks only owned thread/member/marker/key state and Identity's
    public eligibility answer. Every mutation and its retry metadata commit with
    the entry and revision in one transaction, taking thread lock before offer.
    """

    def __init__(
        self,
        pool: AsyncConnectionPool,
        eligibility_check: EligibilityCheck = check_account_eligibility,
    ) -> None:
        """Reuse the process pool and an explicitly bound public Identity check."""
        self._pool = pool
        self._offer_eligibility_check = eligibility_check

    @staticmethod
    def _conflict(field: str = "operation_id", code: str = "conflict") -> PublicError:
        """Expose stable field metadata without private request or SQL details."""
        return PublicError(ERRORS[409], (FieldError(field, code),))

    async def _eligible(
        self, user_id: UUID, required_class: AccountClass | None
    ) -> None:
        """Recheck current account state through the real public Identity binding."""
        try:
            result = await self._offer_eligibility_check(user_id, required_class)
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[503]) from None
        if not result.eligible:
            raise PublicError(ERRORS[403])

    @staticmethod
    async def _member(
        connection: AsyncConnection,
        caller: CallerContext,
        conversation_id: UUID,
        *,
        lock: bool = False,
    ) -> tuple[Any, ...]:
        """Resolve only owned membership; absent and nonmember share safe404."""
        row = await (
            await connection.execute(
                "SELECT t.listing_id,t.initiator_id,t.counterparty_id,t.participant_writes_disabled_at "
                "FROM conversations.threads t JOIN conversations.members m "
                "ON m.conversation_id=t.id AND m.user_id=%s WHERE t.id=%s"
                + (" FOR UPDATE OF t" if lock else ""),
                (caller.user_id, conversation_id),
            )
        ).fetchone()
        if row is None:
            raise PublicError(ERRORS[404])
        return row

    @staticmethod
    def _validate(request: ListingOfferCommand) -> None:
        """Reject impossible trusted-command shapes before any database mutation."""
        invalid = (
            request.expected_revision is not None
            and request.expected_revision > 9_223_372_036_854_775_807
        )
        if request.action == "submit":
            invalid |= (
                request.amount_paise is None
                or request.offer_id is not None
                or request.amount_paise > 9_223_372_036_854_775_807
            )
        else:
            invalid |= (
                request.offer_id is None
                or request.expected_revision is None
                or request.amount_paise is not None
                or request.note_envelope is not None
            )
        note = request.note_envelope
        if note is not None:
            invalid |= (
                note.sdk_message_type != "ciphertext"
                or note.recovery_for_entry_id is not None
            )
            invalid |= (
                note.envelope_version == 1
                and note.sdk_client_message_id not in {None, str(request.operation_id)}
            )
        if invalid:
            raise PublicError(ERRORS[422], (FieldError("body", "invalid_offer"),))

    @staticmethod
    def _note(row: tuple[Any, ...]) -> CipherEnvelope | None:
        """Reconstruct only retained opaque note metadata from the ordered entry."""
        if row[15] is None:
            return None
        return CipherEnvelope(
            protocol_id=row[8],
            protocol_version=row[9],
            envelope_version=row[10],
            sdk_message_type=row[11],
            client_timestamp_ms=row[12],
            sender_key_version=row[16],
            recipient_key_version=row[17],
            sdk_client_message_id=row[18],
            payload_base64=base64.b64encode(bytes(row[15])).decode("ascii"),
        )

    @staticmethod
    def _view(revision: tuple[Any, ...], note: CipherEnvelope | None) -> OfferView:
        """Return the historical revision result, never substitute current state."""
        return OfferView(
            offer_id=revision[0],
            revision=revision[1],
            amount_paise=revision[2],
            status=revision[3],
            updated_at=revision[4],
            note_envelope=note,
        )

    @staticmethod
    async def _revision_for_entry(
        connection: AsyncConnection, entry_id: UUID
    ) -> tuple[Any, ...] | None:
        """Read result and original expected-revision metadata together."""
        return await (
            await connection.execute(
                "SELECT offer_id,revision,amount_paise,status,created_at,request_recorded,request_expected_revision "
                "FROM conversations.offer_revisions WHERE entry_id=%s",
                (entry_id,),
            )
        ).fetchone()

    async def persist_listing_offer(
        self, caller: CallerContext, request: ListingOfferCommand
    ) -> OfferView:
        """Append/replay an offer after Listings authorizes its current origin state."""
        caller.require_current()
        self._validate(request)
        note = request.note_envelope
        if note is not None and note.envelope_version == 1:
            note = note.model_copy(
                update={"sdk_client_message_id": str(request.operation_id)}
            )
        try:
            async with self._pool.connection() as connection, connection.transaction():
                await connection.execute("SET LOCAL lock_timeout = '2s'")
                await connection.execute("SET LOCAL statement_timeout = '5s'")
                thread = await self._member(
                    connection, caller, request.conversation_id, lock=True
                )
                if thread[0] != request.listing_id:
                    raise PublicError(ERRORS[404])
                if thread[1] != caller.user_id:
                    raise PublicError(ERRORS[403])
                await self._eligible(caller.user_id, caller.account_class)
                await self._eligible(thread[2], "regular")
                if thread[3] is not None:
                    raise self._conflict("conversation_id", "writes_disabled")
                await connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                    (f"offer:{caller.user_id}:{request.operation_id}",),
                )
                prior = await PostgresMessageOperations._entry_by_operation(
                    connection, caller.user_id, request.operation_id
                )
                if prior is not None:
                    if prior[1] != request.conversation_id or prior[3] != "offer":
                        raise self._conflict()
                    if prior[7] is not None:
                        raise self._conflict("operation_id", "write_expired")
                    revision = await self._revision_for_entry(connection, prior[0])
                    replay_status = (
                        "submitted" if request.action == "submit" else "withdrawn"
                    )
                    if (
                        revision is None
                        or not revision[5]
                        or revision[6] != request.expected_revision
                        or revision[3] != replay_status
                        or self._note(prior) != note
                        or (
                            request.action == "submit"
                            and revision[2] != request.amount_paise
                        )
                        or (
                            request.action == "withdraw"
                            and revision[0] != request.offer_id
                        )
                    ):
                        raise self._conflict()
                    return self._view(revision, note)

                current = await (
                    await connection.execute(
                        "SELECT o.id,o.current_revision,o.next_revision,r.amount_paise,r.status "
                        "FROM conversations.offers o LEFT JOIN conversations.offer_revisions r "
                        "ON r.offer_id=o.id AND r.revision=o.current_revision "
                        "WHERE o.conversation_id=%s AND o.buyer_id=%s FOR UPDATE OF o",
                        (request.conversation_id, caller.user_id),
                    )
                ).fetchone()
                if (current[1] if current else None) != request.expected_revision:
                    raise self._conflict("expected_revision", "stale_revision")
                if request.action == "withdraw":
                    if current is None or current[0] != request.offer_id:
                        raise PublicError(ERRORS[404])
                    if current[1] is None or current[4] != "submitted":
                        raise self._conflict("offer_id", "not_submitted")
                offer_id = current[0] if current else uuid4()
                revision_number = current[2] if current else 1
                amount = (
                    current[3]
                    if current and request.action == "withdraw"
                    else request.amount_paise
                )
                if amount is None:
                    raise self._conflict("amount_paise")
                status: Literal["submitted", "withdrawn"] = (
                    "withdrawn" if request.action == "withdraw" else "submitted"
                )
                entry_id = uuid4()
                entry = await (
                    await connection.execute(
                        "INSERT INTO conversations.entries "
                        "(id,conversation_id,sender_id,client_operation_id,kind,sdk_client_message_id) "
                        "VALUES (%s,%s,%s,%s,'offer',%s) RETURNING created_at",
                        (
                            entry_id,
                            request.conversation_id,
                            caller.user_id,
                            request.operation_id,
                            note.sdk_client_message_id if note else None,
                        ),
                    )
                ).fetchone()
                if entry is None:
                    raise PublicError(ERRORS[503])
                if note is not None:
                    if (
                        note.sender_key_version is None
                        or note.recipient_key_version is None
                    ):
                        raise PublicError(ERRORS[422])
                    sender_key = await PostgresMessageOperations._key_version_id(
                        connection, caller.user_id, note.sender_key_version
                    )
                    recipient_key = await PostgresMessageOperations._key_version_id(
                        connection, thread[2], note.recipient_key_version
                    )
                    await connection.execute(
                        "INSERT INTO conversations.encrypted_payloads "
                        "(entry_id,protocol_id,protocol_version,envelope_version,sdk_message_type,client_timestamp_ms,"
                        "sender_key_version_id,recipient_key_version_id,envelope) VALUES (%s,%s,%s,%s,'ciphertext',%s,%s,%s,%s)",
                        (
                            entry_id,
                            note.protocol_id,
                            note.protocol_version,
                            note.envelope_version,
                            note.client_timestamp_ms,
                            sender_key,
                            recipient_key,
                            PostgresMessageOperations._payload(note),
                        ),
                    )
                if current is None:
                    await connection.execute(
                        "INSERT INTO conversations.offers (id,conversation_id,buyer_id,current_revision,next_revision) "
                        "VALUES (%s,%s,%s,1,2)",
                        (offer_id, request.conversation_id, caller.user_id),
                    )
                else:
                    await connection.execute(
                        "UPDATE conversations.offers SET current_revision=%s,next_revision=%s,history_deleted_at=NULL WHERE id=%s",
                        (revision_number, revision_number + 1, offer_id),
                    )
                await connection.execute(
                    "INSERT INTO conversations.offer_revisions "
                    "(offer_id,revision,entry_id,amount_paise,status,created_at,request_recorded,request_expected_revision) "
                    "VALUES (%s,%s,%s,%s,%s,%s,true,%s)",
                    (
                        offer_id,
                        revision_number,
                        entry_id,
                        amount,
                        status,
                        entry[0],
                        request.expected_revision,
                    ),
                )
                return OfferView(
                    offer_id=offer_id,
                    revision=revision_number,
                    amount_paise=amount,
                    status=status,
                    updated_at=entry[0],
                    note_envelope=note,
                )
        except PublicError:
            raise
        except IntegrityError:
            raise self._conflict("body", "conflict") from None
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None

    async def read_offer(
        self, caller: CallerContext, conversation_id: UUID
    ) -> OfferView | None:
        """Read only a member's current offer; purged/no-offer/Wanted returns null."""
        caller.require_current()
        try:
            async with self._pool.connection() as connection, connection.transaction():
                await self._member(connection, caller, conversation_id)
                await self._eligible(caller.user_id, caller.account_class)
                row = await (
                    await connection.execute(
                        "SELECT r.entry_id,e.sender_id,e.client_operation_id "
                        "FROM conversations.offers o JOIN conversations.offer_revisions r "
                        "ON r.offer_id=o.id AND r.revision=o.current_revision "
                        "JOIN conversations.entries e ON e.id=r.entry_id "
                        "WHERE o.conversation_id=%s AND e.content_deleted_at IS NULL",
                        (conversation_id,),
                    )
                ).fetchone()
                if row is None:
                    return None
                entry = await PostgresMessageOperations._entry_by_operation(
                    connection, row[1], row[2]
                )
                revision = await self._revision_for_entry(connection, row[0])
                if entry is None or revision is None:
                    raise PublicError(ERRORS[503])
                return self._view(revision, self._note(entry))
        except PublicError:
            raise
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None
