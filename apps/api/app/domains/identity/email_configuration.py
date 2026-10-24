"""Explicit SSM loader for atomic email routing/key snapshots; no ambient activation.

The deployment must separately approve/create the exact SecureString and task-role
read permission. One parameter version holds order and key together; no split
reads can mix a newly selected provider with a separately rotated credential.
"""

from importlib import import_module
import json
import re
from typing import Protocol, cast

from pydantic import SecretStr

from app.domains.identity.email import EmailUnavailable
from app.domains.identity.email_routing import EmailRoute
from app.domains.identity.resend_email import ResendEmailSender
from app.domains.identity.temporary_delivery import EmailSender


class ParameterClient(Protocol):
    """Narrow real SSM read boundary; injectable only through trusted composition."""

    def get_parameter(self, **kwargs: object) -> dict[str, object]:
        """Read one exact versioned SecureString with decryption."""
        ...


class SsmEmailRouteLoader:
    """Load one exact approved parameter on demand, with bounded redacted failures.

    SES remains an explicitly supplied real adapter with its own sandbox/access
    rules. This loader cannot remove its recipient restrictions or change auth
    settings, and never installs a fake. RefreshingEmailSender owns the four-hour
    in-memory lifetime. No value is written to disk, logs or an environment file.
    """

    def __init__(
        self,
        parameter: str,
        recipients: tuple[str, ...],
        ses: EmailSender,
        client: ParameterClient | None = None,
    ) -> None:
        """Require a private project path; construction reads no secrets/providers."""
        if not re.fullmatch(r"/clip/[a-zA-Z0-9_/-]{1,250}", parameter):
            raise ValueError("Explicit project email parameter required")
        self._parameter, self._recipients, self._ses = parameter, recipients, ses
        self._client = client

    def __call__(self) -> EmailRoute:
        """Strictly validate the private versioned JSON before constructing a route."""
        try:
            client = self._client or self._make_client()
            result = client.get_parameter(Name=self._parameter, WithDecryption=True)
            row = result.get("Parameter")
            if not isinstance(row, dict) or row.get("Type") != "SecureString":
                raise ValueError
            raw = row.get("Value")
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > 4096:
                raise ValueError
            value = json.loads(raw)
            if (
                not isinstance(value, dict)
                or set(value) != {"version", "primary", "resend_api_key"}
                or type(value["version"]) is not int
                or value["version"] != 1
                or value["primary"] not in ("resend", "ses")
                or not isinstance(value["resend_api_key"], str)
            ):
                raise ValueError
            return EmailRoute(
                value["primary"],
                ResendEmailSender(SecretStr(value["resend_api_key"]), self._recipients),
                self._ses,
            )
        except Exception:
            raise EmailUnavailable("Email configuration unavailable") from None

    @staticmethod
    def _make_client() -> ParameterClient:
        """Use existing task/profile credentials and fixed Mumbai SSM endpoint.

        Ignore configured endpoint overrides, use3/5second socket limits and one
        SDK attempt. No static AWS credentials, region selector or URL input.
        """
        boto3 = import_module("boto3")
        config = import_module("botocore.config")
        return cast(
            ParameterClient,
            boto3.client(
                "ssm",
                region_name="ap-south-1",
                config=config.Config(
                    ignore_configured_endpoint_urls=True,
                    connect_timeout=3,
                    read_timeout=5,
                    retries={"mode": "standard", "total_max_attempts": 1},
                ),
            ),
        )
