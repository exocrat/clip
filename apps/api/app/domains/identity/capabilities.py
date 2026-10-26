"""Approved Identity capability policy and current-account boolean eligibility.

CallerContext is trusted input only after session validation; constructing it is
not authentication. Owners still enforce resource ownership/membership/state.
Public eligibility targets come from trusted context/authoritative relationships,
never a browser-provided user directory. No account data beyond a bool is returned.
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import UUID

from psycopg.pq import TransactionStatus

from app.contracts.domain_types import AccountClass, AccountEligibility
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.core.identifiers import format_id
from app.core.timestamps import as_utc
from app.domains.identity.temporary_challenges import Database


class Capability(str, Enum):
    """Code-owned authorization categories, not browser-selectable permissions."""

    BROWSE = "browse"
    SEARCH = "search"
    SAVE_LISTINGS = "save_listings"
    MANAGE_OWN_WANTED = "manage_own_wanted"
    START_LISTING_CONVERSATION = "start_listing_conversation"
    USE_AUTHORIZED_CONVERSATIONS = "use_authorized_conversations"
    SUBMIT_OFFERS = "submit_offers"
    READ_OWN_PROFILE = "read_own_profile"
    MANAGE_OWN_PROFILE = "manage_own_profile"
    MANAGE_OWN_CONTACTS = "manage_own_contacts"
    SHARE_OWN_CONTACTS = "share_own_contacts"
    MANAGE_SALE_LISTINGS = "manage_sale_listings"
    START_WANTED_RESPONSE = "start_wanted_response"


REGULAR_ONLY = frozenset(
    {Capability.MANAGE_SALE_LISTINGS, Capability.START_WANTED_RESPONSE}
)

# Explicit allowlists: a future enum addition cannot silently grant either class
# a new permission before its reviewed policy mapping is supplied.
SHARED = frozenset(
    {
        Capability.BROWSE,
        Capability.SEARCH,
        Capability.SAVE_LISTINGS,
        Capability.MANAGE_OWN_WANTED,
        Capability.START_LISTING_CONVERSATION,
        Capability.USE_AUTHORIZED_CONVERSATIONS,
        Capability.SUBMIT_OFFERS,
        Capability.READ_OWN_PROFILE,
        Capability.MANAGE_OWN_PROFILE,
        Capability.MANAGE_OWN_CONTACTS,
        Capability.SHARE_OWN_CONTACTS,
    }
)
ALLOWED = {"regular": SHARED | REGULAR_ONLY, "temporary": SHARED}


class PostgresCapabilities:
    """Fresh eligibility/policy checks; never caches class/lifecycle/caller flags."""

    def __init__(
        self, connect: Callable[[], Database], clock: Callable[[], datetime]
    ) -> None:
        """Bind trusted fresh connections/time without I/O or provider discovery."""
        self._connect = connect
        self._clock = clock

    def _snapshot(self, user_id: UUID) -> tuple[tuple[Any, ...] | None, datetime]:
        """Read only Identity account fields using bounded own-domain SQL."""
        try:
            with self._connect() as connection:
                if connection.info.transaction_status != TransactionStatus.IDLE:
                    raise PublicError(ERRORS[503])
                with connection.transaction():
                    connection.execute("SET LOCAL lock_timeout = '3s'")
                    connection.execute("SET LOCAL statement_timeout = '5s'")
                    row = connection.execute(
                        "SELECT account_class,status,created_at,activated_at,expires_at,profile_removed_at "
                        "FROM identity.users WHERE id=%s",
                        (user_id,),
                    ).fetchone()
                    return row, as_utc(self._clock())
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[503]) from None

    @staticmethod
    def _active(row: tuple[Any, ...] | None, now: datetime) -> bool:
        """No capability survives pending/revoked/removed/future/expired state."""
        if row is None or row[1] != "active" or row[5] is not None or now < row[2]:
            return False
        if row[0] == "regular":
            return row[4] is None
        return (
            row[0] == "temporary"
            and row[3] is not None
            and row[4] is not None
            and row[3] <= now < row[4]
        )

    @staticmethod
    def _identifier(user_id: UUID) -> None:
        """Require the existing UUIDv4 contract; errors never echo supplied IDs."""
        try:
            format_id(user_id)
        except ValueError:
            raise PublicError(ERRORS[422]) from None

    def require_capability(self, caller: CallerContext, capability: Capability) -> None:
        """Authorize a code-owned capability for an already authenticated caller.

        Recheck current account and caller expiry/class, denying stale facts.
        Temporary users retain wanted authorship/existing conversation rights;
        only sale management and wanted-response initiation require regular class.
        This does not prove resource ownership, participant consent or session
        authenticity. Public routes explicitly owned as public stay public.
        """
        if not isinstance(caller, CallerContext):
            raise PublicError(ERRORS[401])
        if not isinstance(capability, Capability):
            raise PublicError(ERRORS[422])
        self._identifier(caller.user_id)
        row, now = self._snapshot(caller.user_id)
        caller.require_current(now)
        if not self._active(row, now) or row is None or row[0] != caller.account_class:
            raise PublicError(ERRORS[401])
        if capability not in ALLOWED.get(row[0], frozenset()):
            raise PublicError(ERRORS[403])

    async def check_account_eligibility(
        self, user_id: UUID, required_class: AccountClass | None = None
    ) -> AccountEligibility:
        """Implement reviewed boolean-only public eligibility with exact class match.

        Reads no sessions: a target account can be eligible while offline. Calling
        domains must supply authoritative IDs and authenticate their own actor.
        Move blocking SQL outside the event loop; no fabricated success fallback.
        """
        self._identifier(user_id)
        if required_class not in (None, "regular", "temporary"):
            raise PublicError(ERRORS[422])
        row, now = await asyncio.to_thread(self._snapshot, user_id)
        eligible = (
            self._active(row, now)
            and row is not None
            and (required_class is None or row[0] == required_class)
        )
        return AccountEligibility(eligible=eligible)
