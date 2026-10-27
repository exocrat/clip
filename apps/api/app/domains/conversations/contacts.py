"""Member-authorized, ephemeral own-contact preparation through Identity."""

from uuid import UUID

from psycopg import Error as PsycopgError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    ContactOptionsView,
    ContactPreparationRequest,
    ContactSharingContext,
    SelectedOwnContacts,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError
from app.core.runtime_bindings import runtime_claims
from app.domains.identity.public import (
    get_selected_own_contacts,
    get_shareable_contact_options,
)


class PostgresContactPreparation:
    """Check owned membership before installing Identity's narrow disclosure scope.

    No values, field selections, entries or activity timestamps are persisted.
    The write-disabled marker is a preflight here; eventual encrypted sharing
    must recheck it under the participant-write thread lock.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def _authorize(self, caller: CallerContext, conversation_id: UUID) -> None:
        """Hide missing/nonmember threads alike and refuse retired-thread work."""
        caller.require_current()
        try:
            async with self._pool.connection() as connection:
                cursor = await connection.execute(
                    "SELECT thread.participant_writes_disabled_at "
                    "FROM conversations.threads AS thread "
                    "JOIN conversations.members AS member ON member.conversation_id=thread.id "
                    "WHERE thread.id=%s AND member.user_id=%s",
                    (conversation_id, caller.user_id),
                )
                row = await cursor.fetchone()
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None
        if row is None:
            raise PublicError(ERRORS[404])
        if row[0] is not None:
            raise PublicError(ERRORS[409])

    async def read_options(
        self, caller: CallerContext, conversation_id: UUID
    ) -> ContactOptionsView:
        """Return only this member's own availability; never substitute empty flags."""
        await self._authorize(caller, conversation_id)
        with runtime_claims(
            {
                "identity.contact_share": ContactSharingContext(
                    caller.user_id, conversation_id
                )
            }
        ):
            options = await get_shareable_contact_options(caller, conversation_id)
        if options.user_id != caller.user_id:
            raise PublicError(ERRORS[503])
        return ContactOptionsView(
            email_available=options.has_email,
            phone_available=options.has_phone,
            upi_available=options.has_upi_id,
        )

    async def prepare(
        self,
        caller: CallerContext,
        conversation_id: UUID,
        request: ContactPreparationRequest,
    ) -> SelectedOwnContacts:
        """Disclose only explicit, distinct, confirmed own fields to the actor's client."""
        await self._authorize(caller, conversation_id)
        fields = frozenset(request.fields)
        if len(fields) != len(request.fields):
            raise PublicError(ERRORS[422], (FieldError("fields", "duplicate_field"),))
        with runtime_claims(
            {
                "identity.contact_share": ContactSharingContext(
                    caller.user_id, conversation_id, fields
                )
            }
        ):
            selected = await get_selected_own_contacts(caller, conversation_id, fields)
        # Refuse a broken provider instead of leaking a partial/unselected value.
        values = selected.model_dump()
        if any(
            (value is not None) != (name in fields) for name, value in values.items()
        ):
            raise PublicError(ERRORS[503])
        return selected
