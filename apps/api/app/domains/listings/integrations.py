"""Listings adapters for reviewed Identity and Conversations public calls."""

from app.core.errors import ERRORS, PublicError
from app.core.identifiers import UserId
from app.domains.identity import public as identity_public


class PublicListingsIdentity:
    """Use Identity's narrow capability API; never read Identity-owned tables."""

    async def account_is_eligible(self, user_id: UserId) -> bool:
        """Require a current regular account and fail closed until Identity is wired."""
        try:
            result = await identity_public.check_account_eligibility(
                user_id, required_class="regular"
            )
        except NotImplementedError:
            raise PublicError(ERRORS[503]) from None
        return result.eligible
