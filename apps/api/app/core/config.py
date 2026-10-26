"""Shared typed, redacted process-environment configuration for the API."""

import re
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    Field,
    SecretStr,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """Report invalid startup settings without echoing supplied values."""


ISOLATED_LISTINGS_TEST_DATABASE = "clip_test_listings"
ISOLATED_LISTINGS_TEST_BUCKET = "clip-test-listings-images-ap-south-1-li02"
ISOLATED_LISTINGS_TEST_REGION = "ap-south-1"
ISOLATED_LISTINGS_TEST_MAX_COUNT = 10
IDENTITY_TEST_BROWSER_ORIGINS = ("https://clip-iisc.site",)


class Settings(BaseSettings):
    """Load API settings from CLIP_ environment names without reading dotenv files.

    Defaults allow credential-free local startup. Database-backed Listings is
    enabled only when its PostgreSQL URL is explicitly configured; no fake
    database or provider fallback is selected.
    """

    model_config = SettingsConfigDict(
        env_prefix="CLIP_",
        env_file=None,
        frozen=True,
        hide_input_in_errors=True,
    )

    environment: Literal["local", "test", "production"] = "local"
    debug: bool = False
    # Selectors default disabled. Real Identity startup remains unbound unless the
    # separately guarded test-only runtime flag and complete configuration exist.
    identity_provider: Literal["disabled", "fake", "microsoft"] = "disabled"
    email_provider: Literal["disabled", "fake", "ses", "dual"] = "disabled"
    # Hosted real Identity startup is an explicit test-environment capability.
    # Defaults preserve the liveness-only, Identity-unbound ASGI entry point.
    identity_runtime_enabled: bool = False
    identity_browser_origins: tuple[str, ...] = Field(default=(), repr=False)
    # Step 2 permits only explicitly controlled sandbox recipients. General delivery
    # requires a separately reviewed production configuration increment.
    ses_region: Literal["ap-south-1"] = "ap-south-1"
    ses_sender: Literal["verify@clip-iisc.site"] = "verify@clip-iisc.site"
    ses_test_recipients: tuple[str, ...] = Field(default=(), repr=False)
    storage_provider: Literal["disabled", "fake", "s3"] = "disabled"
    image_bucket: str | None = None
    image_region: str | None = None
    image_key_prefix: str | None = None
    development_auth: bool = False
    isolated_listings_test_caller: bool = False
    isolated_listings_max_count: int | None = None
    serve_web_app: bool = False
    # SecretStr prevents accidental repr/log output of embedded credentials.
    database_url: SecretStr | None = None
    # Hybrid is opt-in; explicit paths never download/discover a model or interpreter.
    hybrid_search_enabled: bool = False
    hybrid_worker_enabled: bool = False
    hybrid_search_interpreter: Path | None = Field(default=None, repr=False)
    hybrid_search_model_dir: Path | None = Field(
        default=None, repr=False, validate_default=True
    )
    # Listings compares prices against this configurable whole-rupee threshold.
    sensitive_purchase_threshold_paise: int = Field(
        default=500_000, ge=0, multiple_of=100
    )

    @field_validator("hybrid_worker_enabled")
    @classmethod
    def worker_requires_hybrid(cls, value: bool, info: ValidationInfo) -> bool:
        """No standalone/default worker can start without the explicitly owned helper."""
        if value and not info.data.get("hybrid_search_enabled", False):
            raise ValueError("Hybrid worker requires hybrid_search_enabled")
        return value

    @field_validator("hybrid_search_interpreter", "hybrid_search_model_dir")
    @classmethod
    def absolute_hybrid_path(cls, value: Path | None) -> Path | None:
        """Require explicit absolute local paths; preserve interpreter venv symlinks.

        Files/artifact pins are checked by the real helper at startup, not by
        reading files during configuration parsing. No shell/path expansion.
        """
        if value is not None and (not value.is_absolute() or "\x00" in str(value)):
            raise ValueError("Hybrid paths must be absolute local paths")
        return value

    @field_validator("hybrid_search_model_dir")
    @classmethod
    def paired_hybrid_settings(
        cls, value: Path | None, info: ValidationInfo
    ) -> Path | None:
        """Reject partial/ignored Hybrid settings before any runtime side effect.

        This field validates its default too and follows the enable/interpreter/
        database fields, so missing paired inputs still produce a redacted named
        configuration error. No existing target is contacted here.
        """
        enabled = info.data.get("hybrid_search_enabled", False)
        interpreter = info.data.get("hybrid_search_interpreter")
        if enabled and (
            interpreter is None
            or value is None
            or info.data.get("database_url") is None
        ):
            raise ValueError("Hybrid requires database_url, interpreter and model_dir")
        if not enabled and (interpreter is not None or value is not None):
            raise ValueError("Hybrid paths require hybrid_search_enabled")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        """Accept only PostgreSQL connection URLs and keep credentials redacted."""
        if value is None:
            return None
        raw = value.get_secret_value()
        if not raw.startswith(("postgres://", "postgresql://")):
            raise ValueError("must be a PostgreSQL URL")
        return value

    @field_validator(
        "identity_provider",
        "email_provider",
        "storage_provider",
        "development_auth",
        "isolated_listings_test_caller",
    )
    @classmethod
    def reject_production_test_controls(
        cls, value: str | bool, info: ValidationInfo
    ) -> str | bool:
        """Refuse explicit testing controls in production; never select a fallback.

        Real provider options/configuration belong to ID-01/LI-02/CN-03. Unknown provider
        names already fail Literal validation rather than pretending to exist.
        """
        if info.data.get("environment") == "production" and value in ("fake", True):
            raise ValueError(
                "Test providers and development authentication are forbidden in production"
            )
        return value

    @model_validator(mode="after")
    def restrict_microsoft_integration(self) -> Self:
        """Keep private validation unavailable in production before session wiring."""
        if self.identity_provider == "microsoft" and self.environment == "production":
            raise ValueError(
                "Microsoft session integration is not enabled for production"
            )
        return self

    @model_validator(mode="after")
    def validate_hosted_identity_runtime(self) -> Self:
        """Allow explicit real Identity startup only in the bounded test profile.

        This is not a production switch: it requires the test environment, real
        Microsoft plus dual-provider selectors, a separate Listings database URL,
        and exact HTTPS browser origins. Cloud task/IAM/proxy setup remains gated.
        """
        if not self.identity_runtime_enabled:
            if self.identity_browser_origins:
                raise ValueError(
                    "identity_browser_origins requires identity_runtime_enabled"
                )
            return self
        if (
            self.environment != "test"
            or self.identity_provider != "microsoft"
            or self.email_provider != "dual"
            or self.debug
            or self.development_auth
            or self.isolated_listings_test_caller
            or self.database_url is None
            or self.identity_browser_origins != IDENTITY_TEST_BROWSER_ORIGINS
        ):
            raise ValueError("Invalid hosted Identity test configuration")
        for origin in self.identity_browser_origins:
            parsed = urlsplit(origin)
            if (
                not parsed.hostname
                or parsed.scheme != "https"
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in origin
            ):
                raise ValueError("Identity browser origins must be exact HTTPS origins")
        return self

    @model_validator(mode="after")
    def restrict_ses_sandbox(self) -> Self:
        """Require an explicit bounded recipient list and refuse production sending.

        The list limits local/test dispatch; it neither verifies SES identities
        nor authorizes a live send. Those actions retain their human gates.
        """
        if self.email_provider in ("ses", "dual"):
            if self.environment == "production" or not self.ses_test_recipients:
                raise ValueError(
                    "SES currently requires controlled local/test recipients"
                )
            if len(self.ses_test_recipients) > 5 or any(
                not recipient.isascii()
                or recipient.count("@") != 1
                or any(character.isspace() for character in recipient)
                or not all(recipient.split("@"))
                for recipient in self.ses_test_recipients
            ):
                raise ValueError("Invalid controlled SES recipients")
        return self

    @model_validator(mode="after")
    def reject_production_debug(self) -> Self:
        """Prevent detailed error responses from being enabled in production."""
        if self.environment == "production" and self.debug:
            raise ValueError("Debug must be disabled in production")
        if self.storage_provider == "s3" and not all(
            (self.image_bucket, self.image_region, self.image_key_prefix)
        ):
            raise ValueError(
                "S3 storage requires an image bucket, region, and key prefix"
            )
        if self.storage_provider != "s3" and any(
            (self.image_bucket, self.image_region, self.image_key_prefix)
        ):
            raise ValueError("Image S3 settings require storage_provider=s3")
        if self.isolated_listings_test_caller:
            database = (
                urlsplit(self.database_url.get_secret_value()).path.strip("/")
                if self.database_url is not None
                else ""
            )
            if (
                self.environment != "test"
                or not self.development_auth
                or database != ISOLATED_LISTINGS_TEST_DATABASE
                or self.storage_provider != "s3"
                or self.image_bucket != ISOLATED_LISTINGS_TEST_BUCKET
                or self.image_region != ISOLATED_LISTINGS_TEST_REGION
                or self.image_key_prefix is None
                or self.isolated_listings_max_count != ISOLATED_LISTINGS_TEST_MAX_COUNT
                or not re.fullmatch(
                    r"listings/test/[a-z0-9][a-z0-9-]{2,39}",
                    self.image_key_prefix or "",
                )
            ):
                raise ValueError(
                    "The isolated Listings test caller requires the dedicated test database and bucket configuration"
                )
        elif self.isolated_listings_max_count is not None:
            raise ValueError(
                "The isolated Listings limit requires the isolated test caller"
            )
        # Hosting the built UI is independent of authentication. Only the explicit
        # isolated caller flag may activate the guarded Listings demo identity.
        return self


def load_settings() -> Settings:
    """Validate fresh startup settings and report field names, never values.

    Do not cache reads: isolated test environments and subsequent app instances
    must not inherit settings from an earlier environment snapshot.
    """
    try:
        return Settings()
    except ValidationError as error:
        fields = {
            (
                "CLIP_" + str(detail["loc"][0]).upper()
                if detail["loc"]
                else "CLIP_DEBUG (must be false when CLIP_ENVIRONMENT=production); "
                "CLIP_EMAIL_PROVIDER; CLIP_SES_TEST_RECIPIENTS"
            )
            for detail in error.errors(include_input=False, include_url=False)
        }
        raise ConfigurationError(
            "Invalid API configuration; check " + ", ".join(sorted(fields)) + "."
        ) from None
