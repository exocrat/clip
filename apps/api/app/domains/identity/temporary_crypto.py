"""Private temporary-authentication protection; no persistence, send or activation.

Keys must be independently generated and supplied through trusted secret wiring.
Lookup normalization/key changes need coordinated review to preserve enrollment
and idempotency guards. No default key or production environment bypass exists.
"""

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import hmac
from ipaddress import IPv4Address, IPv6Address
import json
import re
import secrets
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.timestamps import as_utc

PURPOSES = frozenset({"initial_verification", "password_reset"})


def normalize_login(email: str) -> str:
    """Use approved ASCII trim/lowercase without provider-specific alias rewriting."""
    if not isinstance(email, str):
        raise ValueError("Invalid email")
    value = email.strip().lower()
    if (
        not value.isascii()
        or not 3 <= len(value) <= 254
        or value.count("@") != 1
        or any(c.isspace() or ord(c) < 33 for c in value)
    ):
        raise ValueError("Invalid email")
    local, domain = value.split("@")
    if (
        not re.fullmatch(r"[a-z0-9!#$%&'*+/=?^_`{|}~.\-]+", local)
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
        or len(local) > 64
        or len(domain) > 253
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", domain)
        or "." not in domain
        or any(
            not part or len(part) > 63 or part.startswith("-") or part.endswith("-")
            for part in domain.split(".")
        )
    ):
        raise ValueError("Invalid email")
    return value


@dataclass(frozen=True)
class TemporaryKeys:
    """Separate 256-bit keys with a non-secret coordinated-rollout version label."""

    version: str
    lookup: bytes = field(repr=False)
    verifier: bytes = field(repr=False)
    target_encryption: bytes = field(repr=False)

    def __post_init__(self) -> None:
        """Reject placeholders, accidental reuse and unsafe version labels."""
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", self.version):
            raise ValueError("Invalid key version")
        keys = (self.lookup, self.verifier, self.target_encryption)
        if (
            any(not isinstance(key, bytes) or len(key) != 32 for key in keys)
            or len(set(keys)) != 3
        ):
            raise ValueError("Three independent 256-bit keys required")

    def _mac(self, key: bytes, label: str, *values: str) -> bytes:
        """Frame private values unambiguously under a domain-separated HMAC."""
        payload = json.dumps(
            ["clip-temporary-v1", self.version, label, *values], separators=(",", ":")
        ).encode()
        return hmac.digest(key, payload, "sha256")

    def target_digest(self, email: str) -> bytes:
        """Return a private stable normalized-login lookup/enrollment identifier."""
        return self._mac(self.lookup, "target", normalize_login(email))

    def source_digest(self, address: IPv4Address | IPv6Address) -> bytes:
        """Protect trusted server-resolved source IP; never accept a browser header."""
        if not isinstance(address, (IPv4Address, IPv6Address)):
            raise ValueError("Trusted parsed source address required")
        return self._mac(self.lookup, "source", address.compressed)

    def request_digest(self, email: str, purpose: str, operation_id: UUID) -> bytes:
        """Identify one purpose/target/request without retaining a clear address."""
        self._purpose(purpose)
        if not isinstance(operation_id, UUID) or operation_id.version != 4:
            raise ValueError("UUIDv4 operation required")
        return self._mac(
            self.lookup, "request", normalize_login(email), purpose, str(operation_id)
        )

    def credential_key(self, email: str) -> str:
        """Use the same protected login key for later credential lookup, not contacts."""
        return self.version + ":" + self.target_digest(email).hex()

    def fingerprints(self) -> tuple[bytes, bytes, bytes]:
        """Public key commitments detect accidental key/version replacement in storage."""
        return (
            hashlib.sha256(self.lookup).digest(),
            hashlib.sha256(self.verifier).digest(),
            hashlib.sha256(self.target_encryption).digest(),
        )

    @staticmethod
    def _purpose(purpose: str) -> None:
        """Keep initial verification and reset as distinct, reviewed capabilities."""
        if purpose not in PURPOSES:
            raise ValueError("Invalid challenge purpose")

    def _context(
        self, challenge_id: UUID, purpose: str, target: bytes, expires_at: datetime
    ) -> str:
        """Bind verifier and ciphertext to one challenge, target, purpose and expiry."""
        self._purpose(purpose)
        if (
            not isinstance(challenge_id, UUID)
            or challenge_id.version != 4
            or len(target) != 32
        ):
            raise ValueError("Invalid challenge identity")
        return json.dumps(
            [
                str(challenge_id),
                purpose,
                target.hex(),
                as_utc(expires_at).isoformat(timespec="microseconds"),
            ],
            separators=(",", ":"),
        )

    def otp_verifier(
        self,
        code: str,
        challenge_id: UUID,
        purpose: str,
        target: bytes,
        expires_at: datetime,
    ) -> bytes:
        """Store a keyed, purpose-bound verifier; raw code never reaches persistence."""
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code):
            raise ValueError("Invalid code format")
        return self._mac(
            self.verifier,
            "otp",
            self._context(challenge_id, purpose, target, expires_at),
            code,
        )

    def encrypt_target(
        self, email: str, challenge_id: UUID, purpose: str, expires_at: datetime
    ) -> bytes:
        """Protect the private target with fresh AES-GCM nonce and bound context."""
        value = normalize_login(email)
        aad = self._context(
            challenge_id, purpose, self.target_digest(value), expires_at
        ).encode()
        nonce = secrets.token_bytes(12)
        return nonce + AESGCM(self.target_encryption).encrypt(
            nonce, value.encode(), aad
        )

    def decrypt_target(
        self,
        encrypted: bytes,
        challenge_id: UUID,
        purpose: str,
        target: bytes,
        expires_at: datetime,
    ) -> str:
        """Recover only an authenticated matching target for the owning transaction."""
        aad = self._context(challenge_id, purpose, target, expires_at).encode()
        value = (
            AESGCM(self.target_encryption)
            .decrypt(encrypted[:12], encrypted[12:], aad)
            .decode()
        )
        if normalize_login(value) != value or not hmac.compare_digest(
            self.target_digest(value), target
        ):
            raise ValueError("Target binding mismatch")
        return value
