"""Runtime validation layered over the frozen generated Listings query type.

No generated declarations are edited. HTTP query strings must represent exact
integers, not floats/bools coerced to money or page coordinates. Text limits
apply after trimming, as specified by the reviewed Search contract.
"""

import re
from typing import Any

from pydantic import field_validator, model_validator, ValidationError

from app.contracts.domain_types import ListingQuery
from app.core.errors import ERRORS, FieldError, PublicError
from app.core.money import validate_paise


class BrowseQuery(ListingQuery):
    """Same public fields/schema with strict runtime parsing and cross-field checks."""

    @field_validator(
        "page", "page_size", "min_price_paise", "max_price_paise", mode="before"
    )
    @classmethod
    def exact_integer(cls, value: Any) -> int | None:
        """Accept integer query text; never round or accept bool/float amounts."""
        if value is None or type(value) is int:
            return value
        if isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+", value):
            try:
                return int(value)
            except ValueError:
                pass
        raise ValueError("Expected exact integer input")

    @field_validator("min_price_paise", "max_price_paise")
    @classmethod
    def whole_rupee_amount(cls, value: int | None) -> int | None:
        """Reuse shared money validation; the generated field also enforces >=0."""
        return validate_paise(value) if value is not None else None

    @field_validator("category_code", "condition_code")
    @classmethod
    def valid_selection_values(cls, values: list[str]) -> list[str]:
        """Reject blank/oversized codes before catalogue validation or SQL use."""
        if any(not value.strip() or len(value) > 100 for value in values):
            raise ValueError("Invalid catalogue selection")
        return values

    @field_validator("q", mode="before")
    @classmethod
    def trimmed_query(cls, value: Any) -> Any:
        """Trim before the inherited 120-code-point bound; blank means browse."""
        return (value.strip() or None) if isinstance(value, str) else value

    @model_validator(mode="after")
    def ordered_ranges(self) -> "BrowseQuery":
        """Reject reversed ranges and offsets outside PostgreSQL's integer domain."""
        if (
            self.min_price_paise is not None
            and self.max_price_paise is not None
            and self.min_price_paise > self.max_price_paise
        ):
            raise ValueError("Minimum price must not exceed maximum price")
        if self.sort == "relevance" and self.q is None:
            raise ValueError("Relevance requires nonblank search text")
        if (self.page - 1) * self.page_size > 2**63 - 1:
            raise ValueError("Page offset is outside the supported integer domain")
        return self


def normalize_query(request: ListingQuery) -> BrowseQuery:
    """Validate internal calls too, mapping errors to fixed, value-free metadata.

    Listings-owned input construction uses BrowseQuery for strict type checks.
    Other domains retain generated public types and validate raw inputs at their
    own boundary; they must not import this private runtime model. Coercion
    already performed by a generated model cannot recover original input types.
    """
    try:
        return BrowseQuery.model_validate(request.model_dump())
    except ValidationError:
        raise PublicError(
            ERRORS[422], (FieldError("query", "invalid_value"),)
        ) from None
