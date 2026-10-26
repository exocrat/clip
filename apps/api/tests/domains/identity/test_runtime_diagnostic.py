"""Exercise the exact reviewed command override offline, without AWS access."""

import importlib.util
import json
from pathlib import Path

from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    MissingDependencyException,
)
import pytest

from app.domains.identity.email import EmailUnavailable

WRAPPER = (
    Path(__file__).resolve().parents[5]
    / "docs/evaluation/identity/id-01-step-2/runtime_diagnostic.py"
)
spec = importlib.util.spec_from_file_location("runtime_diagnostic", WRAPPER)
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
PRIVATE = "PRIVATE_RECIPIENT_CONTENT_CREDENTIALS"


@pytest.fixture
def approved(monkeypatch):
    """Use synthetic settings and fail if any unexpected real client is built."""
    monkeypatch.setenv("CLIP_EMAIL_SMOKE_APPROVED", "true")
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.setenv("CLIP_EMAIL_PROVIDER", "ses")
    monkeypatch.setenv("CLIP_SES_TEST_RECIPIENTS", '["controlled@example.invalid"]')
    monkeypatch.setattr(diagnostic, "verify_runtime_role", lambda: None)
    monkeypatch.setattr(
        diagnostic.SesEmailSender,
        "_make_client",
        lambda self: pytest.fail("Unexpected network client"),
    )


@pytest.mark.parametrize(
    "error,category,code",
    [
        (
            ClientError(
                {"Error": {"Code": "AccessDeniedException", "Message": PRIVATE}},
                "SendEmail",
            ),
            "permission_denied",
            "AccessDeniedException",
        ),
        (
            ClientError({"Error": {"Code": PRIVATE, "Message": PRIVATE}}, "SendEmail"),
            "unclassified",
            "unclassified",
        ),
        (EndpointConnectionError(endpoint_url=PRIVATE), "network", "unclassified"),
        (TimeoutError(PRIVATE), "timeout", "unclassified"),
        (MissingDependencyException(msg=PRIVATE), "sdk_configuration", "unclassified"),
    ],
)
def test_chained_failure_is_classified_redacted_and_not_retried(
    approved, monkeypatch, capsys, error, category, code
):
    """The real sender wraps private SDK failures; diagnostics inspect its context."""
    calls = []

    class Client:
        def send_email(self, **kwargs):
            calls.append(kwargs)
            raise error

    monkeypatch.setattr(
        diagnostic.SesEmailSender, "_make_client", lambda self: Client()
    )
    assert diagnostic.run() == 1
    output = capsys.readouterr()
    assert output.err == ""
    assert PRIVATE not in output.out and "controlled@" not in output.out
    assert len(calls) == 1
    assert json.loads(output.out) == {
        "outcome": "failed_or_uncertain",
        "stage": "ses_submission",
        "category": category,
        "error_code": code,
    }


@pytest.mark.parametrize("stage", ["settings", "task_role", "ses_client"])
def test_early_failure_never_sends(approved, monkeypatch, capsys, stage):
    def fail(*args):
        raise RuntimeError(PRIVATE)

    if stage == "settings":
        monkeypatch.delenv("CLIP_EMAIL_SMOKE_APPROVED")
    elif stage == "task_role":
        monkeypatch.setattr(diagnostic, "verify_runtime_role", fail)
    else:
        monkeypatch.setattr(diagnostic.SesEmailSender, "_make_client", fail)
    assert diagnostic.run() == 1
    output = capsys.readouterr()
    assert PRIVATE not in output.out + output.err
    assert json.loads(output.out)["stage"] == stage


def test_success_uses_real_sender_once(approved, monkeypatch, capsys):
    calls = []

    class Client:
        def send_email(self, **kwargs):
            calls.append(kwargs)
            return {"MessageId": PRIVATE}

    monkeypatch.setattr(
        diagnostic.SesEmailSender, "_make_client", lambda self: Client()
    )
    assert diagnostic.run() == 0
    assert len(calls) == 1
    assert json.loads(capsys.readouterr().out) == {
        "outcome": "submission_accepted",
        "stage": "complete",
    }


def test_context_cycle_is_bounded():
    error = EmailUnavailable(PRIVATE)
    error.__context__ = error
    assert diagnostic.classify(error) == ("unclassified", "unclassified")
