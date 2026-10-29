"""Own profile/contact persistence and scoped, confirmed own-contact disclosure.

No reverse Conversation dependency or private-table read. Its trusted owner must
establish participation/confirmation before installing ContactSharingContext.
Own management requires actual authenticated caller composition; object creation
alone proves no authentication. Login identifiers and copied encrypted shares
are never changed by these source-contact operations.
"""

import asyncio
from contextlib import contextmanager
from datetime import datetime
import re
from typing import Any, Callable, Iterator
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from psycopg.pq import TransactionStatus
from psycopg.errors import UniqueViolation

from app.contracts.domain_types import (
    ContactField,
    ContactSharingContext,
    OwnContacts,
    ProfilePatch,
    ProfileView,
    SelectedOwnContacts,
    ShareableContactOptions,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError
from app.core.identifiers import format_id
from app.core.runtime_bindings import runtime_claim
from app.core.timestamps import as_utc
from app.domains.identity.capabilities import ALLOWED, Capability, PostgresCapabilities
from app.domains.identity.temporary_challenges import Database

FIELDS = {"email": "email", "phone": "phone", "upi_id": "upi_id"}


def contact_value(kind: ContactField, raw: str) -> str:
    """Trim and validate source-contact syntax without DNS/provider/payment calls.

    Keep the entered email spelling/aliases; it is displayed/shared, not used as
    an authentication lookup or verified notification address. Library failures
    and rejected values never appear in public errors or logs.
    """
    if kind not in FIELDS or not isinstance(raw, str):
        raise PublicError(ERRORS[422])
    value = raw.strip()
    try:
        if not value or len(value) > 254:
            raise ValueError
        value.encode("utf-8")
        if kind == "email":
            validate_email(
                value,
                check_deliverability=False,
                allow_smtputf8=True,
                allow_display_name=False,
            )
        elif kind == "phone":
            if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
                raise ValueError
        elif (
            not 3 <= len(value) <= 100
            or not value.isascii()
            or not re.fullmatch(r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+", value)
        ):
            raise ValueError
        return value
    except ValueError, UnicodeError, EmailNotValidError:
        raise PublicError(
            ERRORS[422], (FieldError("value", "invalid_" + kind),)
        ) from None
    except Exception:
        raise PublicError(ERRORS[503]) from None


class PostgresContacts:
    """User-before-contact transactions with fresh lifecycle/caller checks."""

    def __init__(self, connect: Callable[[], Database], clock: Callable[[], datetime]):
        """Bind explicit trusted dependencies; never discover or contact a provider."""
        self._connect, self._clock = connect, clock

    @contextmanager
    def _own(
        self, caller: CallerContext, capability: Capability
    ) -> Iterator[tuple[Database, tuple[Any, ...], datetime]]:
        """Lock current actor before source rows, denying stale/forged class facts."""
        if not isinstance(caller, CallerContext):
            raise PublicError(ERRORS[401])
        try:
            format_id(caller.user_id)
            with self._connect() as c:
                if c.info.transaction_status != TransactionStatus.IDLE:
                    raise PublicError(ERRORS[503])
                with c.transaction():
                    c.execute("SET LOCAL lock_timeout='3s'")
                    c.execute("SET LOCAL statement_timeout='5s'")
                    row = c.execute(
                        "SELECT account_class,status,created_at,activated_at,expires_at,profile_removed_at,display_name FROM identity.users WHERE id=%s FOR UPDATE",
                        (caller.user_id,),
                    ).fetchone()
                    now = as_utc(self._clock())
                    caller.require_current(now)
                    if (
                        row is None
                        or not PostgresCapabilities._active(row, now)
                        or row[0] != caller.account_class
                    ):
                        raise PublicError(ERRORS[401])
                    if capability not in ALLOWED.get(row[0], frozenset()):
                        raise PublicError(ERRORS[403])
                    yield c, row, now
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[503]) from None

    @staticmethod
    def _values(c: Database, user: UUID) -> tuple[str | None, str | None, str | None]:
        """Read only the authenticated actor's three approved source fields."""
        row = c.execute(
            "SELECT email,phone,upi_id FROM identity.contacts WHERE user_id=%s", (user,)
        ).fetchone()
        return (row[0], row[1], row[2]) if row is not None else (None, None, None)

    def update_profile(self, caller: CallerContext, patch: ProfilePatch) -> ProfileView:
        """Claim/edit a trimmed unique Handle without changing account lifetime.

        Omission preserves the profile; null and invalid Handles are rejected.
        Database uniqueness serializes concurrent case-insensitive claims.
        """
        provided = "display_name" in patch.model_fields_set
        name = patch.display_name
        if provided:
            name = name.strip() if name is not None else None
            if name is None or re.fullmatch(r"[A-Za-z0-9_]{3,30}", name) is None:
                raise PublicError(
                    ERRORS[422], (FieldError("display_name", "invalid_value"),)
                )
        with self._own(caller, Capability.MANAGE_OWN_PROFILE) as (c, row, now):
            if provided:
                # A savepoint turns concurrent unique claims into a safe conflict
                # while keeping the owning profile transaction usable.
                try:
                    with c.transaction():
                        c.execute(
                            "UPDATE identity.users SET display_name=%s,handle_ready=true,revision=revision+1 WHERE id=%s",
                            (name, caller.user_id),
                        )
                except UniqueViolation:
                    raise PublicError(ERRORS[409]) from None
            return ProfileView(
                user_id=caller.user_id, display_name=name if provided else row[6]
            )

    def read_contacts(self, caller: CallerContext) -> OwnContacts:
        """Return own values only on the explicit authenticated own-contact endpoint."""
        with self._own(caller, Capability.MANAGE_OWN_CONTACTS) as (c, row, now):
            email, phone, upi = self._values(c, caller.user_id)
            return OwnContacts(email=email, phone=phone, upi_id=upi)

    def set_contact(
        self, caller: CallerContext, kind: ContactField, value: str
    ) -> None:
        """Upsert one code-owned column, preserving other fields and login identity."""
        validated = contact_value(kind, value)
        column = FIELDS[kind]
        with self._own(caller, Capability.MANAGE_OWN_CONTACTS) as (c, row, now):
            c.execute(
                f"INSERT INTO identity.contacts(user_id,{column},updated_at) VALUES (%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET {column}=EXCLUDED.{column},updated_at=EXCLUDED.updated_at WHERE identity.contacts.{column} IS DISTINCT FROM EXCLUDED.{column}",
                (caller.user_id, validated, now),
            )

    def delete_contact(self, caller: CallerContext, kind: ContactField) -> None:
        """Immediately remove one source value; no rewrite of client-held shares."""
        if kind not in FIELDS:
            raise PublicError(ERRORS[422])
        with self._own(caller, Capability.MANAGE_OWN_CONTACTS) as (c, row, now):
            c.execute(
                f"UPDATE identity.contacts SET {FIELDS[kind]}=NULL,updated_at=%s WHERE user_id=%s AND {FIELDS[kind]} IS NOT NULL",
                (now, caller.user_id),
            )
            c.execute(
                "DELETE FROM identity.contacts WHERE user_id=%s AND email IS NULL AND phone IS NULL AND upi_id IS NULL",
                (caller.user_id,),
            )

    @staticmethod
    def _sharing(
        caller: CallerContext,
        conversation_id: UUID,
        fields: frozenset[ContactField] | None,
    ) -> None:
        """Require the trusted actor/conversation scope, plus confirmed selections."""
        if not isinstance(caller, CallerContext):
            raise PublicError(ERRORS[401])
        try:
            format_id(conversation_id)
        except ValueError:
            raise PublicError(ERRORS[422]) from None
        scope = runtime_claim("identity.contact_share")
        if (
            not isinstance(scope, ContactSharingContext)
            or scope.actor_id != caller.user_id
            or scope.conversation_id != conversation_id
        ):
            raise PublicError(ERRORS[403])
        if fields is not None:
            if (
                not isinstance(fields, frozenset)
                or not fields
                or not fields <= FIELDS.keys()
            ):
                raise PublicError(ERRORS[422])
            if scope.confirmed_fields is None or not fields <= scope.confirmed_fields:
                raise PublicError(ERRORS[403])

    async def get_shareable_contact_options(
        self, caller: CallerContext, conversation_id: UUID
    ) -> ShareableContactOptions:
        """Availability flags only after trusted participant/consent-flow checks."""
        self._sharing(caller, conversation_id, None)

        def read() -> ShareableContactOptions:
            with self._own(caller, Capability.SHARE_OWN_CONTACTS) as (c, row, now):
                email, phone, upi = self._values(c, caller.user_id)
                return ShareableContactOptions(
                    user_id=caller.user_id,
                    has_email=email is not None,
                    has_phone=phone is not None,
                    has_upi_id=upi is not None,
                )

        return await asyncio.to_thread(read)

    async def get_selected_own_contacts(
        self,
        caller: CallerContext,
        conversation_id: UUID,
        fields: frozenset[ContactField],
    ) -> SelectedOwnContacts:
        """Return only confirmed/requested, still-present values; never substitute."""
        self._sharing(caller, conversation_id, fields)

        def read() -> SelectedOwnContacts:
            with self._own(caller, Capability.SHARE_OWN_CONTACTS) as (c, row, now):
                values = dict(zip(FIELDS, self._values(c, caller.user_id)))
                if any(values[kind] is None for kind in fields):
                    raise PublicError(
                        ERRORS[422], (FieldError("fields", "unavailable_contact"),)
                    )
                return SelectedOwnContacts(
                    email=values["email"] if "email" in fields else None,
                    phone=values["phone"] if "phone" in fields else None,
                    upi_id=values["upi_id"] if "upi_id" in fields else None,
                )

        return await asyncio.to_thread(read)
