"""Shared typed process-environment configuration for the API foundation."""

from typing import Literal, Self

from pydantic import (
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
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
    # Selectors default disabled. Private Microsoft preparation is local/test only
    # until reviewed login-attempt and session wiring enables the real API flow.
    identity_provider: Literal["disabled", "fake", "microsoft"] = "disabled"
    email_provider: Literal["disabled", "fake", "ses"] = "disabled"
    # Step 2 permits only explicitly controlled sandbox recipients. General delivery
    # requires a separately reviewed production configuration increment.
    ses_region: Literal["ap-south-1"] = "ap-south-1"
    ses_sender: Literal["verify@clip-iisc.site"] = "verify@clip-iisc.site"
    ses_test_recipients: tuple[str, ...] = Field(default=(), repr=False)
    storage_provider: Literal["disabled", "fake"] = "disabled"
    development_auth: bool = False

    @field_validator(
        "identity_provider", "email_provider", "storage_provider", "development_auth"
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
    def restrict_ses_sandbox(self) -> Self:
        """Require an explicit bounded recipient list and refuse production sending.

        The list limits local/test dispatch; it neither verifies SES identities
        nor authorizes a live send. Those actions retain their human gates.
        """
        if self.email_provider == "ses":
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
