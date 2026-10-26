"""Reviewed command override for the existing image; import alone never sends.

No raw exceptions, request/response payloads or destinations leave this wrapper.
Use only under a separately approved one-task/one-send ECS runtime plan.
"""

import json
import logging
import os
import signal

from botocore import exceptions as sdk_errors

from app.core.config import load_settings
from app.domains.identity.email import SesEmailSender
from app.domains.identity.email_smoke import deadline_expired, verify_runtime_role

# Only these literal service codes can be emitted; unknown codes stay private.
SERVICE_CODES = {
    "AccessDenied": "permission_denied",
    "AccessDeniedException": "permission_denied",
    "MessageRejected": "message_rejected",
    "MailFromDomainNotVerifiedException": "message_rejected",
    "NotFoundException": "provider_configuration",
    "BadRequestException": "provider_configuration",
    "AccountSuspendedException": "sending_disabled",
    "SendingPausedException": "sending_disabled",
    "TooManyRequestsException": "rate_limited",
    "LimitExceededException": "rate_limited",
}


def classify(error):
    """Inspect bounded exception context, returning only fixed public categories.

    The sender suppresses exception display but retains SDK context in memory.
    Never stringify an exception or include arbitrary SDK error-code text.
    """
    for _ in range(5):
        if isinstance(error, sdk_errors.ClientError):
            code = error.response.get("Error", {}).get("Code")
            if isinstance(code, str) and code in SERVICE_CODES:
                return SERVICE_CODES[code], code
            return "unclassified", "unclassified"
        if isinstance(
            error,
            (sdk_errors.ConnectTimeoutError, sdk_errors.ReadTimeoutError, TimeoutError),
        ):
            return "timeout", "unclassified"
        if isinstance(
            error,
            (
                sdk_errors.EndpointConnectionError,
                sdk_errors.ConnectionClosedError,
                sdk_errors.SSLError,
            ),
        ):
            return "network", "unclassified"
        if isinstance(
            error,
            (
                sdk_errors.NoCredentialsError,
                sdk_errors.PartialCredentialsError,
                sdk_errors.CredentialRetrievalError,
            ),
        ):
            return "credentials", "unclassified"
        if isinstance(
            error,
            (
                sdk_errors.ParamValidationError,
                sdk_errors.MissingDependencyException,
                sdk_errors.NoRegionError,
            ),
        ):
            return "sdk_configuration", "unclassified"
        error = error.__context__
        if error is None:
            break
    return "unclassified", "unclassified"


def main():
    """Validate unchanged guards, construct one client and invoke sender once.

    Stage means the current operation, not proof an SES request reached AWS.
    A generic failure remains uncertain and must never trigger an automatic retry.
    """
    stage = "settings"
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        if os.environ.get("CLIP_EMAIL_SMOKE_APPROVED") != "true":
            raise ValueError("Explicit approval required")
        settings = load_settings()
        if (
            settings.environment != "test"
            or settings.email_provider != "ses"
            or len(settings.ses_test_recipients) != 1
        ):
            raise ValueError("Single controlled test recipient required")
        stage = "task_role"
        verify_runtime_role()
        stage = "ses_client"
        sender = SesEmailSender(settings)
        # Exercise the image's actual client factory, then reuse that exact client.
        client = sender._make_client()
        sender = SesEmailSender(settings, client=client)
        stage = "ses_submission"
        sender.send(
            settings.ses_test_recipients[0],
            "CLIP email delivery test",
            "This is the approved CLIP email delivery test. No verification code or account action is included.",
        )
        print(json.dumps({"outcome": "submission_accepted", "stage": "complete"}))
        return 0
    except Exception as error:
        category, code = classify(error)
        print(
            json.dumps(
                {
                    "outcome": "failed_or_uncertain",
                    "stage": stage,
                    "category": category,
                    "error_code": code,
                }
            )
        )
        return 1
    finally:
        logging.disable(previous_logging)


def run():
    """Apply the existing 45-second Linux deadline and restore process state."""
    previous_handler = signal.signal(signal.SIGALRM, deadline_expired)
    signal.alarm(45)
    try:
        return main()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


if __name__ == "__main__":
    raise SystemExit(run())
