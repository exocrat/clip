"""Real Argon2id policy/parameter checks using synthetic passwords only."""

from argon2 import PasswordHasher, extract_parameters
from argon2.exceptions import VerifyMismatchError
from argon2.low_level import Type
from pydantic import SecretStr
import pytest

from app.core.errors import PublicError
from app.domains.identity.temporary_passwords import TemporaryPasswords


@pytest.mark.parametrize(
    "value", ["x" * 15, "x" * 128, "  synthetic passphrase  ", "é" * 15, " " * 15]
)
def test_exact_password_preserved_with_approved_parameters(value):
    encoded = TemporaryPasswords().hash(SecretStr(value))
    parameters = extract_parameters(encoded)
    assert parameters.type == Type.ID and parameters.version == 19
    assert (parameters.memory_cost, parameters.time_cost, parameters.parallelism) == (
        19456,
        2,
        1,
    )
    assert parameters.salt_len == 16 and parameters.hash_len == 32
    assert PasswordHasher().verify(encoded, value)
    with pytest.raises(VerifyMismatchError):
        PasswordHasher().verify(encoded, value + "different")


@pytest.mark.parametrize(
    "value",
    [
        SecretStr("x" * 14),
        SecretStr("x" * 129),
        SecretStr("\ud800" * 15),
        "synthetic plain string",
        None,
    ],
)
def test_invalid_password_is_rejected_without_private_error(value):
    with pytest.raises(PublicError) as error:
        TemporaryPasswords().hash(value)
    assert error.value.spec.status == 422
    assert str(error.value) == "validation_error"


def test_repeated_hashes_get_independent_random_salts():
    passwords = TemporaryPasswords()
    value = SecretStr("synthetic passphrase")
    first, second = passwords.hash(value), passwords.hash(value)
    assert first != second
    assert PasswordHasher().verify(first, value.get_secret_value())
    assert PasswordHasher().verify(second, value.get_secret_value())


def test_hash_failure_is_safe(monkeypatch):
    def failed(self, password, **kwargs):
        raise RuntimeError("PRIVATE_PASSWORD_DETAIL")

    monkeypatch.setattr(PasswordHasher, "hash", failed)
    with pytest.raises(PublicError) as error:
        TemporaryPasswords().hash(SecretStr("synthetic passphrase"))
    assert error.value.spec.status == 503
    assert str(error.value) == "dependency_unavailable"
