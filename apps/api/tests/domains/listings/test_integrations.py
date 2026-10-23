"""Listings fails closed while Identity's public implementation is a declaration."""

import asyncio
from uuid import uuid4

import pytest

from app.core.errors import PublicError
from app.domains.listings.integrations import PublicListingsIdentity


def test_identity_declaration_never_authorizes_a_listing_request():
    """A missing Identity provider becomes the common safe 503, never success."""
    with pytest.raises(PublicError) as captured:
        asyncio.run(PublicListingsIdentity().account_is_eligible(uuid4()))
    assert captured.value.spec.status == 503
