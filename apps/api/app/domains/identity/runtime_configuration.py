"""Prepare explicit local/test Identity bindings from approved secret references.

This module never provisions secrets, changes privileges or activates app.main.
The caller must approve/verify the actual AWS identity, references and database
before live bootstrap. Tests inject an offline parameter client and owned SQL.
"""

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import Any, Callable

from pydantic import SecretStr

from app.core.config import ConfigurationError, Settings
from app.domains.identity.email import SesEmailSender
from app.domains.identity.email_configuration import (
    ParameterClient,
    SsmEmailRouteLoader,
)
from app.domains.identity.email_routing import RefreshingEmailSender
from app.domains.identity.http import BrowserPolicy, IdentityHttpDependencies
from app.domains.identity.microsoft import MicrosoftKeys, MicrosoftTokenValidator
from app.domains.identity.runtime_database import connection_factory, validate_database
from app.domains.identity.sessions import IdentitySessions
from app.domains.identity.temporary_crypto import TemporaryKeys


@dataclass(frozen=True)
class RuntimeReferences:
    """Fixed reviewed test namespace; references only, never credential values."""

    authentication_keys: str = "/clip/test/identity/authentication-keys"
    database_url: str = "/clip/test/identity/database-url"
    email_delivery: str = "/clip/test/identity/email-delivery"

    def __post_init__(self) -> None:
        """Refuse alternate namespaces/targets until a reviewed configuration change."""
        if (self.authentication_keys, self.database_url, self.email_delivery) != (
            "/clip/test/identity/authentication-keys",
            "/clip/test/identity/database-url",
            "/clip/test/identity/email-delivery",
        ):
            raise ValueError("Unapproved Identity runtime references")


def read_secure_parameter(client: ParameterClient, name: str) -> SecretStr:
    """Read one bounded versioned SecureString and suppress private SDK responses."""
    try:
        row = client.get_parameter(Name=name, WithDecryption=True).get("Parameter")
        if (
            not isinstance(row, dict)
            or row.get("Name") != name
            or row.get("Type") != "SecureString"
            or type(row.get("Version")) is not int
            or row["Version"] < 1
            or not isinstance(row.get("Value"), str)
            or not 1 <= len(row["Value"].encode("utf-8")) <= 4096
        ):
            raise ValueError
        return SecretStr(row["Value"])
    except Exception:
        raise ConfigurationError("Identity secret configuration unavailable") from None


def parse_authentication_keys(value: SecretStr) -> TemporaryKeys:
    """Decode exactly three independent canonical-base64 256bit keys and version.

    Keys persist across restarts; never generate substitutes or refresh them with
    the email preference cache. Database commitments reject accidental replacement.
    Duplicate/extra JSON fields and malformed/aliased encodings are rejected.
    """
    try:

        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError
                result[key] = item
            return result

        raw = value.get_secret_value()
        if len(raw.encode("utf-8")) > 4096:
            raise ValueError
        row = json.loads(raw, object_pairs_hook=unique)
        fields = ("lookup", "verifier", "target_encryption")
        if (
            not isinstance(row, dict)
            or set(row) != {"schema_version", "key_version", *fields}
            or type(row["schema_version"]) is not int
            or row["schema_version"] != 1
            or not isinstance(row["key_version"], str)
        ):
            raise ValueError
        keys = []
        for field in fields:
            encoded = row[field]
            if not isinstance(encoded, str):
                raise ValueError
            decoded = base64.b64decode(encoded, validate=True)
            if (
                len(decoded) != 32
                or base64.b64encode(decoded).decode("ascii") != encoded
            ):
                raise ValueError
            keys.append(decoded)
        return TemporaryKeys(row["key_version"], *keys)
    except Exception:
        raise ConfigurationError("Invalid persistent Identity keys") from None


def prepare_local_identity(
    settings: Settings,
    policy: BrowserPolicy,
    references: RuntimeReferences = RuntimeReferences(),
    *,
    client: ParameterClient | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> IdentityHttpDependencies:
    """Validate secrets, email snapshot and separate DB login before app assembly.

    Explicit local/test only; production/demo/bypass combinations fail before any
    secret read. Actual SSM/DB access needs the operator's separate approval.
    This returns real dependencies for create_app, not an enabled default app.
    It neither sends mail nor fetches Microsoft metadata/creates an account.
    """
    if (
        settings.environment not in {"local", "test"}
        or settings.identity_provider != "microsoft"
        or settings.email_provider != "dual"
        or settings.development_auth
        or settings.isolated_listings_test_caller
        or settings.serve_web_app
        or not isinstance(policy, BrowserPolicy)
    ):
        raise ConfigurationError("Explicit safe local Identity configuration required")
    try:
        parameter_client = client or SsmEmailRouteLoader._make_client()
        keys = parse_authentication_keys(
            read_secure_parameter(parameter_client, references.authentication_keys)
        )
        dsn = read_secure_parameter(parameter_client, references.database_url)
        connect = connection_factory(dsn, settings.environment)
        validate_database(connect, keys)
        sender = RefreshingEmailSender(
            SsmEmailRouteLoader(
                references.email_delivery,
                settings.ses_test_recipients,
                SesEmailSender(settings),
                parameter_client,
            )
        )
        sender.warmup()
        sessions = IdentitySessions(connect, keys, clock)
        return IdentityHttpDependencies(
            sessions, policy, sender, MicrosoftTokenValidator(MicrosoftKeys()), clock
        )
    except Exception:
        raise ConfigurationError("Identity startup validation failed") from None
