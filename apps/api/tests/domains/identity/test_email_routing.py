"""Offline real-adapter boundaries and bounded failover; no provider/network calls."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import json
from unittest.mock import Mock
from urllib.request import Request

from pydantic import SecretStr
import pytest

from app.domains.identity.email import EmailUnavailable
from app.domains.identity.email_routing import (
    EmailRoute,
    REFRESH_SECONDS,
    RefreshingEmailSender,
)
from app.domains.identity.resend_email import NoEmailRedirects, ResendEmailSender
from app.domains.identity.temporary_delivery import OtpDelivery

RECIPIENT = "controlled@example.invalid"


class Sender:
    """Capture synthetic arguments, optionally failing after apparent acceptance."""

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def send(self, *args):
        self.calls.append(args)
        if self.fail:
            raise TimeoutError("PRIVATE_PROVIDER_DATA")


@pytest.mark.parametrize("primary", ["resend", "ses"])
@pytest.mark.parametrize(
    "first_fails,second_fails", [(False, False), (True, False), (True, True)]
)
def test_exact_order_and_at_most_two_attempts(primary, first_fails, second_fails):
    first, second = Sender(first_fails), Sender(second_fails)
    route = (
        EmailRoute(primary, first, second)
        if primary == "resend"
        else EmailRoute(primary, second, first)
    )
    sender = RefreshingEmailSender(lambda: route)
    args = (RECIPIENT, "Synthetic subject", "SYNTHETIC_BODY")
    if first_fails and second_fails:
        with pytest.raises(EmailUnavailable, match="unavailable or uncertain") as error:
            sender.send(*args)
        assert "PRIVATE" not in str(error.value)
    else:
        sender.send(*args)
    assert first.calls == [args]
    assert second.calls == ([args] if first_fails else [])


def test_four_hour_refresh_changes_order_and_credentials_atomically():
    now = [0.0]
    old_resend, old_ses, new_resend, new_ses = (Sender() for _ in range(4))
    load = Mock(
        side_effect=[
            EmailRoute("resend", old_resend, old_ses),
            EmailRoute("ses", new_resend, new_ses),
        ]
    )
    sender = RefreshingEmailSender(load, lambda: now[0])
    assert load.call_count == 0
    sender.send(RECIPIENT, "Test", "Body")
    now[0] = REFRESH_SECONDS - 0.001
    sender.send(RECIPIENT, "Test", "Body")
    assert load.call_count == 1
    now[0] = REFRESH_SECONDS
    sender.send(RECIPIENT, "Test", "Body")
    assert load.call_count == 2
    assert len(old_resend.calls) == 2 and len(new_ses.calls) == 1
    assert old_ses.calls == new_resend.calls == []


@pytest.mark.parametrize("bad_result", [None, "bad", {"primary": "resend"}])
def test_invalid_initial_configuration_never_sends(bad_result):
    sender = RefreshingEmailSender(lambda: bad_result)
    with pytest.raises(EmailUnavailable, match="configuration unavailable"):
        sender.send(RECIPIENT, "Test", "Body")


def test_expired_configuration_is_not_used_after_refresh_failure():
    now = [0.0]
    resend, ses = Sender(), Sender()
    load = Mock(
        side_effect=[EmailRoute("resend", resend, ses), RuntimeError("PRIVATE_SECRET")]
    )
    sender = RefreshingEmailSender(load, lambda: now[0])
    sender.send(RECIPIENT, "Test", "Body")
    now[0] = REFRESH_SECONDS
    with pytest.raises(EmailUnavailable) as error:
        sender.send(RECIPIENT, "Test", "Body")
    assert "PRIVATE" not in str(error.value)
    assert len(resend.calls) == 1 and ses.calls == []


def test_parallel_initial_sends_load_one_snapshot():
    load = Mock(return_value=EmailRoute("resend", Sender(), Sender()))
    sender = RefreshingEmailSender(load)
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda _: sender.send(RECIPIENT, "Test", "Body"), range(32)))
    assert load.call_count == 1


@pytest.mark.parametrize("primary", ["fake", "", "RESEND"])
def test_invalid_selector_is_rejected(primary):
    with pytest.raises(ValueError):
        EmailRoute(primary, Sender(), Sender())


def test_same_object_cannot_be_both_providers():
    sender = Sender()
    with pytest.raises(ValueError):
        EmailRoute("resend", sender, sender)


@pytest.mark.parametrize("both_fail", [False, True])
def test_otp_ticket_consumed_once_across_fallback_pair(both_fail):
    now = datetime(2026, 10, 24, tzinfo=UTC)
    first, second = Sender(True), Sender(both_fail)
    ticket = OtpDelivery(
        RECIPIENT, "123456", "initial_verification", now + timedelta(minutes=10)
    )
    sender = RefreshingEmailSender(lambda: EmailRoute("resend", first, second))
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(lambda _: ticket.dispatch(sender, now=now), range(32)))
    assert sum(outcomes) == (0 if both_fail else 1)
    assert len(first.calls) == len(second.calls) == 1
    assert first.calls == second.calls
    assert ticket._email is None and ticket._code is None


def response(status=200, raw=b'{"id":"synthetic-id"}'):
    """Bounded HTTP response substitute, with no real connection."""
    result = Mock()
    result.status = status
    result.read.return_value = raw
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    return result


def adapter(monkeypatch, result=None, error=None):
    opener = Mock()
    opener.open.return_value = result or response()
    opener.open.side_effect = error
    monkeypatch.setattr(
        "app.domains.identity.resend_email.build_opener", lambda *args: opener
    )
    sender = ResendEmailSender(SecretStr("synthetic-key"), (RECIPIENT,))
    return sender, opener


def test_resend_fixed_request_and_no_construction_io(monkeypatch):
    sender, opener = adapter(monkeypatch)
    opener.open.assert_not_called()
    sender.send(RECIPIENT, "Test", "Synthetic body")
    assert opener.open.call_count == 1
    request = opener.open.call_args.args[0]
    assert request.full_url == "https://api.resend.com/emails"
    assert request.method == "POST"
    assert request.get_header("User-agent") == "CLIP-Identity/0.1"
    assert request.get_header("Authorization") == "Bearer synthetic-key"
    assert json.loads(request.data) == {
        "from": "verify@clip-iisc.site",
        "to": [RECIPIENT],
        "subject": "Test",
        "text": "Synthetic body",
    }
    assert opener.open.call_args.kwargs == {"timeout": 8}


@pytest.mark.parametrize(
    "status,raw",
    [
        (429, b"PRIVATE"),
        (503, b"PRIVATE"),
        (200, b"bad"),
        (200, b"[]"),
        (200, b'{"id":""}'),
        (200, b"x" * 4097),
    ],
)
def test_resend_errors_are_private_and_never_retry(monkeypatch, status, raw):
    sender, opener = adapter(monkeypatch, response(status, raw))
    with pytest.raises(EmailUnavailable) as error:
        sender.send(RECIPIENT, "Test", "Body")
    assert "PRIVATE" not in str(error.value)
    assert error.value.__suppress_context__
    assert opener.open.call_count == 1


def test_resend_timeout_is_private_without_retry(monkeypatch):
    sender, opener = adapter(monkeypatch, error=TimeoutError("PRIVATE_KEY_BODY"))
    with pytest.raises(EmailUnavailable) as error:
        sender.send(RECIPIENT, "Test", "Body")
    assert "PRIVATE" not in str(error.value)
    assert opener.open.call_count == 1


@pytest.mark.parametrize(
    "recipient,subject,body",
    [
        ("other@example.invalid", "Test", "Body"),
        (RECIPIENT, "Bad\r\nBcc:x", "Body"),
        (RECIPIENT, "", "Body"),
        (RECIPIENT, "Test", "x" * 8193),
    ],
)
def test_resend_unsafe_envelope_never_leaves_process(
    monkeypatch, recipient, subject, body
):
    sender, opener = adapter(monkeypatch)
    with pytest.raises(EmailUnavailable):
        sender.send(recipient, subject, body)
    opener.open.assert_not_called()


@pytest.mark.parametrize(
    "key,recipients",
    [
        ("", (RECIPIENT,)),
        ("bad\nkey", (RECIPIENT,)),
        ("synthetic", ()),
        ("synthetic", (RECIPIENT,) * 6),
    ],
)
def test_invalid_resend_configuration(key, recipients):
    with pytest.raises(EmailUnavailable):
        ResendEmailSender(SecretStr(key), recipients)


def test_redirects_are_refused():
    assert (
        NoEmailRedirects().redirect_request(
            Request("https://api.resend.com/emails"),
            None,
            307,
            "",
            {},
            "https://other.example.invalid",
        )
        is None
    )


def test_ssm_snapshot_order_key_refresh_and_no_construction_io(monkeypatch):
    from app.domains.identity.email_configuration import SsmEmailRouteLoader

    monkeypatch.setattr(
        "app.domains.identity.resend_email.build_opener", lambda *args: Mock()
    )
    client = Mock()
    client.get_parameter.return_value = {
        "Parameter": {
            "Type": "SecureString",
            "Value": json.dumps(
                {"version": 1, "primary": "resend", "resend_api_key": "synthetic-key"}
            ),
        }
    }
    loader = SsmEmailRouteLoader(
        "/clip/test/identity/email-delivery", (RECIPIENT,), Sender(), client
    )
    client.get_parameter.assert_not_called()
    route = loader()
    assert route.primary == "resend"
    client.get_parameter.assert_called_once_with(
        Name="/clip/test/identity/email-delivery", WithDecryption=True
    )
    assert "synthetic-key" not in repr(route)
    assert route.resend._key.get_secret_value() == "synthetic-key"


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        "[]",
        '{"version":true,"primary":"ses","resend_api_key":"synthetic"}',
        '{"version":1,"primary":"fake","resend_api_key":"synthetic"}',
        '{"version":1,"primary":"ses","resend_api_key":""}',
        "x" * 4097,
    ],
)
def test_ssm_invalid_private_configuration_is_redacted(value):
    from app.domains.identity.email_configuration import SsmEmailRouteLoader

    client = Mock()
    client.get_parameter.return_value = {
        "Parameter": {"Type": "SecureString", "Value": value}
    }
    loader = SsmEmailRouteLoader(
        "/clip/test/identity/email-delivery", (RECIPIENT,), Sender(), client
    )
    with pytest.raises(EmailUnavailable, match="configuration unavailable"):
        loader()


def test_ssm_requires_securestring_and_redacts_read_failure():
    from app.domains.identity.email_configuration import SsmEmailRouteLoader

    client = Mock()
    client.get_parameter.return_value = {
        "Parameter": {"Type": "String", "Value": "PRIVATE"}
    }
    loader = SsmEmailRouteLoader(
        "/clip/test/identity/email-delivery", (RECIPIENT,), Sender(), client
    )
    with pytest.raises(EmailUnavailable) as error:
        loader()
    assert "PRIVATE" not in str(error.value)
    client.get_parameter.side_effect = RuntimeError("PRIVATE_KEY")
    with pytest.raises(EmailUnavailable) as error:
        loader()
    assert "PRIVATE" not in str(error.value)


def test_ssm_actual_sdk_shape_without_network(monkeypatch):
    from botocore.stub import Stubber
    from app.domains.identity.email_configuration import SsmEmailRouteLoader

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "SYNTHETIC_TEST_KEY")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SYNTHETIC_TEST_SECRET")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://override.example.invalid")
    client = SsmEmailRouteLoader._make_client()
    assert client.meta.endpoint_url == "https://ssm.ap-south-1.amazonaws.com"
    assert client.meta.config.retries["total_max_attempts"] == 1
    with Stubber(client) as stubber:
        stubber.add_response(
            "get_parameter",
            {
                "Parameter": {
                    "Name": "/clip/test/identity/email-delivery",
                    "Type": "SecureString",
                    "Value": json.dumps(
                        {
                            "version": 1,
                            "primary": "ses",
                            "resend_api_key": "synthetic-key",
                        }
                    ),
                }
            },
            {"Name": "/clip/test/identity/email-delivery", "WithDecryption": True},
        )
        route = SsmEmailRouteLoader(
            "/clip/test/identity/email-delivery", (RECIPIENT,), Sender(), client
        )()
        assert route.primary == "ses"
        stubber.assert_no_pending_responses()
