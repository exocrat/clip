"""Validate OpenE2EE relay metadata and CLIP entry classification."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from contracts.source.types import (
    CipherEnvelope,
    ContactShareRequest,
    ConversationEntry,
    OfferRevisionRequest,
)


def _envelope(**overrides):
    values = {
        "protocol_id": "open-e2ee-signal",
        "protocol_version": "13.0.0",
        "envelope_version": 1,
        "sdk_message_type": "ciphertext",
        "client_timestamp_ms": 1_797_000_000_000,
        "sender_key_version": 1,
        "recipient_key_version": 2,
        "payload_base64": "AQID",
    }
    values.update(overrides)
    return CipherEnvelope(**values)


def test_encrypted_sdk_message_requires_timestamp_and_both_key_versions():
    envelope = _envelope()
    assert envelope.client_timestamp_ms == 1_797_000_000_000
    assert envelope.sdk_message_type == "ciphertext"

    with pytest.raises(ValidationError):
        _envelope(sender_key_version=None)
    with pytest.raises(ValidationError):
        _envelope(client_timestamp_ms=True)
    with pytest.raises(ValidationError):
        _envelope(client_timestamp_ms=1.5)


def test_retry_request_is_unencrypted_control_without_key_versions():
    envelope = _envelope(
        sdk_message_type="retry_request",
        sender_key_version=None,
        recipient_key_version=None,
    )
    assert envelope.payload_base64 == "AQID"

    with pytest.raises(ValidationError):
        _envelope(sdk_message_type="retry_request")


def test_one_to_one_contract_rejects_unsupported_sdk_envelope_types():
    with pytest.raises(ValidationError):
        _envelope(sdk_message_type="sender_key")
    with pytest.raises(ValidationError):
        _envelope(sdk_message_type="unidentified_sender")


def test_protocol_control_is_a_sequenced_conversation_entry():
    entry = ConversationEntry(
        entry_id="00000000-0000-4000-8000-000000000001",
        sequence=1,
        kind="protocol_control",
        sender_user_id="00000000-0000-4000-8000-000000000002",
        created_at="2026-10-22T12:00:00.000000Z",
        envelope=_envelope(
            sdk_message_type="retry_request",
            sender_key_version=None,
            recipient_key_version=None,
        ),
    )
    assert entry.kind == "protocol_control"
    with pytest.raises(ValidationError):
        ConversationEntry(
            entry_id="00000000-0000-4000-8000-000000000003",
            sequence=2,
            kind="message",
            sender_user_id="00000000-0000-4000-8000-000000000002",
            created_at="2026-10-22T12:00:00.000000Z",
            envelope=entry.envelope,
        )


def test_non_message_content_accepts_only_encrypted_ciphertext_envelopes():
    retry_control = _envelope(
        sdk_message_type="retry_request",
        sender_key_version=None,
        recipient_key_version=None,
    )
    with pytest.raises(ValidationError):
        ContactShareRequest(envelope=retry_control, operation_id=uuid4())
    with pytest.raises(ValidationError):
        OfferRevisionRequest(
            amount_paise=100,
            note_envelope=retry_control,
            operation_id=uuid4(),
        )
