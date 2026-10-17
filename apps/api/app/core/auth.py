"""Internal authenticated caller shape; real credential validation belongs to Identity."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import Request

from app.core.errors import ERRORS, PublicError
from app.core.identifiers import format_id
from app.core.timestamps import as_utc


@dataclass(frozen=True)
class CallerContext:
    """Immutable validated facts supplied by the trusted authentication boundary.

    Constructing this Python object is not proof of authentication. Only Identity
    wiring may populate the internal ASGI scope slot; no request input is read.
    """

    user_id: UUID
    account_class: Literal["regular", "temporary"]
    valid_until: datetime

    def __post_init__(self) -> None:
        """Validate types and normalize validity without inventing permissions."""
        format_id(self.user_id)
        if self.account_class not in ("regular", "temporary"):
            raise ValueError("Invalid account class")
        object.__setattr__(self, "valid_until", as_utc(self.valid_until))

    def require_current(self, now: datetime | None = None) -> None:
        """Reject an expired context; Identity must also check current revocation."""
        if self.valid_until <= as_utc(now if now is not None else datetime.now(UTC)):
            raise PublicError(ERRORS[401])


async def require_caller(request: Request) -> CallerContext:
    """Consume only server-established context, denying access until Identity wires it.

    Header/query/body IDs are deliberately ignored. Domain handlers use this
    dependency and then enforce their own ownership/participant permissions.
    """
    caller = request.scope.get("clip.caller")
    if not isinstance(caller, CallerContext):
        raise PublicError(ERRORS[401])
    caller.require_current()
    return caller
