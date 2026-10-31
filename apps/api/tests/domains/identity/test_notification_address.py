"""Synthetic cryptographic checks for the Identity notification destination."""

from uuid import uuid4
from datetime import UTC, datetime, timedelta
import asyncio

import pytest
from cryptography.exceptions import InvalidTag

from app.domains.identity.notification_address import NotificationAddressCipher
from app.domains.identity.notification_address import NotificationRecipientResolver
from app.domains.identity.temporary_crypto import TemporaryKeys
from app.contracts.domain_types import NotificationWorkerContext
from app.core.errors import PublicError
from app.core.runtime_bindings import runtime_claims
from pydantic import SecretStr
from apps.api.tests.domains.identity.session_fixtures import activate, EMAIL, SOURCE


def test_address_is_randomized_and_bound_to_account_and_version():
    """Ciphertexts hide the address and cannot be moved between accounts."""
    cipher = NotificationAddressCipher(
        TemporaryKeys("v1", b"a" * 32, b"b" * 32, b"c" * 32)
    )
    user = uuid4()
    first = cipher.encrypt(user, "Member@Example.invalid")
    second = cipher.encrypt(user, "Member@Example.invalid")
    assert first != second
    assert b"member@example.invalid" not in first
    assert cipher.decrypt(user, first, "v1") == "member@example.invalid"
    with pytest.raises(InvalidTag):
        cipher.decrypt(uuid4(), first, "v1")
    with pytest.raises(ValueError):
        cipher.decrypt(user, first, "v2")
    with pytest.raises(InvalidTag):
        cipher.decrypt(user, first[:-1] + bytes([first[-1] ^ 1]), "v1")


def test_resolver_requires_worker_permit_and_current_account():
    """An in-process marker alone cannot retrieve an address or bypass expiry."""
    now = datetime.now(UTC)
    keys = TemporaryKeys("v1", b"a" * 32, b"b" * 32, b"c" * 32)
    user = uuid4()
    encrypted = NotificationAddressCipher(keys).encrypt(user, "test@example.invalid")
    row = [
        "temporary",
        "active",
        now - timedelta(days=1),
        now - timedelta(days=1),
        now + timedelta(days=1),
        None,
        encrypted,
        "v1",
    ]
    permit = object()

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, *args):
            return self

        def fetchone(self):
            return tuple(row)

    resolver = NotificationRecipientResolver(Connection, lambda: now, keys, permit)

    async def scenario():
        with pytest.raises(PublicError):
            await resolver.resolve(NotificationWorkerContext(), user)
        with runtime_claims({"identity.notification_worker": permit}):
            result = await resolver.resolve(NotificationWorkerContext(), user)
            assert result is not None and result.email == "test@example.invalid"
            row[4] = now
            assert await resolver.resolve(NotificationWorkerContext(), user) is None

    asyncio.run(scenario())


@pytest.mark.parametrize("account_class", ["temporary", "regular"])
def test_real_auth_persists_encrypted_destination(
    identity_runtime, signed_tokens, account_class
):
    """A successful real account transaction stores the correct login address."""
    state = identity_runtime
    if account_class == "temporary":
        grant = activate(state)
        expected = EMAIL
    else:
        attempt = state.service.start_microsoft(SOURCE)
        expected = "synthetic-recipient@iisc.ac.in"
        token = SecretStr(
            signed_tokens.token({"nonce": attempt.nonce, "email": expected})
        )
        grant = state.service.microsoft_exchange(
            token, attempt.token.get_secret_value(), SOURCE, signed_tokens.validator()
        )
    user = grant.identity.caller.user_id
    with state.connect() as c:
        ciphertext, version = c.execute(
            "SELECT ciphertext,key_version FROM identity.notification_destinations WHERE user_id=%s",
            (user,),
        ).fetchone()
    assert expected.encode() not in bytes(ciphertext)
    assert (
        NotificationAddressCipher(state.keys).decrypt(user, bytes(ciphertext), version)
        == expected
    )
    permit = object()
    resolver = NotificationRecipientResolver(
        state.connect, lambda: state.clock[0], state.keys, permit
    )

    async def resolve():
        with runtime_claims({"identity.notification_worker": permit}):
            return await resolver.resolve(NotificationWorkerContext(), user)

    assert asyncio.run(resolve()).email == expected
    state.service.revoke_account(user)
    assert asyncio.run(resolve()) is None
    state.clock[0] += timedelta(days=30)
    assert state.cleanup.run().counts["notification_destinations"] == 1
    assert state.cleanup.run(apply=True).counts["notification_destinations"] == 1
    with state.connect() as c:
        assert (
            c.execute(
                "SELECT count(*) FROM identity.notification_destinations WHERE user_id=%s",
                (user,),
            ).fetchone()[0]
            == 0
        )
