"""No-send tests of approved normalization, key separation and protected targets."""

from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
import secrets
from uuid import uuid4

from cryptography.exceptions import InvalidTag
import pytest

from app.domains.identity.temporary_crypto import TemporaryKeys, normalize_login


@pytest.fixture
def temporary_keys():
    return TemporaryKeys("synthetic-v1", *(secrets.token_bytes(32) for _ in range(3)))


def test_normalization_preserves_provider_aliases():
    assert normalize_login("  A.B+tag@EXAMPLE.invalid  ") == "a.b+tag@example.invalid"
    assert normalize_login("ab@example.invalid") != normalize_login(
        "a.b@example.invalid"
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "x",
        "x@@example.invalid",
        "x\n@example.invalid",
        "x@localhost",
        ".x@example.invalid",
        "x..y@example.invalid",
        "x@-example.invalid",
        "Name <x@example.invalid>",
        "x@ｅxample.invalid",
    ],
)
def test_bad_email_is_rejected(value):
    with pytest.raises(ValueError):
        normalize_login(value)


def test_protected_target_nonce_context_and_verifier(temporary_keys):
    keys = temporary_keys
    identifier = uuid4()
    expiry = datetime(2030, 1, 1, tzinfo=UTC)
    target = keys.target_digest("synthetic@example.invalid")
    encrypted = keys.encrypt_target(
        "SYNTHETIC@example.invalid", identifier, "initial_verification", expiry
    )
    assert b"synthetic@example.invalid" not in encrypted
    assert (
        keys.decrypt_target(
            encrypted, identifier, "initial_verification", target, expiry
        )
        == "synthetic@example.invalid"
    )
    assert encrypted != keys.encrypt_target(
        "synthetic@example.invalid", identifier, "initial_verification", expiry
    )
    for alternate_id, purpose, date in [
        (uuid4(), "initial_verification", expiry),
        (identifier, "password_reset", expiry),
        (identifier, "initial_verification", expiry + timedelta(seconds=1)),
    ]:
        with pytest.raises(InvalidTag):
            keys.decrypt_target(encrypted, alternate_id, purpose, target, date)
    digest = keys.otp_verifier(
        "001234", identifier, "initial_verification", target, expiry
    )
    assert len(digest) == 32 and digest != b"001234"
    assert digest != keys.otp_verifier(
        "001234", identifier, "password_reset", target, expiry
    )


def test_key_and_request_separation(temporary_keys):
    keys = temporary_keys
    operation = uuid4()
    email = "synthetic@example.invalid"
    assert keys.target_digest(email) == keys.target_digest(email.upper())
    assert keys.target_digest(email) != keys.source_digest(ip_address("192.0.2.1"))
    assert keys.request_digest(
        email, "initial_verification", operation
    ) != keys.request_digest(email, "password_reset", operation)
    assert keys.request_digest(
        email, "initial_verification", operation
    ) != keys.request_digest(email, "initial_verification", uuid4())
    assert keys.credential_key(email).startswith(keys.version + ":")
    assert keys.lookup.hex() not in repr(keys)
    with pytest.raises(ValueError):
        keys.source_digest("192.0.2.1")
    with pytest.raises(ValueError):
        TemporaryKeys("bad version", keys.lookup, keys.verifier, keys.target_encryption)
    with pytest.raises(ValueError):
        TemporaryKeys("v1", keys.lookup, keys.lookup, keys.lookup)
