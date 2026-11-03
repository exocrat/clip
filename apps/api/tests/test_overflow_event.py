"""Synthetic request conversion checks; no app, session, or AWS connection."""

import json

import pytest

from app.alb_event import parse_alb_read
from app.overflow_event import build_read_event, clean_ingress_headers

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
        (b"cookie", b"bad\x00value"),
    ],
)
def test_unsafe_headers_are_rejected(header):
    with pytest.raises(ValueError):
        build_read_event("GET", "/api/listings/id", b"", [header], TG)


def test_interleaved_query_keys_are_refused_instead_of_reordered():
    with pytest.raises(ValueError):
        build_read_event("GET", "/api/listings", b"a=1&b=2&a=3", [], TG)


def test_trusted_https_replaces_forwarding_claims():
    incoming = [
        (b"host", b"clip-iisc.site"),
        (b"cookie", b"synthetic=session"),
        (b"x-forwarded-proto", b"http"),
        (b"x-forwarded-for", b"spoofed"),
        (b"connection", b"keep-alive"),
    ]
    cleaned = clean_ingress_headers("https", incoming)
    event = json.loads(
        build_read_event("GET", "/api/listings", b"", cleaned, TG, trusted_https=True)
    )
    assert event["multiValueHeaders"]["x-forwarded-proto"] == ["https"]
    assert "x-forwarded-for" not in event["multiValueHeaders"]
    assert event["multiValueHeaders"]["cookie"] == ["synthetic=session"]


@pytest.mark.parametrize(
    "scheme,headers",
    [
        ("http", [(b"host", b"clip-iisc.site")]),
        ("https", [(b"host", b"attacker.invalid")]),
        ("https", [(b"host", b"clip-iisc.site"), (b"host", b"clip-iisc.site")]),
        ("https", [(b"host", b"clip-iisc.site"), (b"connection", b"cookie")]),
    ],
)
def test_trusted_ingress_rejects_bad_scheme_host_and_connection(scheme, headers):
    with pytest.raises(ValueError):
        clean_ingress_headers(scheme, headers)


def test_trusted_event_requires_exact_single_host():
    with pytest.raises(ValueError):
        build_read_event("GET", "/api/listings", b"", [], TG, trusted_https=True)
