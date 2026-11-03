"""Offline safety checks; these tests never construct a real AWS client."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.domains.identity.email import EmailUnavailable, SesEmailSender

RECIPIENT = "controlled@example.invalid"


class RecordingClient:
    """Record dispatch shape or simulate an uncertain provider failure."""

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def send_email(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("PRIVATE_PROVIDER_PAYLOAD")
        return {"MessageId": "synthetic-accepted-id"}


def settings(**changes):
    """Build explicit test-only settings independent of live credentials."""
    return Settings(
        environment="test",
        email_provider="ses",
        ses_test_recipients=(RECIPIENT,),
        **changes,
    )


def test_single_recipient_submission():
    client = RecordingClient()
    sender = SesEmailSender(settings(), client)
    sender.send(RECIPIENT, "CLIP verification", "SYNTHETIC_BODY")
    assert len(client.calls) == 1
    assert client.calls[0]["Destination"] == {"ToAddresses": [RECIPIENT]}
    assert client.calls[0]["FromEmailAddress"] == "verify@clip-iisc.site"


def test_denied_destination_never_calls_provider():
    client = RecordingClient()
    with pytest.raises(EmailUnavailable):
        SesEmailSender(settings(), client).send("other@example.invalid", "Test", "Body")
    assert client.calls == []


def test_explicit_hosted_auth_accepts_unlisted_canonical_recipient():
    """SES production access is useful only when the hosted app permits its users."""
    from pydantic import SecretStr

    configured = Settings(
        environment="test",
        identity_provider="microsoft",
        email_provider="dual",
        identity_runtime_enabled=True,
        identity_browser_origins=("https://clip-iisc.site",),
        database_url=SecretStr("postgresql://synthetic@db.invalid/clip_test"),
        ses_test_recipients=(RECIPIENT,),
    )
    client = RecordingClient()
    sender = SesEmailSender(configured, client)
    sender.send("other@example.invalid", "CLIP verification", "SYNTHETIC_BODY")
    assert len(client.calls) == 1
    with pytest.raises(EmailUnavailable):
        sender.send(
            "other@example.invalid\r\nBcc: injected",
            "CLIP verification",
            "SYNTHETIC_BODY",
        )
    assert len(client.calls) == 1


def test_uncertain_failure_is_redacted_without_retry():
    client = RecordingClient(fail=True)
    with pytest.raises(EmailUnavailable) as captured:
        SesEmailSender(settings(), client).send(RECIPIENT, "Test", "PRIVATE_BODY")
    assert len(client.calls) == 1
    assert "PRIVATE" not in str(captured.value)
    assert captured.value.__suppress_context__


@pytest.mark.parametrize(
    "subject,body",
    [("Test\r\nBcc: injected", "Body"), ("Test", "x" * 8193), ("", "Body")],
)
def test_unsafe_content_never_calls_provider(subject, body):
    client = RecordingClient()
    with pytest.raises(EmailUnavailable):
        SesEmailSender(settings(), client).send(RECIPIENT, subject, body)
    assert client.calls == []


def test_ses_requires_allowlist_and_rejects_production():
    with pytest.raises(ValidationError):
        Settings(email_provider="ses", ses_test_recipients=())
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            email_provider="ses",
            ses_test_recipients=(RECIPIENT,),
        )


def test_disabled_sender_cannot_be_constructed():
    with pytest.raises(EmailUnavailable):
        SesEmailSender(Settings(email_provider="disabled"), RecordingClient())


def test_real_sdk_shape_and_timeouts_without_network(monkeypatch):
    """Validate boto3 request serialization using botocore's offline stubber."""
    from botocore.stub import Stubber

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "SYNTHETIC_TEST_KEY")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SYNTHETIC_TEST_SECRET")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://override.example.invalid")
    sender = SesEmailSender(settings())
    client = sender._make_client()
    assert client.meta.endpoint_url == "https://email.ap-south-1.amazonaws.com"
    assert client.meta.config.connect_timeout == 3
    assert client.meta.config.read_timeout == 5
    assert client.meta.config.retries["total_max_attempts"] == 1
    with Stubber(client) as stubber:
        stubber.add_response(
            "send_email",
            {"MessageId": "synthetic-accepted-id"},
            {
                "FromEmailAddress": "verify@clip-iisc.site",
                "Destination": {"ToAddresses": [RECIPIENT]},
                "Content": {
                    "Simple": {
                        "Subject": {"Data": "Test", "Charset": "UTF-8"},
                        "Body": {
                            "Text": {"Data": "SYNTHETIC_BODY", "Charset": "UTF-8"}
                        },
                    }
                },
            },
        )
        sender._client = client
        sender.send(RECIPIENT, "Test", "SYNTHETIC_BODY")
        stubber.assert_no_pending_responses()
