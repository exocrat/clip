"""Listings adapters for reviewed Identity and Conversations public calls."""

from app.core.errors import ERRORS, PublicError
from app.core.identifiers import UserId
import app.domains.identity.public as identity_public


class PublicListingsIdentity:
    """Use Identity's narrow capability API; never read Identity-owned tables."""

    async def account_is_eligible(self, user_id: UserId) -> bool:
        """Check current eligibility; Listings enforces regular-only seller actions."""
        try:
            result = await identity_public.check_account_eligibility(
                user_id, required_class=None
            )
        except NotImplementedError:
            raise PublicError(ERRORS[503]) from None
        return result.eligible
