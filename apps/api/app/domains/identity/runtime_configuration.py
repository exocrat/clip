"""Prepare explicit local/test Identity bindings from approved secret references.

This module never provisions secrets, changes privileges or activates app.main.
The caller must approve/verify the actual AWS identity, references and database
before live bootstrap. Tests inject an offline parameter client and owned SQL.
"""

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from os import environ
from typing import Any, Callable, Self

from pydantic import SecretStr, model_validator

from app.core.config import (
    IDENTITY_TEST_BROWSER_ORIGINS,
    ConfigurationError,
    Settings,
    load_settings,
)
from app.domains.identity.email import SesEmailSender
from app.domains.identity.email_configuration import (
    ParameterClient,
    SsmEmailRouteLoader,
)
from app.domains.identity.email_routing import RefreshingEmailSender
from app.domains.identity.http import (
    BrowserPolicy,
    IdentityHttpDependencies,
    IdentityReadDependencies,
)
from app.domains.identity.microsoft import MicrosoftKeys, MicrosoftTokenValidator
from app.domains.identity.runtime_database import connection_factory, validate_database
from app.domains.identity.sessions import IdentitySessions
from app.domains.identity.temporary_crypto import TemporaryKeys

LISTINGS_DATABASE_PARAMETER = "/clip/test/listings-database-url"
PARAMETER_OPT_IN = "CLIP_LAMBDA_DATABASE_PARAMETER_ENABLED"


class LambdaReadSettings(Settings):
    """Keep hosted session reads isolated from email and write runtimes."""

    @model_validator(mode="after")
    def validate_hosted_identity_runtime(self) -> Self:
        """Require the real hosted test identity and no unrelated app services."""
        if (
            not self.identity_runtime_enabled
            or self.nfr07_restore_smoke_enabled
            or self.environment != "test"
            or self.identity_provider != "microsoft"
            or self.email_provider != "disabled"
            or self.ses_test_recipients
            or self.identity_browser_origins != IDENTITY_TEST_BROWSER_ORIGINS
            or self.database_url is None
            or self.debug
            or self.development_auth
            or self.isolated_listings_test_caller
            or self.serve_web_app
            or self.notification_worker_enabled
            or self.hybrid_worker_enabled
            or self.storage_provider != "disabled"
        ):
            raise ValueError("Invalid Lambda read-only Identity configuration")
        return self

    @model_validator(mode="after")
    def restrict_ses_sandbox(self) -> Self:
        """Forbid email configuration entirely for this read-only runtime."""
        if self.email_provider != "disabled" or self.ses_test_recipients:
            raise ValueError("Lambda read-only Identity cannot configure email")
        return self


def load_lambda_settings(*, client: ParameterClient | None = None) -> Settings:
    """Use a fixed SecureString only after validating the rest of the test setup.

    The value remains a SecretStr in process memory. This function neither
    modifies the environment nor permits a caller-selected parameter name.
    """
    enabled = environ.get(PARAMETER_OPT_IN, "false")
    if enabled == "false":
        return load_settings()
    if (
        enabled != "true"
        or not environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or environ.get("CLIP_ENVIRONMENT") != "test"
        or environ.get("CLIP_IDENTITY_RUNTIME_ENABLED") != "true"
        or "CLIP_DATABASE_URL" in environ
    ):
        raise ConfigurationError("Invalid Lambda database parameter setup")
    try:
        # Validate all other settings before a provider or credential is accessed.
        LambdaReadSettings(
            database_url=SecretStr("postgresql://fixture@localhost/clip")
        )
    except Exception:
        raise ConfigurationError("Invalid Lambda hosted test configuration") from None
    try:
        parameter_client = client or SsmEmailRouteLoader._make_client()
        value = read_secure_parameter(parameter_client, LISTINGS_DATABASE_PARAMETER)
        return LambdaReadSettings(database_url=value)
    except Exception:
        raise ConfigurationError("Lambda database configuration unavailable") from None


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
        or settings.identity_runtime_enabled
        or settings.development_auth
        or settings.isolated_listings_test_caller
        or settings.serve_web_app
        or not isinstance(policy, BrowserPolicy)
    ):
        raise ConfigurationError("Explicit safe local Identity configuration required")
    return _prepare_identity(settings, policy, references, client=client, clock=clock)


def prepare_hosted_test_identity(
    settings: Settings,
    references: RuntimeReferences = RuntimeReferences(),
    *,
    client: ParameterClient | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> IdentityHttpDependencies:
    """Prepare real bindings for the explicit hosted test-environment opt-in.

    The Settings validator requires real Microsoft/dual selectors, a Listings
    database URL, exact HTTPS Origins, and test mode. This path reads the fixed Identity SecureStrings (with the fixed isolated
    database parameter in the explicit NFR-07 profile) and audits the DB role;
    it never migrates, provisions or sends mail during startup.
    """
    if not settings.identity_runtime_enabled or settings.environment != "test":
        raise ConfigurationError("Explicit hosted Identity test mode required")
    try:
        policy = BrowserPolicy(settings.identity_browser_origins)
    except Exception:
        raise ConfigurationError("Invalid hosted Identity browser policy") from None
    return _prepare_identity(settings, policy, references, client=client, clock=clock)


def prepare_hosted_test_identity_reads(
    settings: Settings,
    references: RuntimeReferences = RuntimeReferences(),
    *,
    client: ParameterClient | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> IdentityReadDependencies:
    """Prepare existing-cookie validation without email or login provider startup.

    Explicit hosted test opt-in only. Reads the same fixed auth-key and Identity
    DB references, reuses the existing role/key audit and real session service.
    This does not narrow that DB role's grants or change authentication semantics.
    Actual secret/DB access remains an operator action requiring separate approval.
    """
    if (
        not settings.identity_runtime_enabled
        or settings.environment != "test"
        or settings.development_auth
        or settings.isolated_listings_test_caller
    ):
        raise ConfigurationError("Explicit hosted Identity test mode required")
    try:
        policy = BrowserPolicy(settings.identity_browser_origins)
        parameter_client = client or SsmEmailRouteLoader._make_client()
        keys = parse_authentication_keys(
            read_secure_parameter(parameter_client, references.authentication_keys)
        )
        dsn = read_secure_parameter(parameter_client, references.database_url)
        connect = connection_factory(dsn, settings.environment)
        validate_database(connect, keys)
        return IdentityReadDependencies(IdentitySessions(connect, keys, clock), policy)
    except Exception:
        raise ConfigurationError("Identity read startup validation failed") from None


def _prepare_identity(
    settings: Settings,
    policy: BrowserPolicy,
    references: RuntimeReferences,
    *,
    client: ParameterClient | None,
    clock: Callable[[], datetime],
) -> IdentityHttpDependencies:
    """Load bounded runtime references and assemble the existing real services."""
    try:
        parameter_client = client or SsmEmailRouteLoader._make_client()
        keys = parse_authentication_keys(
            read_secure_parameter(parameter_client, references.authentication_keys)
        )
        # Restore smoke uses the same real keys/provider but its own restored
        # Identity role/endpoint. No caller-selected secret namespace is allowed.
        database_parameter = (
            "/clip/test/nfr07/identity-database-url"
            if settings.nfr07_restore_smoke_enabled
            else references.database_url
        )
        dsn = read_secure_parameter(parameter_client, database_parameter)
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
