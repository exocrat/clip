"""Explicit synthetic Microsoft fixture; never injects a provider into API startup."""

from datetime import UTC, datetime

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt.api_jwt
import pytest

from apps.api.tests.domains.identity.microsoft_fixtures import SignedTokens


@pytest.fixture(scope="module")
def signing_key():
    """One transient RSA key per module; never saved or sent to any provider."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def jwt_clock(monkeypatch):
    """Control PyJWT's real date checks explicitly, only in requesting tests.

    Keep signature/issuer/audience/date validation enabled. Patch the installed
    library's datetime lookup, never global time or deployed validation options.
    Mutable UTC lets tests probe exact microsecond boundaries without sleeping.
    """
    clock = [datetime(2030, 1, 1, tzinfo=UTC)]

    class ControlledDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0].astimezone(tz) if tz else clock[0].replace(tzinfo=None)

    monkeypatch.setattr(jwt.api_jwt, "datetime", ControlledDateTime)
    return clock


@pytest.fixture
def signed_tokens(signing_key, jwt_clock):
    """Explicit synthetic signer/time; each test has isolated mutable clock."""
    return SignedTokens(lambda: jwt_clock[0], signing_key)


# Explicit fixture import registers the same safe disposable route for both services.
from apps.api.tests.domains.identity.postgres_fixtures import disposable_database

# Shared Step7 integration fixture composes real services; no autouse auth injection.
from apps.api.tests.domains.identity.session_fixtures import (
    identity_runtime,
    temporary_state,
)
