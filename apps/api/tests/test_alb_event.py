"""Offline checks for parsing synthetic ALB request events."""

import pytest

from app.alb_event import parse_alb_read


def event():
    return {
        "httpMethod": "GET",
        "path": "/api/listings",
        "multiValueHeaders": {"Host": ["example.invalid"], "Cookie": ["synthetic=1"]},
        "multiValueQueryStringParameters": {
            "category": ["books", "music"],
            "q": ["red%20bike"],
        },
        "body": None,
    }


def test_preserves_repeated_query_and_headers():
    result = parse_alb_read(event())
    assert result.query_string == b"category=books&category=music&q=red+bike"
    assert (b"cookie", b"synthetic=1") in result.headers


@pytest.mark.parametrize(
    "field,value",
    [
        ("httpMethod", "POST"),
        ("body", "x"),
        ("path", "other"),
        ("multiValueHeaders", None),
    ],
)
def test_rejects_malformed_or_non_read_requests(field, value):
    request = event()
    request[field] = value
    with pytest.raises(ValueError, match="Invalid ALB read request"):
        parse_alb_read(request)


def test_rejects_header_injection():
    request = event()
    request["multiValueHeaders"] = {"x-test": ["ok\r\ninjected"]}
    with pytest.raises(ValueError):
        parse_alb_read(request)


def test_request_representation_omits_cookie():
    assert "synthetic=1" not in repr(parse_alb_read(event()))


@pytest.mark.parametrize("name", ["bad header", "x-test\r\ninjected"])
def test_rejects_invalid_header_names(name):
    request = event()
    request["multiValueHeaders"] = {name: ["value"]}
    with pytest.raises(ValueError):
        parse_alb_read(request)


def test_rejects_non_mapping_query_even_if_empty():
    request = event()
    request["multiValueQueryStringParameters"] = []
    with pytest.raises(ValueError):
        parse_alb_read(request)
