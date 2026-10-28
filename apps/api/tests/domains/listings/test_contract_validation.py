"""Check required Listings input and price boundaries with synthetic values."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.contracts.domain_types import CreateListingRequest, ListingReplacement


def _create_request(**updates: object) -> CreateListingRequest:
    values: dict[str, object] = {
        "title": "Synthetic item",
        "description": "A fixture used only for request validation.",
        "category_code": "books",
        "condition_code": "good",
        "asking_price_paise": 0,
        "negotiable": False,
        "available_from": datetime(2026, 10, 21, tzinfo=UTC),
        "image_upload_ids": [uuid4()],
        "operation_id": uuid4(),
    }
    return CreateListingRequest(**(values | updates))


def test_zero_price_and_omitted_proof_are_valid():
    request = _create_request()

    assert request.asking_price_paise == 0
    assert request.proof_available is None


@pytest.mark.parametrize("price", [-100, 1, 99, 101])
def test_create_rejects_negative_or_fractional_rupee_prices(price: int):
    with pytest.raises(ValidationError):
        _create_request(asking_price_paise=price)


@pytest.mark.parametrize(
    "changes",
    [
        {"title": ""},
        {"description": ""},
        {"category_code": None},
        {"condition_code": None},
        {"image_upload_ids": []},
        {"image_upload_ids": [uuid4() for _ in range(9)]},
        {"title": None},
    ],
    ids=[
        "empty-title",
        "empty-description",
        "missing-category",
        "missing-condition",
        "no-images",
        "too-many-images",
        "null-title",
    ],
)
def test_create_rejects_invalid_required_fields(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _create_request(**changes)


def test_create_rejects_a_missing_required_field():
    values = _create_request().model_dump()
    del values["description"]

    with pytest.raises(ValidationError):
        CreateListingRequest(**values)


def test_replacement_requires_an_explicit_nullable_proof_declaration():
    request = _create_request()
    replacement = ListingReplacement(
        expected_revision=1,
        title=request.title,
        description=request.description,
        category_code=request.category_code,
        condition_code=request.condition_code,
        asking_price_paise=0,
        original_price_paise=None,
        negotiable=False,
        pickup_area=None,
        available_from=request.available_from,
        available_until=None,
        proof_available=False,
        images=[{"source": "upload", "upload_id": request.image_upload_ids[0]}],
        operation_id=uuid4(),
    )

    assert replacement.proof_available is False

    values = replacement.model_dump()
    del values["proof_available"]
    with pytest.raises(ValidationError):
        ListingReplacement(**values)
