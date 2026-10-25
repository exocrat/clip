"""Wanted HTTP validation and explicit content-safe response projection."""

import re
from typing import Any

from pydantic import field_validator, model_validator

from app.contracts.domain_types import (
    CreateWantedRequest,
    DraftMatchRequest,
    PageQuery,
    WantedRequestOwnerView,
    WantedRequestPatch,
    WantedRequestPublic,
    WantedRequestStateChange,
)
from app.core.money import validate_paise


class WantedCreate(CreateWantedRequest):
    """Trim text before inherited bounds; never coerce bool/float money."""

    @field_validator("title", "description", mode="before")
    @classmethod
    def trimmed_text(cls, value: Any) -> Any:
        """Whitespace-only input becomes empty and fails the inherited minimum."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("budget_paise", mode="before")
    @classmethod
    def exact_budget(cls, value: Any) -> Any:
        """Null is unstated; numeric amounts must be whole-rupee integer paise."""
        if value is not None:
            validate_paise(value)
            if value > 2**63 - 1:
                raise ValueError("Amount exceeds bigint storage")
        return value


class WantedPatch(WantedRequestPatch):
    """Omission preserves fields; only budget permits an explicit null."""

    @field_validator("title", "description", "category_code", mode="before")
    @classmethod
    def nonnull_text(cls, value: Any) -> Any:
        """Reject explicit null; omitted optional defaults are not validated."""
        if value is None:
            raise ValueError("Non-null field")
        return value.strip() if isinstance(value, str) else value

    @field_validator("budget_paise", mode="before")
    @classmethod
    def exact_budget(cls, value: Any) -> Any:
        """Preserve explicit null while enforcing exact integer money."""
        if value is not None:
            validate_paise(value)
            if value > 2**63 - 1:
                raise ValueError("Amount exceeds bigint storage")
        return value

    @field_validator("expected_revision", mode="before")
    @classmethod
    def exact_revision(cls, value: Any) -> Any:
        """Do not round floats or accept booleans as revisions."""
        if type(value) is not int:
            raise ValueError("Integer revision required")
        return value


class WantedState(WantedRequestStateChange):
    """Availability uses the same strict revision rule as edits."""

    @field_validator("expected_revision", mode="before")
    @classmethod
    def exact_revision(cls, value: Any) -> Any:
        """Validate internal construction as well as HTTP parsing."""
        return WantedPatch.exact_revision(value)


class WantedPage(PageQuery):
    """Accept exact HTTP integers and reject offsets beyond PostgreSQL bigint."""

    @field_validator("page", "page_size", mode="before")
    @classmethod
    def exact_integer(cls, value: Any) -> Any:
        """Permit integer query strings, but not booleans/floats/coercion."""
        if isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+", value):
            value = int(value)
        if type(value) is not int:
            raise ValueError("Integer page required")
        return value

    @model_validator(mode="after")
    def bounded_offset(self) -> "WantedPage":
        """Keep numbered pagination within the storage offset domain."""
        if (self.page - 1) * self.page_size > 2**63 - 1:
            raise ValueError("Page outside supported domain")
        return self


def owner_view(row: dict[str, Any], label: str) -> WantedRequestOwnerView:
    """Select only reviewed fields; author/pending/retirement data never escape."""
    return WantedRequestOwnerView(
        request_id=row["id"],
        title=row["title"],
        description=row["description"],
        category_code=row["category_code"],
        category_label=label,
        budget_paise=row["budget_paise"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        state=row["status"],
        revision=row["revision"],
    )


def public_view(view: WantedRequestOwnerView) -> WantedRequestPublic:
    """Strip owner-only state/revision even when the caller authored an open row."""
    return WantedRequestPublic.model_validate(
        view.model_dump(exclude={"state", "revision"})
    )


class DraftTitle(DraftMatchRequest):
    """Transient title only; apply the reviewed trim-before-limit validation."""

    @field_validator("draft_title", mode="before")
    @classmethod
    def trimmed_title(cls, value: Any) -> Any:
        """Blank is invalid; padding does not consume the120-character limit."""
        return value.strip() if isinstance(value, str) else value
