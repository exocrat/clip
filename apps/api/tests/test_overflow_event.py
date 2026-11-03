"""Synthetic request conversion checks; no app, session, or AWS connection."""

import json

import pytest

from app.alb_event import parse_alb_read
from app.overflow_event import build_read_event

TG = "arn:aws:elasticloadbalancing:ap-south-1:335523638354:targetgroup/clip-exp03-test001-lambda/0123456789abcdef"


def test_repeated_query_and_private_headers_survive_local_roundtrip():
    encoded = build_read_event(
        "GET",
        "/api/listings",
        b"category=a&category=b&q=red%2Bbike",
        [(b"host", b"clip-iisc.site"), (b"cookie", b"synthetic=private")],
        TG,
    )
    event = json.loads(encoded)
    assert event["multiValueQueryStringParameters"]["category"] == ["a", "b"]
    parsed = parse_alb_read(event)
    assert parsed.query_string == b"category=a&category=b&q=red%2Bbike"
    assert (b"cookie", b"synthetic=private") in parsed.headers


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/listings"),
        ("GET", "/api/listings/id/extra"),
        ("GET", "/api/conversations"),
    ],
)
def test_only_selected_reads_are_accepted(method, path):
    with pytest.raises(ValueError):
        build_read_event(method, path, b"", [], TG)


@pytest.mark.parametrize(
    "header",
    [
        (b"x-forwarded-proto", b"https"),
        (b"connection", b"close"),
        (b"cookie", b"bad\r\nvalue"),
    ],
)
def test_unsafe_headers_are_rejected(header):
    with pytest.raises(ValueError):
        build_read_event("GET", "/api/listings/id", b"", [header], TG)
