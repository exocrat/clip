"""Offline smoke-command denial, role and redaction checks; never sends email."""

import json
from types import SimpleNamespace

import pytest

from app.domains.identity import email_smoke

RECIPIENT = "controlled@example.invalid"


@pytest.fixture
def approved(monkeypatch):
    """Select one synthetic recipient without granting real AWS access."""
    monkeypatch.setenv("CLIP_EMAIL_SMOKE_APPROVED", "true")
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.setenv("CLIP_EMAIL_PROVIDER", "ses")
    monkeypatch.setenv("CLIP_SES_TEST_RECIPIENTS", json.dumps([RECIPIENT]))
    monkeypatch.setattr(email_smoke, "verify_runtime_role", lambda: None)


@pytest.mark.parametrize("change", ["approval", "production", "multiple"])
def test_invalid_controls_do_not_construct_sender(
    approved, monkeypatch, capsys, change
):
    def forbidden(*args):
        pytest.fail("Sender constructed before guards passed")

    monkeypatch.setattr(email_smoke, "SesEmailSender", forbidden)
    if change == "approval":
        monkeypatch.delenv("CLIP_EMAIL_SMOKE_APPROVED")
    elif change == "production":
        monkeypatch.setenv("CLIP_ENVIRONMENT", "production")
    else:
        monkeypatch.setenv(
            "CLIP_SES_TEST_RECIPIENTS", json.dumps([RECIPIENT, "other@example.invalid"])
        )
    assert email_smoke.main() == 1
    assert capsys.readouterr().out == '{"outcome": "failed_or_uncertain"}\n'


def test_one_submission_and_safe_output(approved, monkeypatch, capsys):
    calls = []

    class Sender:
        def __init__(self, settings):
            pass

        def send(self, *args):
            calls.append(args)

    monkeypatch.setattr(email_smoke, "SesEmailSender", Sender)
    assert email_smoke.run() == 0
    assert len(calls) == 1 and calls[0][0] == RECIPIENT
    assert capsys.readouterr().out == '{"outcome": "submission_accepted"}\n'


def test_failure_is_redacted_and_never_retried(approved, monkeypatch, capsys):
    calls = []

    class Sender:
        def __init__(self, settings):
            pass

        def send(self, *args):
            calls.append(args)
            raise RuntimeError("PRIVATE_PROVIDER_PAYLOAD")

    monkeypatch.setattr(email_smoke, "SesEmailSender", Sender)
    assert email_smoke.main() == 1
    assert len(calls) == 1
    output = capsys.readouterr()
    assert "PRIVATE" not in output.out + output.err
    assert RECIPIENT not in output.out + output.err


@pytest.mark.parametrize(
    "method,arn",
    [
        (
            "env",
            "arn:aws:sts::335523638354:assumed-role/clip-shared-test-api-task/test",
        ),
        ("container-role", "arn:aws:sts::335523638354:assumed-role/other-role/test"),
    ],
)
def test_runtime_requires_actual_task_role(monkeypatch, method, arn):
    monkeypatch.setenv("AWS_EXECUTION_ENV", "AWS_ECS_EC2")
    session = SimpleNamespace(
        get_credentials=lambda: SimpleNamespace(method=method),
        client=lambda *args, **kwargs: SimpleNamespace(
            get_caller_identity=lambda: {
                "Account": "335523638354",
                "Arn": arn,
            }
        ),
    )
    real_import = email_smoke.import_module
    monkeypatch.setattr(
        email_smoke,
        "import_module",
        lambda name: (
            SimpleNamespace(Session=lambda: session)
            if name == "boto3"
            else real_import(name)
        ),
    )
    with pytest.raises(ValueError):
        email_smoke.verify_runtime_role()


def test_local_runtime_is_refused():
    with pytest.raises(ValueError):
        email_smoke.verify_runtime_role()


def test_expected_role_is_accepted_offline(monkeypatch):
    """The strict identity guard permits its intended signed role response."""
    monkeypatch.setenv("AWS_EXECUTION_ENV", "AWS_ECS_EC2")
    session = SimpleNamespace(
        get_credentials=lambda: SimpleNamespace(method="container-role"),
        client=lambda *args, **kwargs: SimpleNamespace(
            get_caller_identity=lambda: {
                "Account": "335523638354",
                "Arn": "arn:aws:sts::335523638354:assumed-role/clip-shared-test-api-task/test",
            }
        ),
    )
    real_import = email_smoke.import_module
    monkeypatch.setattr(
        email_smoke,
        "import_module",
        lambda name: (
            SimpleNamespace(Session=lambda: session)
            if name == "boto3"
            else real_import(name)
        ),
    )
    email_smoke.verify_runtime_role()
