"""Identity-owned SES transport; challenge creation/verification belongs to Step 5.

Construction and import perform no AWS calls. Only explicit dispatch can send.
The transport accepts a purpose-bound body from trusted Identity code and must
never be exposed as a generic browser-controlled email endpoint.
"""

from importlib import import_module
from typing import Protocol, cast

from app.core.config import Settings
from app.domains.identity.temporary_crypto import normalize_login


class EmailUnavailable(RuntimeError):
    """A safe transport failure; provider text, recipient and body stay private."""


class SesClient(Protocol):
    """Narrow SDK boundary allowing deterministic offline transport tests."""

    def send_email(self, **kwargs: object) -> dict[str, object]:
        """Submit one message; SDK acceptance does not establish inbox delivery."""
        ...


class SesEmailSender:
    """Send bounded Identity mail without automatic duplicate retries.

    A timeout can follow provider acceptance. Callers must treat that outcome as
    uncertain, not retry blindly or claim delivery. No message data is logged.
    Blocking dispatch must run outside the async event loop when Step 5 wires it.
    """

    def __init__(self, settings: Settings, client: SesClient | None = None) -> None:
        """Bind validated sandbox settings and an optional offline SDK substitute."""
        if settings.email_provider not in ("ses", "dual"):
            raise EmailUnavailable("Email provider is disabled")
        self._settings = settings
        self._client = client

    def send(self, recipient: str, subject: str, body: str) -> None:
        """Submit only canonical recipients; hosted real auth supports general mail.

        No raw OTP, recipient, content or provider exception is returned. This
        function stores nothing and does not create or activate an account.
        Standalone/local test configuration retains its recipient restriction;
        only the already explicit real hosted runtime removes that restriction.
        """
        try:
            valid_recipient = normalize_login(recipient) == recipient
        except Exception:
            valid_recipient = False
        if (
            not valid_recipient
            or (
                not self._settings.identity_runtime_enabled
                and recipient not in self._settings.ses_test_recipients
            )
            or not subject
            or len(subject) > 120
            or any(character in subject for character in "\r\n")
            or not body
            or len(body.encode("utf-8")) > 8192
        ):
            raise EmailUnavailable("Email dispatch refused")
        try:
            client = self._client or self._make_client()
            response = client.send_email(
                FromEmailAddress=self._settings.ses_sender,
                Destination={"ToAddresses": [recipient]},
                Content={
                    "Simple": {
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                    }
                },
            )
            if (
                not isinstance(response.get("MessageId"), str)
                or not response["MessageId"]
            ):
                raise EmailUnavailable("Email submission was not confirmed")
        except Exception:
            # Never chain SDK errors: they can contain destinations or message data.
            raise EmailUnavailable(
                "Email submission unavailable or uncertain"
            ) from None

    def _make_client(self) -> SesClient:
        """Load the pinned SDK lazily; use its credential chain and bounded I/O.

        ECS uses its task role; local operators use their approved AWS profile.
        No access key, SMTP password, custom endpoint or static secret is accepted.
        SDK debug logging must remain disabled because wire payloads are private.
        """
        boto3 = import_module("boto3")
        config_module = import_module("botocore.config")
        return cast(
            SesClient,
            boto3.client(
                "sesv2",
                region_name=self._settings.ses_region,
                config=config_module.Config(
                    ignore_configured_endpoint_urls=True,
                    connect_timeout=3,
                    read_timeout=5,
                    retries={"mode": "standard", "total_max_attempts": 1},
                ),
            ),
        )
