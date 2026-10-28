"""Explicit loopback-only UI transport fixtures, never a Search implementation.

The normal app never imports this module. No PostgreSQL/authentication/storage
is provided. Named query scripts and simple fixture selection let the human
inspect controls/states; they do not prove SQL matching, ranking or acceptance.
"""

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import os
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "apps/api"))
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Request, Response  # noqa: E402
from pydantic import ValidationError  # noqa: E402
import uvicorn  # noqa: E402

from app.contracts.domain_types import (
    CatalogueView,
    Category,
    ListingQuery,
    ListingSummary,
    PageResult,
)  # noqa: E402
from app.core.errors import (
    ERRORS,
    PublicError,
    error_response,
    install_error_handlers,
)  # noqa: E402

CATEGORIES = (
    ("mobile_phone", "Mobile Phones"),
    ("laptop", "Laptops"),
    ("electronics", "Electronics"),
    ("furniture", "Furniture"),
    ("books", "Books and Study Materials"),
    ("bicycles", "Bicycles"),
    ("appliances", "Home Appliances"),
    ("sports_fitness", "Sports & Fitness"),
    ("other", "Other"),
)
CONDITIONS = (
    ("new", "New / Unused"),
    ("like_new", "Like New"),
    ("good", "Good"),
    ("fair", "Fair"),
)


