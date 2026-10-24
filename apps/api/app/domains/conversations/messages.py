"""Conversations-owned persistence for ordered encrypted entries and read state."""

import base64
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from psycopg import AsyncConnection, Error as PsycopgError
from psycopg.errors import IntegrityError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    CipherEnvelope,
    ConversationEntry,
    EntryPage,
    EntryQuery,
    MessageRequest,
    ReadAcknowledgement,
    ReadState,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError


@dataclass(frozen=True)
class MessageWriteResult:
    """Committed entry plus whether the response is an idempotent replay."""

    entry: ConversationEntry
    replayed: bool


class PostgresMessageOperations:
    """Persist encrypted messages and member-scoped read watermarks.

    The caller is supplied only by the trusted Identity boundary. Every read is
    membership-scoped; every participant write serializes on the Conversations
    thread lock. The server stores opaque SDK bytes, never decrypted content.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        """Retain the process pool; each public operation owns its transaction."""
        self._pool = pool

    @staticmethod
    def _unavailable() -> PublicError:
        """Return a generic dependency error without database diagnostics."""
        return PublicError(ERRORS[503])

    @staticmethod
    def _not_found() -> PublicError:
        """Hide whether an absent private thread exists outside membership."""
        return PublicError(ERRORS[404])

    @staticmethod
    def _conflict(field: str = "operation_id", code: str = "conflict") -> PublicError:
        """Return a stable conflict with only reviewed field metadata."""
        return PublicError(ERRORS[409], (FieldError(field, code),))

    @staticmethod
    def _payload(envelope: CipherEnvelope) -> bytes:
        """Decode only canonical, bounded Base64; never inspect SDK payload bytes."""
        try:
            payload = base64.b64decode(envelope.payload_base64, validate=True)
        except ValueError:
            raise PublicError(
                ERRORS[422], (FieldError("body", "invalid_envelope"),)
            ) from None
        if (
            not 1 <= len(payload) <= 65536
            or base64.b64encode(payload).decode("ascii") != envelope.payload_base64
            or envelope.protocol_id != "open-e2ee-signal"
            or envelope.protocol_version != "13.0.0"
            or envelope.envelope_version not in {1, 2}
        ):
            raise PublicError(ERRORS[422], (FieldError("body", "invalid_envelope"),))
        return payload

    @staticmethod
    def _recovery_identity(envelope: CipherEnvelope) -> tuple[str, UUID, int] | None:
        """Parse an SDK recovery ID into its kind, family UUID and attempt."""
        if envelope.recovery_for_entry_id is None:
            return None
        match = re.fullmatch(
            r"(?P<family>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
            r":(?P<kind>retry-request|resend|null)(?::(?P<attempt>[2-9]|[1-9][0-9]+))?",
            envelope.sdk_client_message_id or "",
        )
        if match is None:
            raise PublicError(ERRORS[422], (FieldError("body", "invalid_recovery_id"),))
        return (
            match.group("kind"),
            UUID(match.group("family")),
            int(match.group("attempt") or "1"),
        )

    @staticmethod
    async def _require_member(
        connection: AsyncConnection[Any], conversation_id: UUID, user_id: UUID
    ) -> tuple[Any, ...]:
        """Return the locked thread for a member; use one safe 404 otherwise."""
        cursor = await connection.execute(
            "SELECT thread.id, thread.initiator_id, thread.counterparty_id, "
            "thread.next_sequence, thread.participant_writes_blocked_at "
            "FROM conversations.threads AS thread "
            "JOIN conversations.members AS member "
            "ON member.conversation_id = thread.id AND member.user_id = %s "
            "WHERE thread.id = %s FOR UPDATE OF thread",
            (user_id, conversation_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise PostgresMessageOperations._not_found()
        return cast(tuple[Any, ...], row)

    @staticmethod
    async def _key_version_id(
        connection: AsyncConnection[Any], user_id: UUID, version: int
    ) -> UUID:
        """Resolve a claimed numeric version to its owning member's stored key."""
        cursor = await connection.execute(
            "SELECT id FROM conversations.public_key_versions "
            "WHERE user_id = %s AND version = %s AND protocol_id = 'open-e2ee-signal'",
            (user_id, version),
        )
        row = await cursor.fetchone()
        if row is None:
            raise PublicError(ERRORS[422], (FieldError("body", "invalid_key_version"),))
        return cast(UUID, row[0])

    @staticmethod
    async def _entry_by_operation(
        connection: AsyncConnection[Any], user_id: UUID, operation_id: UUID
    ) -> tuple[Any, ...] | None:
        """Load a stable retry record without returning content-deleted payloads."""
        cursor = await connection.execute(
            "SELECT entry.id, entry.conversation_id, entry.sequence, entry.kind, "
            "entry.sender_id, entry.recipient_id, entry.created_at, entry.content_deleted_at, "
            "payload.protocol_id, payload.protocol_version, payload.envelope_version, "
            "payload.sdk_message_type, payload.client_timestamp_ms, "
            "payload.sender_key_version_id, payload.recipient_key_version_id, payload.envelope, "
            "sender_key.version, recipient_key.version, entry.sdk_client_message_id, "
            "entry.recovery_for_entry_id, recovery_original.sequence, "
            "recovery_original.sender_id, recovery_original.created_at "
            "FROM conversations.entries AS entry "
            "LEFT JOIN conversations.encrypted_payloads AS payload ON payload.entry_id = entry.id "
            "LEFT JOIN conversations.public_key_versions AS sender_key "
            "ON sender_key.id = payload.sender_key_version_id "
            "LEFT JOIN conversations.public_key_versions AS recipient_key "
            "ON recipient_key.id = payload.recipient_key_version_id "
            "LEFT JOIN conversations.entries AS recovery_original "
            "ON recovery_original.id = entry.recovery_for_entry_id "
            "WHERE entry.sender_id = %s AND entry.client_operation_id = %s",
            (user_id, operation_id),
        )
        return await cursor.fetchone()

    @staticmethod
    def _entry_from_row(row: Sequence[Any]) -> ConversationEntry:
        """Build the reviewed wire envelope without exposing internal routing IDs."""
        (
            entry_id,
            _conversation_id,
            sequence,
            kind,
            sender_id,
            _recipient_id,
            created_at,
            content_deleted_at,
            protocol_id,
            protocol_version,
            envelope_version,
            sdk_message_type,
            client_timestamp_ms,
            _sender_key_id,
            _recipient_key_id,
            payload,
            sender_key_version,
            recipient_key_version,
            sdk_client_message_id,
            recovery_for_entry_id,
            recovery_sequence,
            recovery_sender_id,
            recovery_created_at,
        ) = row
        envelope = None
        if payload is not None and content_deleted_at is None:
            envelope = CipherEnvelope(
                protocol_id=protocol_id,
                protocol_version=protocol_version,
                envelope_version=envelope_version,
                sdk_message_type=sdk_message_type,
                client_timestamp_ms=client_timestamp_ms,
                sdk_client_message_id=sdk_client_message_id,
                recovery_for_entry_id=recovery_for_entry_id,
                sender_key_version=sender_key_version,
                recipient_key_version=recipient_key_version,
                payload_base64=base64.b64encode(bytes(payload)).decode("ascii"),
            )
        return ConversationEntry(
            entry_id=entry_id,
            sequence=sequence,
            kind=kind,
            sender_user_id=sender_id,
            created_at=created_at,
            envelope=envelope,
            recovery_target=(
                {
                    "entry_id": recovery_for_entry_id,
                    "sequence": recovery_sequence,
                    "sender_user_id": recovery_sender_id,
                    "created_at": recovery_created_at,
                }
                if (
                    payload is not None
                    and content_deleted_at is None
                    and recovery_for_entry_id is not None
                    and recovery_created_at is not None
                )
                else None
            ),
            content_deleted=content_deleted_at is not None,
        )

    async def submit_message(
        self,
        caller: CallerContext,
        conversation_id: UUID,
        request: MessageRequest,
    ) -> MessageWriteResult:
        """Write one opaque entry atomically and replay only exact live retries."""
        caller.require_current()
        payload = self._payload(request.envelope)
        recovery = self._recovery_identity(request.envelope)
        recovery_kind = recovery[0] if recovery is not None else None
        recovery_family_id = recovery[1] if recovery is not None else None
        recovery_attempt = recovery[2] if recovery is not None else None
        kind = (
            "protocol_control"
            if recovery is not None
            or request.envelope.sdk_message_type == "retry_request"
            else "message"
        )
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    thread = await self._require_member(
                        connection, conversation_id, caller.user_id
                    )
                    _, initiator_id, counterparty_id, next_sequence, blocked_at = thread
                    other_member = (
                        counterparty_id
                        if caller.user_id == initiator_id
                        else initiator_id
                    )
                    await connection.execute(
                        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                        (f"message:{caller.user_id}:{request.operation_id}",),
                    )
                    prior = await self._entry_by_operation(
                        connection, caller.user_id, request.operation_id
                    )
                    expected_recipient = (
                        other_member if kind == "protocol_control" else None
                    )
                    sdk_client_message_id = (
                        request.envelope.sdk_client_message_id
                        if request.envelope.envelope_version == 2
                        else str(request.operation_id)
                    )
                    if prior is not None:
                        same_request = (
                            prior[1] == conversation_id
                            and prior[3] == kind
                            and prior[5] == expected_recipient
                            and prior[7] is None
                            and prior[8] == request.envelope.protocol_id
                            and prior[9] == request.envelope.protocol_version
                            and prior[10] == request.envelope.envelope_version
                            and prior[11] == request.envelope.sdk_message_type
                            and prior[12] == request.envelope.client_timestamp_ms
                            and prior[16] == request.envelope.sender_key_version
                            and prior[17] == request.envelope.recipient_key_version
                            and bytes(prior[15]) == payload
                            and prior[18] == sdk_client_message_id
                            and prior[19] == request.envelope.recovery_for_entry_id
                        )
                        if not same_request:
                            raise self._conflict()
                        return MessageWriteResult(self._entry_from_row(prior), True)

                    recovery_requester_id = None
                    new_entry_id = uuid4()
                    if recovery is not None:
                        cursor = await connection.execute(
                            "SELECT original.id, original.sequence, original.sender_id, "
                            "original.created_at, original.content_deleted_at, original.kind, "
                            "original.conversation_id FROM conversations.entries AS original "
                            "WHERE original.id = %s",
                            (request.envelope.recovery_for_entry_id,),
                        )
                        original = await cursor.fetchone()
                        if (
                            original is None
                            or original[6] != conversation_id
                            or original[5] != "message"
                            or original[4] is not None
                        ):
                            raise self._conflict(
                                "recovery_for_entry_id", "invalid_target"
                            )
                        original_sender_id = original[2]
                        recovery_requester_id = (
                            caller.user_id
                            if recovery_kind == "retry-request"
                            else other_member
                        )
                        if recovery_kind == "retry-request":
                            if original_sender_id != other_member:
                                raise self._conflict(
                                    "recovery_for_entry_id", "invalid_target"
                                )
                            if recovery_attempt == 1:
                                await connection.execute(
                                    "INSERT INTO conversations.recovery_families "
                                    "(requester_id, family_id, conversation_id, original_entry_id, first_request_entry_id) "
                                    "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                                    (
                                        recovery_requester_id,
                                        recovery_family_id,
                                        conversation_id,
                                        request.envelope.recovery_for_entry_id,
                                        new_entry_id,
                                    ),
                                )
                        else:
                            if caller.user_id != original_sender_id:
                                raise self._conflict(
                                    "recovery_for_entry_id", "wrong_sender"
                                )
                            cursor = await connection.execute(
                                "SELECT conversation_id, original_entry_id FROM conversations.recovery_families "
                                "WHERE requester_id = %s AND family_id = %s",
                                (recovery_requester_id, recovery_family_id),
                            )
                            family = await cursor.fetchone()
                            if family != (
                                conversation_id,
                                request.envelope.recovery_for_entry_id,
                            ):
                                raise self._conflict(
                                    "recovery_for_entry_id", "unknown_recovery"
                                )

                    sender_key_id = None
                    recipient_key_id = None
                    if (
                        recovery_kind not in {"retry-request", "null"}
                        and request.envelope.sdk_message_type != "retry_request"
                    ):
                        sender_version = request.envelope.sender_key_version
                        recipient_version = request.envelope.recipient_key_version
                        if sender_version is None or recipient_version is None:
                            raise PublicError(
                                ERRORS[422],
                                (FieldError("body", "invalid_key_version"),),
                            )
                        sender_key_id = await self._key_version_id(
                            connection,
                            caller.user_id,
                            sender_version,
                        )
                        recipient_key_id = await self._key_version_id(
                            connection,
                            other_member,
                            recipient_version,
                        )

                    if blocked_at is not None:
                        raise self._conflict("conversation_id", "writes_disabled")

                    recipient_id = other_member if kind == "protocol_control" else None
                    cursor = await connection.execute(
                        "INSERT INTO conversations.entries "
                        "(id, conversation_id, sequence, sender_id, client_operation_id, kind, recipient_id, "
                        "sdk_client_message_id, recovery_for_entry_id, recovery_requester_id, "
                        "recovery_family_id, recovery_attempt, recovery_kind) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                        "RETURNING id",
                        (
                            new_entry_id,
                            conversation_id,
                            next_sequence,
                            caller.user_id,
                            request.operation_id,
                            kind,
                            recipient_id,
                            sdk_client_message_id,
                            request.envelope.recovery_for_entry_id,
                            recovery_requester_id,
                            recovery_family_id,
                            recovery_attempt,
                            recovery_kind,
                        ),
                    )
                    if await cursor.fetchone() is None:
                        raise self._unavailable()
                    await connection.execute(
                        "INSERT INTO conversations.encrypted_payloads "
                        "(entry_id, protocol_id, protocol_version, envelope_version, sdk_message_type, "
                        "client_timestamp_ms, sender_key_version_id, recipient_key_version_id, envelope) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            new_entry_id,
                            request.envelope.protocol_id,
                            request.envelope.protocol_version,
                            request.envelope.envelope_version,
                            request.envelope.sdk_message_type,
                            request.envelope.client_timestamp_ms,
                            sender_key_id,
                            recipient_key_id,
                            payload,
                        ),
                    )
                    if kind == "message":
                        await self._upsert_unread_intent(
                            connection,
                            conversation_id,
                            caller.user_id,
                            other_member,
                            next_sequence,
                        )
                    saved = await self._entry_by_operation(
                        connection, caller.user_id, request.operation_id
                    )
                    if saved is None:
                        raise self._unavailable()
                    return MessageWriteResult(self._entry_from_row(saved), False)
        except PublicError:
            raise
        except IntegrityError:
            raise self._conflict("operation_id", "recovery_conflict") from None
        except PsycopgError, PoolTimeout:
            raise self._unavailable() from None

    @staticmethod
    async def _upsert_unread_intent(
        connection: AsyncConnection[Any],
        conversation_id: UUID,
        sender_id: UUID,
        recipient_id: UUID,
        sequence: int,
    ) -> None:
        """Coalesce a text message into its recipient's current unread episode."""
        cursor = await connection.execute(
            "SELECT reminder_episode_start_sequence, reminder_sent_at, last_read_sequence "
            "FROM conversations.members WHERE conversation_id = %s AND user_id = %s FOR UPDATE",
            (conversation_id, recipient_id),
        )
        member = await cursor.fetchone()
        if member is None:
            raise PostgresMessageOperations._unavailable()
        episode_start, reminder_sent_at, last_read_sequence = member
        if (
            episode_start is None
            or reminder_sent_at is not None
            or last_read_sequence >= sequence
        ):
            return
        cursor = await connection.execute(
            "SELECT id, created_at FROM conversations.entries "
            "WHERE conversation_id = %s AND sequence = %s AND sender_id = %s AND kind = 'message'",
            (conversation_id, episode_start, sender_id),
        )
        first_message = await cursor.fetchone()
        if first_message is None:
            raise PostgresMessageOperations._unavailable()
        first_entry_id, first_created_at = first_message
        due_at = first_created_at + timedelta(minutes=15)
        expires_at = due_at + timedelta(hours=24)
        cursor = await connection.execute("SELECT clock_timestamp()")
        clock_row = await cursor.fetchone()
        if clock_row is None:
            raise PostgresMessageOperations._unavailable()
        now = clock_row[0]
        if expires_at <= now:
            return
        key = f"unread_reminder:{conversation_id}:{recipient_id}:{episode_start}"
        await connection.execute(
            "INSERT INTO conversations.notification_intents "
            "(id, conversation_id, recipient_id, trigger_entry_id, event_kind, "
            "deduplication_key, due_at, expires_at, unread_episode_start_sequence, "
            "unread_through_sequence) "
            "VALUES (%s, %s, %s, %s, 'unread_reminder', %s, %s, %s, %s, %s) "
            "ON CONFLICT (deduplication_key) DO UPDATE SET "
            "unread_through_sequence = EXCLUDED.unread_through_sequence, updated_at = clock_timestamp() "
            "WHERE conversations.notification_intents.state = 'pending' "
            "AND conversations.notification_intents.unread_through_sequence < EXCLUDED.unread_through_sequence",
            (
                uuid4(),
                conversation_id,
                recipient_id,
                first_entry_id,
                key,
                due_at,
                expires_at,
                episode_start,
                sequence,
            ),
        )

    async def read_entries(
        self,
        caller: CallerContext,
        conversation_id: UUID,
        query: EntryQuery,
    ) -> EntryPage:
        """Return a bounded visible page and advance through inspected private controls."""
        caller.require_current()
        scan_limit = query.page_size + 1
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    cursor = await connection.execute(
                        "SELECT 1 FROM conversations.members "
                        "WHERE conversation_id = %s AND user_id = %s",
                        (conversation_id, caller.user_id),
                    )
                    if await cursor.fetchone() is None:
                        raise self._not_found()
                    cursor = await connection.execute(
                        "SELECT entry.id, entry.conversation_id, entry.sequence, entry.kind, "
                        "entry.sender_id, entry.recipient_id, entry.created_at, entry.content_deleted_at, "
                        "payload.protocol_id, payload.protocol_version, payload.envelope_version, "
                        "payload.sdk_message_type, payload.client_timestamp_ms, "
                        "payload.sender_key_version_id, payload.recipient_key_version_id, payload.envelope, "
                        "sender_key.version, recipient_key.version, entry.sdk_client_message_id, "
                        "entry.recovery_for_entry_id, recovery_original.sequence, "
                        "recovery_original.sender_id, recovery_original.created_at "
                        "FROM conversations.entries AS entry "
                        "LEFT JOIN conversations.encrypted_payloads AS payload ON payload.entry_id = entry.id "
                        "LEFT JOIN conversations.public_key_versions AS sender_key "
                        "ON sender_key.id = payload.sender_key_version_id "
                        "LEFT JOIN conversations.public_key_versions AS recipient_key "
                        "ON recipient_key.id = payload.recipient_key_version_id "
                        "LEFT JOIN conversations.entries AS recovery_original "
                        "ON recovery_original.id = entry.recovery_for_entry_id "
                        "WHERE entry.conversation_id = %s AND entry.sequence > %s "
                        "ORDER BY entry.sequence LIMIT %s",
                        (conversation_id, query.after_sequence, scan_limit),
                    )
                    scanned = await cursor.fetchall()
                    visible = [
                        row
                        for row in scanned
                        if row[3] != "protocol_control" or row[5] == caller.user_id
                    ]
                    has_extra_visible = len(visible) > query.page_size
                    returned = visible[: query.page_size]
                    if has_extra_visible:
                        scanned_through = returned[-1][2]
                        has_more = True
                    elif scanned:
                        scanned_through = scanned[-1][2]
                        cursor = await connection.execute(
                            "SELECT EXISTS (SELECT 1 FROM conversations.entries "
                            "WHERE conversation_id = %s AND sequence > %s)",
                            (conversation_id, scanned_through),
                        )
                        has_more_row = await cursor.fetchone()
                        if has_more_row is None:
                            raise self._unavailable()
                        has_more = has_more_row[0]
                    else:
                        scanned_through = query.after_sequence
                        has_more = False
                    return EntryPage(
                        items=[self._entry_from_row(row) for row in returned],
                        scanned_through_sequence=scanned_through,
                        has_more=has_more,
                    )
        except PublicError:
            raise
        except PsycopgError, PoolTimeout:
            raise self._unavailable() from None

    async def read_state(
        self, caller: CallerContext, conversation_id: UUID
    ) -> ReadState:
        """Read only the authenticated member's watermark without renewing activity."""
        caller.require_current()
        try:
            async with self._pool.connection() as connection:
                cursor = await connection.execute(
                    "SELECT last_read_sequence FROM conversations.members "
                    "WHERE conversation_id = %s AND user_id = %s",
                    (conversation_id, caller.user_id),
                )
                row = await cursor.fetchone()
        except PsycopgError, PoolTimeout:
            raise self._unavailable() from None
        if row is None:
            raise self._not_found()
        return ReadState(own_last_read_sequence=row[0])

    async def acknowledge_read(
        self,
        caller: CallerContext,
        conversation_id: UUID,
        acknowledgement: ReadAcknowledgement,
    ) -> ReadState:
        """Atomically advance only the caller's watermark through committed entries."""
        caller.require_current()
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    await self._require_member(
                        connection, conversation_id, caller.user_id
                    )
                    cursor = await connection.execute(
                        "SELECT COALESCE(max(sequence), 0) FROM conversations.entries "
                        "WHERE conversation_id = %s",
                        (conversation_id,),
                    )
                    maximum_row = await cursor.fetchone()
                    if maximum_row is None:
                        raise self._unavailable()
                    maximum = maximum_row[0]
                    if acknowledgement.last_read_sequence > maximum:
                        raise PublicError(
                            ERRORS[422],
                            (FieldError("body", "beyond_committed_sequence"),),
                        )
                    await connection.execute(
                        "UPDATE conversations.members SET last_read_sequence = %s, "
                        "read_at = clock_timestamp() WHERE conversation_id = %s AND user_id = %s "
                        "AND last_read_sequence < %s",
                        (
                            acknowledgement.last_read_sequence,
                            conversation_id,
                            caller.user_id,
                            acknowledgement.last_read_sequence,
                        ),
                    )
                    cursor = await connection.execute(
                        "SELECT last_read_sequence FROM conversations.members "
                        "WHERE conversation_id = %s AND user_id = %s",
                        (conversation_id, caller.user_id),
                    )
                    row = await cursor.fetchone()
                    if row is None:
                        raise self._not_found()
                    return ReadState(own_last_read_sequence=row[0])
        except PublicError:
            raise
        except PsycopgError, PoolTimeout:
            raise self._unavailable() from None
