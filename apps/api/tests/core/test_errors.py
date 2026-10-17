"""Safe public errors through the actual FastAPI exception boundary."""

import json
from typing import Annotated

from fastapi import HTTPException, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, StrictInt
import pytest
from starlette.requests import Request

from app.core.errors import ERRORS, ErrorSpec, FieldError, PublicError, error_response
from app.core.identifiers import parse_id

SENTINEL = "synthetic-private-value"


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "bad_request"),
        (401, "unauthenticated"),
        (403, "forbidden"),
        (404, "not_found"),
        (405, "method_not_allowed"),
        (409, "conflict"),
        (422, "validation_error"),
        (429, "rate_limited"),
        (500, "internal_error"),
        (503, "dependency_unavailable"),
        (418, "request_failed"),
    ],
)
def test_http_errors_use_stable_codes_without_raw_detail(core_app, status, code):
    """Exception text is replaced; only approved protocol headers survive."""

    @core_app.get("/error")
    async def fail():
        """Raise synthetic framework errors in a test-owned route."""
        raise HTTPException(
            status,
            detail=SENTINEL,
            headers={
                "WWW-Authenticate": "Bearer",
                "Retry-After": "5",
                "Allow": "GET",
                "X-Private-Debug": SENTINEL,
            },
        )

    with TestClient(core_app) as client:
        response = client.get("/error")
    assert response.status_code == status
    body = response.json()
    assert body["error"]["code"] == code
    assert set(body["error"]) == {"code", "message"}
    assert parse_id(body["request_id"])
    assert body["request_id"] == response.headers["x-request-id"]
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["retry-after"] == "5"
    assert response.headers["allow"] == "GET"
    assert "x-private-debug" not in response.headers
    assert SENTINEL not in response.text


def test_reviewed_domain_error_has_safe_field_codes(core_app):
    """Domain error extensions preserve the shared envelope and safe metadata."""

    @core_app.get("/amount")
    async def amount():
        """Demonstrate the approved whole-rupee field-error contract."""
        raise PublicError(
            ERRORS[422], (FieldError("price_paise", "whole_rupees_required"),)
        )

    with TestClient(core_app) as client:
        response = client.get("/amount")
    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "price_paise", "code": "whole_rupees_required"}
    ]


def test_custom_domain_code_does_not_require_a_private_envelope(core_app):
    """Additional reviewed codes can use the common status/response mechanism."""

    @core_app.get("/state")
    async def state():
        """Use a synthetic state conflict unrelated to marketplace implementation."""
        raise PublicError(
            ErrorSpec(409, "synthetic_state_conflict", "Synthetic state conflict")
        )

    with TestClient(core_app) as client:
        response = client.get("/state")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "synthetic_state_conflict"


def test_unknown_route_and_method_use_common_envelope(core_app):
    """Framework-generated 404/405 responses cannot bypass standard errors."""

    @core_app.get("/known")
    async def known():
        """Supply only a temporary route for method handling."""
        return {"ok": True}

    with TestClient(core_app) as client:
        missing = client.get("/unknown")
        method = client.post("/known")
    assert missing.json()["error"]["code"] == "not_found"
    assert method.status_code == 405
    assert method.json()["error"]["code"] == "method_not_allowed"
    assert "GET" in method.headers["allow"]


class SyntheticPayload(BaseModel):
    """Deliberately strict synthetic fields for untrusted-value leakage checks."""

    amount: StrictInt
    attributes: dict[str, StrictInt]


@pytest.mark.parametrize("kind", ["fields", "malformed_json"])
def test_schema_errors_do_not_echo_private_values_or_map_keys(core_app, kind):
    """Nested validation locations may contain input keys; expose only body."""

    @core_app.post("/validate")
    async def validate(payload: SyntheticPayload):
        """Use real request validation and never return the synthetic payload."""
        return {"ok": True}

    with TestClient(core_app) as client:
        if kind == "fields":
            response = client.post(
                "/validate",
                json={"amount": SENTINEL, "attributes": {SENTINEL: SENTINEL}},
            )
        else:
            response = client.post(
                "/validate",
                content='{"amount":',
                headers={"Content-Type": "application/json"},
            )
    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "body", "code": "invalid_value"}
    ]
    assert SENTINEL not in response.text
    assert "input" not in response.json()["error"]


def test_query_validation_uses_safe_location(core_app):
    """Schema query errors do not echo invalid query values."""

    @core_app.get("/validate")
    async def validate(count: Annotated[int, Query(ge=1)]):
        """Bind an ordinary validated query parameter in the private test app."""
        return {"count": count}

    with TestClient(core_app) as client:
        response = client.get("/validate", params={"count": SENTINEL})
    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "query", "code": "invalid_value"}
    ]
    assert SENTINEL not in response.text


@pytest.mark.parametrize("debug", [False, True])
def test_unexpected_errors_are_safe_even_with_local_debug(core_app, debug, log_stream):
    """Unhandled exceptions produce a correlated safe 500 and no raw diagnostics."""
    core_app.debug = debug

    @core_app.get("/failure")
    async def failure():
        """Fail before response start with a synthetic private exception."""
        raise RuntimeError(SENTINEL)

    with TestClient(core_app) as client:
        response = client.get("/failure")
    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_error",
        "message": "Unexpected server error",
    }
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert SENTINEL not in response.text + log_stream.getvalue()
    assert any(
        json.loads(line)["event"] == "request_failed"
        for line in log_stream.getvalue().splitlines()
    )


def test_non_http_error_helper_can_omit_correlation():
    """A helper outside request middleware need not invent a correlation ID."""
    response = error_response(Request({"type": "http"}), ERRORS[409])
    assert json.loads(response.body) == {
        "error": {"code": "conflict", "message": "Resource state conflict"}
    }


@pytest.mark.parametrize("value", ["", "invalid field", "field\nvalue", "x" * 129])
def test_field_error_metadata_is_bounded_and_structural(value):
    """Reviewed field codes still reject malformed or oversized metadata."""
    with pytest.raises(ValueError):
        FieldError(value, "invalid_value")
    with pytest.raises(ValueError):
        FieldError("price_paise", value)
