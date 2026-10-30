"""Explicit SES/Resend notification delivery; no I/O until a batch sends.

The loader reads an approved SSM SecureString only when explicitly invoked.
This module installs no scheduler, provider, credential or test recipient.
"""

import asyncio
from dataclasses import dataclass, field
from importlib import import_module
import json
import re
from threading import Lock
from time import monotonic
from typing import Callable, Literal
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from pydantic import SecretStr

from app.contracts.domain_types import NotificationClaim, NotificationRecipient
from app.domains.conversations.notifications.provider import NotificationDeliveryFailure
from app.domains.conversations.notifications.templates import render_notification

SENDER = "updates@clip-iisc.site"
REFRESH_SECONDS = 4 * 60 * 60


@dataclass(frozen=True)
class EmailConfiguration:
    """One atomic private provider/key snapshot loaded from the secret manager."""

    primary: Literal["ses", "resend"]
    resend_api_key: SecretStr = field(repr=False)

    def __post_init__(self) -> None:
        """Reject invalid selectors and keys without exposing their contents."""
        value = self.resend_api_key.get_secret_value()
        if (
            self.primary not in ("ses", "resend")
            or not 1 <= len(value) <= 512
            or not value.isascii()
            or any(not 33 <= ord(c) <= 126 for c in value)
        ):
            raise ValueError("Invalid notification email configuration")


def _client(service: str):
    """Create an AWS client with fixed region, TLS endpoints and no SDK retries."""
    boto3 = import_module("boto3")
    config = import_module("botocore.config")
    return boto3.client(
        service,
        region_name="ap-south-1",
        config=config.Config(
            ignore_configured_endpoint_urls=True,
            connect_timeout=3,
            read_timeout=5,
            retries={"mode": "standard", "total_max_attempts": 1},
        ),
    )


class SsmNotificationConfiguration:
    """Read the existing versioned Identity email-route parameter on demand."""

    def __init__(self, parameter: str, client=None) -> None:
        """Bind one explicit project parameter without reading it."""
        if not re.fullmatch(r"/clip/[a-zA-Z0-9_/-]{1,250}", parameter):
            raise ValueError("Explicit project email parameter required")
        self._parameter, self._client = parameter, client

    def __call__(self) -> EmailConfiguration:
        """Load one complete secret version; all failures are safely redacted."""
        try:
            response = (self._client or _client("ssm")).get_parameter(
                Name=self._parameter, WithDecryption=True
            )
            row = response["Parameter"]
            if (
                row["Type"] != "SecureString"
                or not isinstance(row["Value"], str)
                or len(row["Value"].encode()) > 4096
            ):
                raise ValueError
            value = json.loads(row["Value"])
            if (
                not isinstance(value, dict)
                or set(value) != {"version", "primary", "resend_api_key"}
                or type(value["version"]) is not int
                or value["version"] != 1
                or not isinstance(value["resend_api_key"], str)
            ):
                raise ValueError
            return EmailConfiguration(
                value["primary"], SecretStr(value["resend_api_key"])
            )
        except Exception:
            raise NotificationDeliveryFailure("transient_failure") from None


class NoRedirects(HTTPRedirectHandler):
    """Never forward credentials or message data to another HTTP endpoint."""

    def redirect_request(self, *args, **kwargs):
        return None


