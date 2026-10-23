"""Offline composition with the actual SES adapter; no AWS clients or emails."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import re
import secrets
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.domains.identity.email import SesEmailSender
from app.domains.identity.temporary_crypto import TemporaryKeys
from app.domains.identity.temporary_delivery import prepare_challenge

NOW = datetime(2030, 1, 1, tzinfo=UTC)
EMAIL = "synthetic@example.invalid"


class RecordingClient:
    """Observe synthetic SDK requests, optionally failing after acceptance is possible."""

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def send_email(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("PRIVATE_PROVIDER_DETAIL")
        return {"MessageId": "synthetic-accepted"}


def setup(purpose="initial_verification", fail=False):
    """Use random synthetic keys and the real sandbox-only transport with fake SDK."""
    keys = TemporaryKeys("synthetic-v1", *(secrets.token_bytes(32) for _ in range(3)))
    challenge = prepare_challenge(
        keys, EMAIL.upper(), uuid4(), purpose, NOW + timedelta(minutes=10)
    )
    client = RecordingClient(fail)
    settings = Settings(
        environment="test", email_provider="ses", ses_test_recipients=(EMAIL,)
    )
    return keys, challenge, client, SesEmailSender(settings, client)


@pytest.mark.parametrize("purpose", ["initial_verification", "password_reset"])
def test_real_transport_receives_matching_code_without_persistable_plaintext(purpose):
    keys, challenge, client, sender = setup(purpose)
    assert client.calls == []
    assert EMAIL not in repr(challenge)
    assert challenge.delivery.dispatch(sender, now=NOW)
    body = client.calls[0]["Content"]["Simple"]["Body"]["Text"]["Data"]
    code = re.search(r"Use ([0-9]{6}) to", body).group(1)
    assert challenge.verifier == keys.otp_verifier(
        code,
        challenge.challenge_id,
        purpose,
        challenge.target_digest,
        challenge.expires_at,
    )
    assert code not in repr(challenge)
    assert (
        keys.decrypt_target(
            challenge.encrypted_target,
            challenge.challenge_id,
            purpose,
            challenge.target_digest,
            challenge.expires_at,
        )
        == EMAIL
    )
    assert ("reset" in body) == (purpose == "password_reset")
    assert client.calls[0]["Destination"] == {"ToAddresses": [EMAIL]}
    assert not challenge.delivery.dispatch(sender, now=NOW)
    assert len(client.calls) == 1


def test_concurrent_dispatch_submits_only_once():
    _, challenge, client, sender = setup()
    with ThreadPoolExecutor(max_workers=16) as pool:
        outcomes = list(
            pool.map(lambda _: challenge.delivery.dispatch(sender, now=NOW), range(32))
        )
    assert sum(outcomes) == 1
    assert len(client.calls) == 1


def test_uncertain_provider_failure_never_retries_or_propagates_private_error():
    _, challenge, client, sender = setup(fail=True)
    assert not challenge.delivery.dispatch(sender, now=NOW)
    assert not challenge.delivery.dispatch(sender, now=NOW)
    assert len(client.calls) == 1
    assert challenge.delivery._email is None and challenge.delivery._code is None


@pytest.mark.parametrize("mode", ["expired", "discarded"])
def test_expired_or_suppressed_ticket_never_calls_transport(mode):
    _, challenge, client, sender = setup()
    if mode == "discarded":
        challenge.delivery.discard()
    instant = challenge.expires_at if mode == "expired" else NOW
    assert not challenge.delivery.dispatch(sender, now=instant)
    assert not challenge.delivery.dispatch(sender, now=NOW)
    assert client.calls == []


def test_generation_preserves_leading_zeroes(monkeypatch):
    monkeypatch.setattr(
        "app.domains.identity.temporary_delivery.secrets.randbelow", lambda upper: 7
    )
    keys, challenge, client, sender = setup()
    assert challenge.delivery.dispatch(sender, now=NOW)
    assert challenge.verifier == keys.otp_verifier(
        "000007",
        challenge.challenge_id,
        challenge.purpose,
        challenge.target_digest,
        challenge.expires_at,
    )
    assert (
        "Use 000007 to" in client.calls[0]["Content"]["Simple"]["Body"]["Text"]["Data"]
    )
