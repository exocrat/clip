"""Approved temporary-account password validation and Argon2id hashing only.

Never normalize or trim a password. Inputs remain SecretStr and hashes stay in
owning-domain persistence; neither is an API response or log value. Password
sign-in/reset orchestration belongs to sessions.py; this module exposes no HTTP
or persistence. Automatic rehash remains a separately reviewed policy.
"""

from argon2 import PasswordHasher, extract_parameters
from argon2.exceptions import VerifyMismatchError
from argon2.low_level import Type
from pydantic import SecretStr

from app.core.errors import ERRORS, PublicError


class TemporaryPasswords:
    """Hash with explicit approved parameters and independently random salts."""

    def __init__(self) -> None:
        """Pin Argon2id parameters rather than inherit changing library defaults."""
        self._hasher = PasswordHasher(
            time_cost=2,
            memory_cost=19 * 1024,
            parallelism=1,
            hash_len=32,
            salt_len=16,
            encoding="utf-8",
            type=Type.ID,
        )

    @staticmethod
    def validate(password: SecretStr) -> None:
        """Accept 15–128 Unicode characters, including spaces, without rewriting.

        Bound input before UTF-8 encoding; invalid surrogate text fails safely.
        This checks policy only and neither authenticates nor stores anything.
        """
        if not isinstance(password, SecretStr):
            raise PublicError(ERRORS[422])
        value = password.get_secret_value()
        if not 15 <= len(value) <= 128:
            raise PublicError(ERRORS[422])
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise PublicError(ERRORS[422]) from None

    def hash(self, password: SecretStr) -> str:
        """Create an encoded salted Argon2id hash; suppress private library errors.

        Activation calls this only after OTP verification, within its transaction.
        A hashing failure aborts account creation and rolls back OTP consumption.
        """
        self.validate(password)
        try:
            return self._hasher.hash(password.get_secret_value())
        except Exception:
            raise PublicError(ERRORS[503]) from None

    def verify(self, encoded: str, password: SecretStr) -> bool:
        """Verify trusted stored hashes at bounded approved cost, with safe errors.

        Unknown/ineligible login paths supply a real dummy hash. Unexpected stored
        algorithms/costs fail closed rather than execute attacker-chosen work.
        No automatic rehash or password/account-state response is introduced.
        """
        try:
            self.validate(password)
        except PublicError:
            return False
        try:
            params = extract_parameters(encoded)
            if (
                params.type,
                params.version,
                params.memory_cost,
                params.time_cost,
                params.parallelism,
                params.salt_len,
                params.hash_len,
            ) != (Type.ID, 19, 19456, 2, 1, 16, 32):
                raise PublicError(ERRORS[503])
            return self._hasher.verify(encoded, password.get_secret_value())
        except VerifyMismatchError:
            return False
        except Exception:
            raise PublicError(ERRORS[503]) from None
