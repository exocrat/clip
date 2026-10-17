"""Page-size, wire-shape, bounds and static ordering contracts."""

from dataclasses import FrozenInstanceError
from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient
import pytest

from app.core.pagination import PageRequest, page_from_window, page_parameters


@pytest.mark.parametrize("size", [20, 50, 100])
def test_paging_preserves_static_order_without_losing_tied_rows(size):
    """Preserve sorted windows; future SQL ordering/auth/snapshots are separate."""
    ordered = [(index // 3, index) for index in range(137)]
    collected = []
    page = 1
    while True:
        request = PageRequest(page, size)
        result = page_from_window(
            request, ordered[request.offset : request.offset + size + 1]
        )
        assert result.page == page and result.page_size == size
        collected.extend(result.items)
        if not result.has_next:
            break
        page += 1
    assert collected == ordered
    assert page_from_window(PageRequest(page + 1, size), []).items == ()


@pytest.mark.parametrize(
    ("count", "has_next"), [(0, False), (19, False), (20, False), (21, True)]
)
def test_extra_row_only_controls_continuation(count, has_next):
    """Lookahead never leaks an extra row or invents a continuation."""
    result = page_from_window(PageRequest(), list(range(count)))
    assert result.items == tuple(range(min(count, 20)))
    assert result.has_next is has_next


@pytest.mark.parametrize(
    ("page", "size"),
    [
        (0, 20),
        (-1, 20),
        (True, 20),
        (1.0, 20),
        ("1", 20),
        (1, True),
        (1, 30),
        (1, 101),
        (1, "20"),
    ],
)
def test_internal_page_coordinates_are_strict(page, size):
    """Internal code cannot bypass supported bounds through coercion."""
    with pytest.raises(ValueError):
        PageRequest(page, size)


def test_page_request_is_immutable_and_oversized_window_fails():
    """Coordinates stay fixed; an unbounded query window is not silently sliced."""
    request = PageRequest()
    assert request.offset == 0
    with pytest.raises(FrozenInstanceError):
        request.page = 2
    with pytest.raises(ValueError):
        page_from_window(request, list(range(22)))


@pytest.mark.parametrize(
    ("query", "page", "size"),
    [("", 1, 20), ("?page=2&page_size=50", 2, 50), ("?page=3&page_size=100", 3, 100)],
)
def test_http_page_shape_and_query_conversion(core_app, query, page, size):
    """Real dependency parsing uses the shared page response shape."""

    @core_app.get("/pages")
    async def pages(parameters: Annotated[PageRequest, Depends(page_parameters)]):
        """Expose only a temporary test-owned list operation."""
        return page_from_window(parameters, [])

    with TestClient(core_app) as client:
        response = client.get("/pages" + query)
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": page,
        "page_size": size,
        "has_next": False,
    }


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=-1",
        "page=not-an-integer",
        "page_size=0",
        "page_size=30",
        "page_size=101",
        "page_size=20.5",
    ],
)
def test_invalid_http_page_input_has_shared_422(core_app, query):
    """Invalid public coordinates return the shared envelope, not a server error."""

    @core_app.get("/pages")
    async def pages(parameters: Annotated[PageRequest, Depends(page_parameters)]):
        """Bind shared validation without implementing domain behavior."""
        return page_from_window(parameters, [])

    with TestClient(core_app) as client:
        response = client.get("/pages?" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["request_id"] == response.headers["x-request-id"]
