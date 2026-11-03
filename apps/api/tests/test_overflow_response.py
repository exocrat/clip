"""Synthetic Lambda response parsing checks, without network or sessions."""

import base64
import json

import pytest

from app.overflow_response import parse_read_response


def encode(**overrides):
    event = {
        "statusCode": 200,
        "multiValueHeaders": {"set-cookie": ["a=synthetic", "b=synthetic"]},
        "isBase64Encoded": True,
        "body": base64.b64encode(b"private synthetic body").decode(),
    }
    event.update(overrides)
    return json.dumps(event).encode()


def test_parses_repeated_headers_without_exposing_body_in_repr():
    result = parse_read_response(encode())
    assert result.status == 200
    assert len(result.headers) == 2
    assert result.body == b"private synthetic body"
    assert "synthetic" not in repr(result)


@pytest.mark.parametrize(
    "changes",
    [
        {"statusCode": True},
        {"statusCode": 199},
        {"body": "!invalid!"},
        {"isBase64Encoded": "yes"},
        {"multiValueHeaders": {"transfer-encoding": ["chunked"]}},
        {"multiValueHeaders": {"x-test": ["hello\r\ninjection"]}},
    ],
)
def test_refuses_malformed_or_unsafe_response(changes):
    with pytest.raises(ValueError, match="Invalid Lambda read response"):
        parse_read_response(encode(**changes))


def test_preserves_non_success_status():
    assert parse_read_response(encode(statusCode=401)).status == 401


def test_discards_length_from_encoded_response():
    result = parse_read_response(encode(multiValueHeaders={"content-length": ["10"]}))
    assert result.headers == ()
