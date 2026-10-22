"""Contract-boundary checks for the bounded opaque message transport."""

from base64 import b64encode
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.contracts.domain_types import CipherEnvelope, MessageRequest


def envelope(**overrides) -> dict:
    """Build a deterministic synthetic SDK envelope without real key material."""
    return {
        "protocol_id": "open-e2ee-signal",
        "protocol_version": "13.0.0",
        "envelope_version": 1,
        "sdk_message_type": "ciphertext",
        "client_timestamp_ms": 1_797_000_000_000,
        "sender_key_version": 1,
        "recipient_key_version": 1,
        "payload_base64": b64encode(b"synthetic opaque bytes").decode("ascii"),
        **overrides,
    }


def test_cipher_envelope_accepts_canonical_bounded_payload_only():
    parsed = CipherEnvelope(**envelope())
    assert parsed.payload_base64 == b64encode(b"synthetic opaque bytes").decode("ascii")

    for payload in ("not base64!", "YQ", b64encode(b"x" * 65537).decode("ascii")):
        with pytest.raises(ValidationError):
            CipherEnvelope(**envelope(payload_base64=payload))


@pytest.mark.parametrize(
    "change",
    [
        {"protocol_id": "other"},
        {"protocol_version": "13.0.1"},
        {"envelope_version": 2},
        {"sdk_message_type": "retry_request", "sender_key_version": 1},
    ],
)
def test_cipher_envelope_rejects_unsupported_or_inconsistent_metadata(change):
    with pytest.raises(ValidationError):
        CipherEnvelope(**envelope(**change))


def test_message_request_requires_a_uuid_v4_retry_key():
    request = MessageRequest(
        envelope=CipherEnvelope(**envelope()), operation_id=uuid4()
    )
    assert request.operation_id.version == 4
    with pytest.raises(ValidationError):
        MessageRequest(
            envelope=CipherEnvelope(**envelope()),
            operation_id="00000000-0000-0000-0000-000000000000",
        )


def test_retry_control_requires_null_key_references():
    control = CipherEnvelope(
        **envelope(
            sdk_message_type="retry_request",
            sender_key_version=None,
            recipient_key_version=None,
        )
    )
    assert control.sdk_message_type == "retry_request"
