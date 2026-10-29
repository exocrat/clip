"""Optional pickup follows shared omitted/null/provided-text semantics."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.contracts.domain_types import CreateListingRequest, ListingReplacement


def request_fields():
    """Build safe fields shared by create and full replacement examples."""
    return dict(
        title="Synthetic book",
        description="Synthetic item",
        category_code="books",
        condition_code="good",
        asking_price_paise=0,
        original_price_paise=None,
        negotiable=False,
        image_upload_ids=[uuid4()],
        operation_id=uuid4(),
    )


def test_create_allows_omitted_null_and_supplied_pickup_area():
    """An unstated area has no manufactured default; existing supplied text remains valid."""
    assert CreateListingRequest(**request_fields()).pickup_area is None
    assert (
        CreateListingRequest(**request_fields(), pickup_area=None).pickup_area is None
    )
    assert (
        CreateListingRequest(
            **request_fields(), pickup_area="Synthetic area"
        ).pickup_area
        == "Synthetic area"
    )
    for invalid in ("", "x" * 121):
        with pytest.raises(ValidationError):
            CreateListingRequest(**request_fields(), pickup_area=invalid)


def test_replacement_requires_an_explicit_nullable_area():
    """A full replacement clears using null; omission is not a hidden partial update."""
    fields = request_fields() | dict(
        expected_revision=1,
        available_from="2026-10-21T00:00:00Z",
        available_until=None,
        proof_available=None,
        images=[{"source": "existing", "image_id": str(uuid4())}],
    )
    fields.pop("image_upload_ids")
    assert ListingReplacement(**fields, pickup_area=None).pickup_area is None
    with pytest.raises(ValidationError):
        ListingReplacement(**fields)


def test_replacement_accepts_an_ordered_mix_of_existing_and_new_images():
    """The wire list preserves explicit keep/add image identity and order."""
    fields = request_fields() | dict(
        expected_revision=1,
        available_from="2026-10-21T00:00:00Z",
        available_until=None,
        proof_available=None,
        pickup_area=None,
        images=[
            {"source": "existing", "image_id": str(uuid4())},
            {"source": "upload", "upload_id": str(uuid4())},
        ],
    )
    fields.pop("image_upload_ids")
    replacement = ListingReplacement(**fields)
    assert [image.source for image in replacement.images] == ["existing", "upload"]
    with pytest.raises(ValidationError):
        ListingReplacement(**(fields | {"images": []}))
