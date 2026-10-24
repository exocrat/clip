"""Explicit synthetic Microsoft fixture; never injects a provider into API startup."""

import pytest

from apps.api.tests.domains.identity.microsoft_fixtures import SignedTokens


@pytest.fixture(scope="module")
def signed_tokens():
    """Reuse an in-memory synthetic RSA key while every token gets fresh dates."""
    return SignedTokens()


# Explicit fixture import registers the same safe disposable route for both services.
from apps.api.tests.domains.identity.postgres_fixtures import disposable_database

# Shared Step7 integration fixture composes real services; no autouse auth injection.
from apps.api.tests.domains.identity.session_fixtures import identity_runtime