class NotificationEmailSender:
    """Refresh routes lazily and make at most one attempt per real provider.

    Trusted composition supplies a renderer and an explicit delivery profile.
    Test profiles enforce the allowlist unless explicitly configured to send
    to eligible unlisted accounts; production remains independently guarded.
    """

    def __init__(
        self,
        load: Callable[[], EmailConfiguration],
        render: Callable,
        *,
        profile: Literal["test", "production"],
        test_recipients: tuple[str, ...] = (),
        allow_unlisted_recipients: bool = False,
        ses_client=None,
        opener=None,
        clock: Callable[[], float] = monotonic,
    ):
        """Validate safe delivery profile without touching providers or secrets."""
        if (
            profile not in ("test", "production")
            or type(allow_unlisted_recipients) is not bool
            or (profile == "production" and allow_unlisted_recipients)
            or (profile == "test" and not 1 <= len(test_recipients) <= 5)
            or (
                profile == "production"
                and (
                    test_recipients
                    or ses_client is not None
                    or opener is not None
                    or not isinstance(load, SsmNotificationConfiguration)
                    or load._client is not None
                    or render is not render_notification
                )
            )
        ):
            raise ValueError("Explicit notification delivery profile required")
        self._load, self._render, self._profile = load, render, profile
        self._recipients = frozenset(test_recipients)
        self._allow_unlisted_recipients = allow_unlisted_recipients
        self._ses, self._opener, self._clock = ses_client, opener, clock
        self._lock, self._configuration, self._expires = Lock(), None, 0.0

    def _snapshot(self) -> EmailConfiguration:
        """Refresh once per process; a failed refresh never uses stale secrets."""
        with self._lock:
            if self._configuration is not None and self._clock() < self._expires:
                return self._configuration
            try:
                value = self._load()
                if not isinstance(value, EmailConfiguration):
                    raise ValueError
            except Exception:
                raise NotificationDeliveryFailure("transient_failure") from None
            self._configuration, self._expires = value, self._clock() + REFRESH_SECONDS
            return value

    def _ses_send(self, recipient: str, subject: str, body: str) -> None:
        """Submit one UTF-8 email with the task role; never log SDK responses."""
        response = (self._ses or _client("sesv2")).send_email(
            FromEmailAddress=SENDER,
            Destination={"ToAddresses": [recipient]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                }
            },
        )
        if not isinstance(response.get("MessageId"), str) or not response["MessageId"]:
            raise ValueError

    def _resend_send(
        self, key: SecretStr, recipient: str, subject: str, body: str
    ) -> None:
        """Submit once to Resend's fixed TLS endpoint without redirect or proxy."""
        opener = self._opener or build_opener(
            ProxyHandler({}), HTTPSHandler(), NoRedirects()
        )
        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps(
                {"from": SENDER, "to": [recipient], "subject": subject, "text": body}
            ).encode(),
            headers={
                "Authorization": "Bearer " + key.get_secret_value(),
                "Content-Type": "application/json",
                "User-Agent": "CLIP-Notifications/0.1",
            },
            method="POST",
        )
        with opener.open(request, timeout=8) as response:
            if response.status != 200:
                raise ValueError
            raw = response.read(4097)
            if len(raw) > 4096:
                raise ValueError
            data = json.loads(raw)
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("id"), str)
                or not 1 <= len(data["id"]) <= 128
            ):
                raise ValueError

    def _send(self, claim: NotificationClaim, recipient: NotificationRecipient) -> None:
        """Render minimal text and try the configured primary then alternate once."""
        if claim.recipient_id != recipient.recipient_id or (
            self._profile == "test"
            and not self._allow_unlisted_recipients
            and recipient.email not in self._recipients
        ):
            raise NotificationDeliveryFailure("terminal_failure")
        try:
            subject, body = self._render(claim)
            if (
                not isinstance(subject, str)
                or not 1 <= len(subject) <= 120
                or any(c in subject for c in "\r\n")
                or not isinstance(body, str)
                or not 1 <= len(body.encode("utf-8")) <= 8192
            ):
                raise ValueError
        except Exception:
            raise NotificationDeliveryFailure("terminal_failure") from None
        configuration = self._snapshot()
        providers = (
            ("ses", "resend") if configuration.primary == "ses" else ("resend", "ses")
        )
        for provider in providers:
            try:
                if provider == "ses":
                    self._ses_send(recipient.email, subject, body)
                else:
                    self._resend_send(
                        configuration.resend_api_key, recipient.email, subject, body
                    )
                return
            except Exception:
                pass  # Provider details and private addresses never escape.
        raise NotificationDeliveryFailure("ambiguous") from None

    async def __call__(
        self, claim: NotificationClaim, recipient: NotificationRecipient
    ) -> None:
        """Run bounded synchronous provider calls away from the API event loop."""
        await asyncio.to_thread(self._send, claim, recipient)