def require_preview_settings(isolated: bool) -> None:
    """Require explicit test opt-in and refuse ambient database/provider targets."""
    if (
        not isolated
        or os.environ.get("CLIP_ENVIRONMENT") != "test"
        or os.environ.get("CLIP_DEVELOPMENT_AUTH") != "true"
        or os.environ.get("CLIP_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or any(key.startswith("AWS_") for key in os.environ)
    ):
        raise ValueError(
            "Use explicit isolated test settings without database/AWS configuration"
        )


def fixture_rows() -> list[ListingSummary]:
    """Return public synthetic text-only fixture summaries, with no real image keys."""
    rows = []
    example_titles = {
        "mobile_phone": "mobile phone",
        "laptop": "student laptop",
        "electronics": "desk monitor",
        "furniture": "study desk",
        "books": "linear algebra textbook",
        "bicycles": "campus bicycle",
        "appliances": "electric kettle",
        "sports_fitness": "badminton racket",
        "other": "student backpack",
    }
    for index in range(42):
        code, label = CATEGORIES[index % len(CATEGORIES)]
        title = example_titles[code]
        condition, condition_label = CONDITIONS[index % 4]
        rows.append(
            ListingSummary(
                listing_id=UUID(int=index + 1, version=4),
                title=f"Synthetic {title} {index+1}",
                description="Synthetic UI fixture for inspecting campus listings. No real item is for sale.",
                category_code=code,
                category_label=label,
                condition_code=condition,
                condition_label=condition_label,
                asking_price_paise=0 if index == 0 else (index + 1) * 10000,
                original_price_paise=None,
                negotiable=bool(index % 2),
                pickup_area="Synthetic campus area",
                available_from=datetime(2026, 1, 1, tzinfo=UTC),
                available_until=None,
                availability="available",
                sensitive_purchase=False,
                image_ids=[],
            )
        )
    return rows


def create_preview_app() -> FastAPI:
    """Mount only labelled read-only fixtures behind local transport/header checks."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    install_error_handlers(app)
    rows = fixture_rows()
    attempts = 0

    @app.middleware("http")
    async def local_fixture_transport(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Default/production clients cannot accidentally consume these fake responses."""
        origin = request.headers.get("origin")
        if (
            request.client is None
            or request.client.host not in {"127.0.0.1", "::1", "testclient"}
            or request.headers.get("x-clip-ui-preview") != "search-fixtures"
            or (origin is not None and origin != "http://127.0.0.1:5173")
        ):
            return error_response(request, ERRORS[403])
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Clip-Preview"] = "search-ui-fixtures"
        return response

    @app.get("/catalogue", response_model=CatalogueView)
    async def catalogue() -> CatalogueView:
        """Return the reviewed catalogue vocabulary as test data, not a live provider."""
        return CatalogueView(
            categories=[Category(code=code, label=label) for code, label in CATEGORIES],
            conditions=[Category(code=code, label=label) for code, label in CONDITIONS],
        )

    @app.get("/listings", response_model=None)
    async def scripted_page(
        request: Request,
    ) -> PageResult[ListingSummary] | dict[str, bool]:
        """Select named UI scripts; this deliberately has no general text-search engine."""
        nonlocal attempts
        values: dict[str, str | int | list[str]] = dict(request.query_params)
        for name in ("category_code", "condition_code"):
            selected = request.query_params.getlist(name)
            if selected:
                values[name] = selected
        try:
            for name in ("page", "page_size"):
                if name in values:
                    values[name] = int(values[name])
            query = ListingQuery.model_validate(values)
        except ValueError, ValidationError:
            raise PublicError(ERRORS[422]) from None
        text = (query.q or "").strip().lower()
        if query.sort == "relevance" and not text:
            raise PublicError(ERRORS[422])
        # Explicit scripted Hybrid outage permits inspecting Keyword recovery;
        # this is not a real helper, semantic match or rank implementation.
        if text == "hybrid-down" and query.search_mode == "hybrid":
            raise PublicError(ERRORS[503])
        if text in {"denied", "expired", "unavailable"}:
            raise PublicError(
                ERRORS[{"denied": 403, "expired": 401, "unavailable": 503}[text]]
            )
        if text == "retry":
            attempts += 1
            if attempts == 1:
                raise PublicError(ERRORS[503])
        if text == "slow":
            await asyncio.sleep(1.5)
        if text == "malformed":
            return {"not_a_listing_page": True}
        # Transport-only fixture cases, not English stemming/ranking/SQL evidence.
        groups = {"bicycle": "bicycles", "books": "books", "desk": "furniture"}
        selected = (
            list(rows)
            if text in {"", "slow", "retry", "hybrid-down"}
            else [row for row in rows if row.category_code == groups.get(text)]
        )
        if any(code not in dict(CATEGORIES) for code in query.category_code):
            raise PublicError(ERRORS[422])
        if any(code not in dict(CONDITIONS) for code in query.condition_code):
            raise PublicError(ERRORS[422])
        if (
            query.min_price_paise is not None
            and query.max_price_paise is not None
            and query.min_price_paise > query.max_price_paise
        ):
            raise PublicError(ERRORS[422])
        selected = [
            row
            for row in selected
            if (not query.category_code or row.category_code in query.category_code)
            and (not query.condition_code or row.condition_code in query.condition_code)
            and (
                query.min_price_paise is None
                or row.asking_price_paise >= query.min_price_paise
            )
            and (
                query.max_price_paise is None
                or row.asking_price_paise <= query.max_price_paise
            )
            and (query.negotiable is None or row.negotiable == query.negotiable)
        ]
        selected.sort(
            key=(
                (lambda row: row.listing_id)
                if query.sort in {"created_desc", "relevance"}
                else (lambda row: (row.asking_price_paise, row.listing_id))
            ),
            reverse=query.sort in {"created_desc", "price_desc"},
        )
        start = (query.page - 1) * query.page_size
        return PageResult[ListingSummary](
            items=selected[start : start + query.page_size],
            page=query.page,
            page_size=query.page_size,
            has_next=start + query.page_size < len(selected),
        )

    return app


def main() -> None:
    """Start only fixed loopback port 8000; never select shared infrastructure."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--isolated-search-ui", action="store_true")
    args = parser.parse_args()
    try:
        require_preview_settings(args.isolated_search_ui)
    except ValueError as error:
        parser.error(str(error))
    print(
        "ISOLATED UI FIXTURES ONLY: no PostgreSQL, real auth, storage or NFR evidence.",
        flush=True,
    )
    uvicorn.run(
        create_preview_app(),
        host="127.0.0.1",
        port=8000,
        access_log=False,
        proxy_headers=False,
    )


if __name__ == "__main__":
    main()
