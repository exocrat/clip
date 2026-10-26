"""No-send tests of safe SDK denial-resource/reason classification."""

import importlib.util
import json
from pathlib import Path

from botocore.exceptions import ClientError
import pytest

WRAPPER = (
    Path(__file__).resolve().parents[5]
    / "docs/evaluation/identity/id-01-step-2/runtime_authorization_diagnostic.py"
)
spec = importlib.util.spec_from_file_location("authorization_diagnostic", WRAPPER)
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
RECIPIENT = "private@example.invalid"
PREFIX = "arn:aws:ses:ap-south-1:335523638354:"


@pytest.mark.parametrize(
    "resource,expected",
    [
        ("identity/clip-iisc.site", "sender_domain"),
        ("identity/no-reply@clip-iisc.site", "sender_address"),
        ("identity/" + RECIPIENT, "controlled_recipient"),
        ("configuration-set/PRIVATE", "other_resource"),
    ],
)
@pytest.mark.parametrize(
    "reason,expected_reason",
    [
        ("because no identity-based policy allows it", "missing_identity_allow"),
        ("with an explicit deny in a service control policy", "organization_policy"),
    ],
)
def test_real_sender_chained_error_remains_private(
    monkeypatch, capsys, resource, expected, reason, expected_reason
):
    for key, value in {
        "CLIP_EMAIL_SMOKE_APPROVED": "true",
        "CLIP_ENVIRONMENT": "test",
        "CLIP_EMAIL_PROVIDER": "ses",
        "CLIP_SES_TEST_RECIPIENTS": json.dumps([RECIPIENT]),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(diagnostic, "verify_runtime_role", lambda: None)
    calls = []

    class Client:
        def send_email(self, **kwargs):
            calls.append(kwargs)
            raise ClientError(
                {
                    "Error": {
                        "Code": "AccessDeniedException",
                        "Message": f"PRIVATE is not authorized on resource `{PREFIX}{resource}` {reason}",
                    }
                },
                "SendEmail",
            )

    monkeypatch.setattr(
        diagnostic.SesEmailSender, "_make_client", lambda self: Client()
    )
    assert diagnostic.run() == 1
    output = capsys.readouterr()
    assert (
        output.err == "" and "PRIVATE" not in output.out and RECIPIENT not in output.out
    )
    result = json.loads(output.out)
    assert (
        result["resource_class"] == expected
        and result["denial_reason"] == expected_reason
    )
    assert len(calls) == 1


def test_unknown_message_does_not_escape():
    error = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "PRIVATE"}}, "SendEmail"
    )
    assert diagnostic.authorization_detail(error, RECIPIENT) == {
        "resource_class": "unclassified",
        "denial_reason": "unclassified",
    }
