"""Offline SES/Resend, SSM snapshot and safe-profile tests; no real calls."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import SecretStr
import pytest

from app.contracts.domain_types import NotificationClaim, NotificationRecipient
from app.domains.conversations.notifications.email_delivery import (
    EmailConfiguration,
    NotificationEmailSender,
    SsmNotificationConfiguration,
)
from app.domains.conversations.notifications.provider import NotificationDeliveryFailure


def fixture():
    """Create one synthetic claim and destination without real account data."""
    now, user = datetime.now(UTC), uuid4()
    return NotificationClaim(
        intent_id=uuid4(),
        conversation_id=uuid4(),
        recipient_id=user,
        event_kind="new_conversation",
        due_at=now,
        fencing_token=uuid4(),
        lease_expires_at=now + timedelta(minutes=1),
    ), NotificationRecipient(recipient_id=user, email="synthetic@example.invalid")


class Ses:
    """Offline SDK substitute records sender and can simulate an uncertain failure."""

    def __init__(self, failure=False):
        self.failure, self.calls = failure, []

    def send_email(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise TimeoutError("PRIVATE SDK RESPONSE")
        return {"MessageId": "synthetic"}


class Response:
    """Minimal successful fixed-endpoint HTTP response for the synthetic adapter."""

    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, count):
        return b'{"id":"synthetic"}'


class Opener:
    """Capture only synthetic requests; never access a network."""

    def __init__(self, failure=False):
        self.calls, self.failure = [], failure

    def open(self, request, timeout):
        self.calls.append(json.loads(request.data))
        if self.failure:
            raise TimeoutError("PRIVATE HTTP RESPONSE")
        return Response()


@pytest.mark.parametrize(
    "ses_failure,resend_failure", [(False, False), (True, False), (True, True)]
)
def test_ses_first_then_resend_with_bounded_failure(ses_failure, resend_failure):
    """Fallback happens once only, with fixed sender and no provider details."""
    claim, recipient = fixture()
    ses, opener = Ses(ses_failure), Opener(resend_failure)
    sender = NotificationEmailSender(
        lambda: EmailConfiguration("ses", SecretStr("synthetic-key")),
        lambda job: ("Synthetic notification", "Synthetic body"),
        profile="test",
        test_recipients=(recipient.email,),
        ses_client=ses,
        opener=opener,
    )
    if resend_failure:
        with pytest.raises(NotificationDeliveryFailure) as error:
            asyncio.run(sender(claim, recipient))
        assert error.value.kind == "ambiguous" and "PRIVATE" not in str(error.value)
    else:
        asyncio.run(sender(claim, recipient))
    assert len(ses.calls) == 1
    assert ses.calls[0]["FromEmailAddress"] == "updates@clip-iisc.site"
    assert len(opener.calls) == int(ses_failure)
    if opener.calls:
        assert opener.calls[0]["from"] == "updates@clip-iisc.site"


def test_refresh_and_controlled_recipient_gate():
    """Refresh at four hours; mismatched or uncontrolled destinations never send."""
    claim, recipient = fixture()
    time = [0.0]
    loads = []
    ses = Ses()

    def load():
        loads.append(True)
        return EmailConfiguration("ses", SecretStr("synthetic-key"))

    sender = NotificationEmailSender(
        load,
        lambda job: ("Subject", "Body"),
        profile="test",
        test_recipients=(recipient.email,),
        ses_client=ses,
        clock=lambda: time[0],
    )
    asyncio.run(sender(claim, recipient))
    time[0] = 14399
    asyncio.run(sender(claim, recipient))
    time[0] = 14400
    asyncio.run(sender(claim, recipient))
    assert len(loads) == 2 and len(ses.calls) == 3
    with pytest.raises(NotificationDeliveryFailure):
        asyncio.run(
            sender(
                claim,
                NotificationRecipient(
                    recipient_id=recipient.recipient_id, email="other@example.invalid"
                ),
            )
        )
    assert len(ses.calls) == 3


def test_explicit_unlisted_test_recipient_still_requires_matching_identity():
    """Unlisted accounts may receive only their own intended notification."""
    claim, recipient = fixture()
    ses = Ses()
    sender = NotificationEmailSender(
        lambda: EmailConfiguration("ses", SecretStr("synthetic-key")),
        lambda job: ("Subject", "Body"),
        profile="test",
        test_recipients=("other@example.invalid",),
        allow_unlisted_recipients=True,
        ses_client=ses,
    )
    asyncio.run(sender(claim, recipient))
    assert len(ses.calls) == 1
    with pytest.raises(NotificationDeliveryFailure):
        asyncio.run(
            sender(
                claim,
                NotificationRecipient(recipient_id=uuid4(), email=recipient.email),
            )
        )
    assert len(ses.calls) == 1


def test_ssm_snapshot_schema_and_secret_redaction():
    """Read one explicit SecureString snapshot and reject malformed versions."""

    class Client:
        def get_parameter(self, **kwargs):
            assert kwargs == {"Name": "/clip/test/email", "WithDecryption": True}
            return {
                "Parameter": {
                    "Type": "SecureString",
                    "Value": json.dumps(
                        {
                            "version": 1,
                            "primary": "ses",
                            "resend_api_key": "synthetic-secret",
                        }
                    ),
                }
            }

    snapshot = SsmNotificationConfiguration("/clip/test/email", Client())()
    assert snapshot.primary == "ses" and "synthetic-secret" not in repr(snapshot)
    with pytest.raises(ValueError):
        SsmNotificationConfiguration("/unrelated/secret", Client())


def test_production_rejects_injected_provider_and_secret_fakes():
    """A production profile cannot silently use the local fake adapters."""
    with pytest.raises(ValueError):
        NotificationEmailSender(
            lambda: EmailConfiguration("ses", SecretStr("synthetic")),
            lambda job: ("Subject", "Body"),
            profile="production",
            ses_client=Ses(),
        )
    with pytest.raises(ValueError):
        NotificationEmailSender(
            SsmNotificationConfiguration("/clip/test/email"),
            lambda job: ("Unreviewed subject", "Unreviewed body"),
            profile="production",
        )


def test_failed_refresh_never_uses_stale_provider_configuration():
    """Expired secrets are not silently reused when a refresh fails."""
    claim, recipient = fixture()
    time = [0.0]
    ses = Ses()

    def load():
        if time[0] >= 14400:
            raise RuntimeError("PRIVATE SECRET ERROR")
        return EmailConfiguration("ses", SecretStr("synthetic"))

    sender = NotificationEmailSender(
        load,
        lambda job: ("Subject", "Body"),
        profile="test",
        test_recipients=(recipient.email,),
        ses_client=ses,
        clock=lambda: time[0],
    )
    asyncio.run(sender(claim, recipient))
    time[0] = 14400
    with pytest.raises(NotificationDeliveryFailure) as error:
        asyncio.run(sender(claim, recipient))
    assert error.value.kind == "transient_failure" and "PRIVATE" not in str(error.value)
    assert len(ses.calls) == 1


def test_configuration_can_change_primary_without_recreating_sender():
    """A refreshed snapshot can switch provider order for future sends."""
    claim, recipient = fixture()
    time, selection = [0.0], ["ses"]
    ses, opener = Ses(), Opener()
    sender = NotificationEmailSender(
        lambda: EmailConfiguration(selection[0], SecretStr("synthetic")),
        lambda job: ("Subject", "Body"),
        profile="test",
        test_recipients=(recipient.email,),
        ses_client=ses,
        opener=opener,
        clock=lambda: time[0],
    )
    asyncio.run(sender(claim, recipient))
    selection[0], time[0] = "resend", 14400
    asyncio.run(sender(claim, recipient))
    assert len(ses.calls) == len(opener.calls) == 1
