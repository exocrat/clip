"""Explicit synthetic Microsoft fixture; never injects a provider into API startup."""

import pytest

from apps.api.tests.domains.identity.microsoft_fixtures import SignedTokens


@pytest.fixture(scope="module")
def signed_tokens():
    """Reuse an in-memory synthetic RSA key while every token gets fresh dates."""
    return SignedTokens()
