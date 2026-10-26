"""Explicit one-message ECS smoke command; never installed as an HTTP endpoint.

Run only under a separately approved image/task/send plan. This module does not
activate an account, generate an OTP, access a database or start any service.
"""

from importlib import import_module
import json
import logging
import os
import signal
from types import FrameType
from typing import NoReturn

from app.core.config import load_settings
from app.domains.identity.email import SesEmailSender


def verify_runtime_role() -> None:
    """Require ECS task-role credentials and validate the signed caller identity.

    No static local profile/key may substitute for the approved application role.
    STS identity is checked in memory and is never emitted with session metadata.
    """
    if os.environ.get("AWS_EXECUTION_ENV") != "AWS_ECS_EC2":
        raise ValueError("ECS runtime required")
    if any(
        os.environ.get(key)
        for key in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_PROFILE",
            "AWS_DEFAULT_PROFILE",
            "AWS_SHARED_CREDENTIALS_FILE",
        )
    ):
        raise ValueError("Static credential overrides forbidden")
    sdk = import_module("boto3")
    config = import_module("botocore.config")
    session = sdk.Session()
    credentials = session.get_credentials()
    if credentials is None or credentials.method != "container-role":
        raise ValueError("Task-role credentials required")
    client = session.client(
        "sts",
        region_name="ap-south-1",
        config=config.Config(
            ignore_configured_endpoint_urls=True,
            connect_timeout=3,
            read_timeout=5,
            retries={"mode": "standard", "total_max_attempts": 1},
        ),
    )
    caller = client.get_caller_identity()
    prefix = "arn:aws:sts::335523638354:assumed-role/clip-shared-test-api-task/"
    if caller.get("Account") != "335523638354" or not caller.get("Arn", "").startswith(
        prefix
    ):
        raise ValueError("Unexpected runtime role")


def main() -> int:
    """Validate explicit approval/settings, then attempt exactly one submission.

    Output contains only fixed outcomes. Disable library logging during the run
    so SDK debugging cannot expose recipients, credentials or message content.
    Accepted means provider acceptance only; inbox receipt needs human evidence.
    """
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        if os.environ.get("CLIP_EMAIL_SMOKE_APPROVED") != "true":
            raise ValueError("Explicit smoke approval required")
        settings = load_settings()
        if (
            settings.environment != "test"
            or settings.email_provider != "ses"
            or len(settings.ses_test_recipients) != 1
        ):
            raise ValueError("Single controlled test recipient required")
        verify_runtime_role()
        sender = SesEmailSender(settings)
        sender.send(
            settings.ses_test_recipients[0],
            "CLIP email delivery test",
            "This is the approved CLIP email delivery test. No verification code or account action is included.",
        )
        print(json.dumps({"outcome": "submission_accepted"}))
        return 0
    except Exception:
        print(json.dumps({"outcome": "failed_or_uncertain"}))
        return 1
    finally:
        logging.disable(previous_logging)


def deadline_expired(signum: int, frame: FrameType | None) -> NoReturn:
    """Abort stalled credential/provider I/O without logging exception contents."""
    raise TimeoutError("Smoke deadline reached")


def run() -> int:
    """Bound the Linux ECS command to 45 seconds, including credential lookup."""
    previous = signal.signal(signal.SIGALRM, deadline_expired)
    signal.alarm(45)
    try:
        return main()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == "__main__":
    raise SystemExit(run())
