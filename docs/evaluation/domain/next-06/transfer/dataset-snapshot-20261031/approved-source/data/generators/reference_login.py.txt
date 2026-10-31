"""Refresh SDK browser-login credentials through the existing AWS CLI, in memory.

The bridge writes no credential/config files. The CLI manages its normal existing
login cache and handles its approved
login session; only its versioned process-format response enters the SDK signer.
Static/other named profile mechanisms retain the normal SDK chain. Import and
session construction never export credentials or contact a service.
"""

from datetime import UTC, datetime, timedelta
import json
import os
import shutil
import subprocess

import boto3
import botocore.session
from botocore.credentials import (
    CredentialProvider,
    CredentialResolver,
    RefreshableCredentials,
)


class CliLoginUnavailable(RuntimeError):
    """Fixed safe diagnostic; never propagate CLI stdout/stderr or credential values."""


class CliLoginProvider(CredentialProvider):
    """Use the named CLI login profile with bounded exports and refreshable tokens."""

    METHOD = "clip-cli-login"

    def __init__(self, profile, executable):
        self.profile = profile
        self.executable = executable

    def _export(self):
        """Capture temporary credentials privately; reject malformed/stale responses."""
        try:
            result = subprocess.run(
                [
                    self.executable,
                    "--profile",
                    self.profile,
                    "--no-cli-pager",
                    "--cli-connect-timeout",
                    "5",
                    "--cli-read-timeout",
                    "10",
                    "configure",
                    "export-credentials",
                    "--format",
                    "process",
                ],
                env={
                    k: os.environ[k]
                    for k in (
                        "HOME",
                        "PATH",
                        "SSL_CERT_FILE",
                        "HTTPS_PROXY",
                        "NO_PROXY",
                    )
                    if k in os.environ
                }
                | {
                    "AWS_MAX_ATTEMPTS": "1",
                    "AWS_PAGER": "",
                    "AWS_CLI_AUTO_PROMPT": "off",
                },
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=20,
                check=False,
            )
            if result.returncode or len(result.stdout) > 65536:
                raise ValueError
            value = json.loads(result.stdout)
            if type(value.get("Version")) is not int or value["Version"] != 1:
                raise ValueError
            for key in ("AccessKeyId", "SecretAccessKey", "SessionToken", "Expiration"):
                if not isinstance(value.get(key), str) or not value[key].strip():
                    raise ValueError
            expiry = datetime.fromisoformat(value["Expiration"].replace("Z", "+00:00"))
            if expiry.utcoffset() is None or not datetime.now(UTC) + timedelta(
                seconds=30
            ) < expiry <= datetime.now(UTC) + timedelta(hours=12):
                raise ValueError
            return {
                "access_key": value["AccessKeyId"],
                "secret_key": value["SecretAccessKey"],
                "token": value["SessionToken"],
                "expiry_time": expiry.astimezone(UTC).isoformat(),
            }
        except (
            ValueError,
            TypeError,
            AttributeError,
            OSError,
            subprocess.SubprocessError,
        ):
            raise CliLoginUnavailable("cli_login_export_unavailable") from None

    def load(self):
        """Use process-format expiry and refresh without exposing credentials to callers."""
        return RefreshableCredentials.create_from_metadata(
            self._export(),
            refresh_using=self._export,
            method=self.METHOD,
            advisory_timeout=60,
            mandatory_timeout=30,
        )


def sdk_session(profile, region):
    """Select only the explicit profile; bridge login without requiring botocore[crt].

    Register one scoped provider instead of relying on ambient/default/root chain
    fallback. Actual account/non-root validation remains the caller's STS gate.
    Non-login profile types keep their existing normal SDK behavior.
    """
    if not isinstance(profile, str) or not profile or any(c.isspace() for c in profile):
        raise CliLoginUnavailable("explicit_profile_required")
    session = botocore.session.Session(profile=profile)
    if session.get_scoped_config().get("login_session"):
        executable = shutil.which("aws")
        if not executable:
            raise CliLoginUnavailable("aws_cli_required_for_login")
        session.register_component(
            "credential_provider",
            CredentialResolver([CliLoginProvider(profile, executable)]),
        )
    return boto3.Session(botocore_session=session, region_name=region)
