"""Shared typed process-environment configuration for the API foundation."""

from typing import Literal, Self

from pydantic import ValidationError, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """Report invalid startup settings without echoing supplied values."""


class Settings(BaseSettings):
    """Load the skeleton's non-secret settings from CLIP_ environment names.

    Defaults allow credential-free local startup. No dotenv or secret files are
    loaded. Database/provider requirements belong to their implementing tasks;
    this model does not imply those dependencies exist or are configured.
    """

    model_config = SettingsConfigDict(
        env_prefix="CLIP_",
        env_file=None,
        frozen=True,
        hide_input_in_errors=True,
    )

    environment: Literal["local", "test", "production"] = "local"
    debug: bool = False
    # These select future test adapters only; no provider is implemented here.
    identity_provider: Literal["disabled", "fake"] = "disabled"
    email_provider: Literal["disabled", "fake"] = "disabled"
    development_auth: bool = False

    @field_validator("identity_provider", "email_provider", "development_auth")
    @classmethod
    def reject_production_test_controls(
        cls, value: str | bool, info: ValidationInfo
    ) -> str | bool:
        """Refuse explicit testing controls in production; never select a fallback.

        Real provider options/configuration belong to ID-01/CN-03. Unknown provider
        names already fail Literal validation rather than pretending to exist.
        """
        if info.data.get("environment") == "production" and value in ("fake", True):
            raise ValueError(
                "Test providers and development authentication are forbidden in production"
            )
        return value

    @model_validator(mode="after")
    def reject_production_debug(self) -> Self:
        """Prevent detailed error responses from being enabled in production."""
        if self.environment == "production" and self.debug:
            raise ValueError("Debug must be disabled in production")
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
                else "CLIP_DEBUG (must be false when CLIP_ENVIRONMENT=production)"
            )
            for detail in error.errors(include_input=False, include_url=False)
        }
        raise ConfigurationError(
            "Invalid API configuration; check " + ", ".join(sorted(fields)) + "."
        ) from None
