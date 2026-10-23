"""Shared numbered-page bounds and response construction over ordered results."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Generic, Literal, TypeVar, cast

from fastapi import Query

from app.core.errors import ERRORS, FieldError, PublicError

T = TypeVar("T")


@dataclass(frozen=True)
class PageRequest:
    """Validated page coordinates; callers must filter/authorize before slicing."""

    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        """Reject coercion and unsupported sizes before building a DB offset."""
        if type(self.page) is not int or self.page < 1:
            raise ValueError("Page must be a positive integer")
        if type(self.page_size) is not int or self.page_size not in (20, 50, 100):
            raise ValueError("Page size must be 20, 50, or 100")

    @property
    def offset(self) -> int:
        """Return the zero-based offset; this is not a snapshot guarantee."""
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class Page(Generic[T]):
    """Framework-independent response; items retain the owning query's order."""

    items: tuple[T, ...]
    page: int
    page_size: Literal[20, 50, 100]
    has_next: bool


def page_from_window(request: PageRequest, rows: Sequence[T]) -> Page[T]:
    """Build a page from at most size+1 ordered, already-offset query results.

    Fetching one extra authorized row determines has_next without a count query.
    Domain queries own sorting/tie-breaks, filtering and SQL parameterization.
    """
    if len(rows) > request.page_size + 1:
        raise ValueError("Expected at most page_size + 1 rows")
    return Page(
        tuple(rows[: request.page_size]),
        request.page,
        cast(Literal[20, 50, 100], request.page_size),
        len(rows) > request.page_size,
    )


def page_parameters(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query()] = 20,
) -> PageRequest:
    """FastAPI dependency translating invalid page sizes to the shared 422 envelope.

    FastAPI parses query integers; PageRequest separately protects internal calls.
    No domain routes are added by defining this dependency.
    """
    try:
        return PageRequest(page=page, page_size=page_size)
    except ValueError:
        raise PublicError(
            ERRORS[422], (FieldError("page_size", "unsupported_page_size"),)
        ) from None
