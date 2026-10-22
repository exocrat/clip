"""Validate public prekey wire models without implementing crypto behavior."""

import base64

import pytest
from pydantic import ValidationError

from contracts.source.types import (
    MemberPreKeyBundle,
    PublicPreKeyBatchRequest,
    PublicKeyBundleRequest,
    PublicPreKeyMaterial,
)


def test_public_prekey_material_enforces_open_e2ee_signature_shape():
    """KEM OTPs are identity-signed; EC OTPs carry no separate signature."""
    ec_public = base64.b64encode(b"e" * 32).decode("ascii")
    kem_public = base64.b64encode(b"k" * 1569).decode("ascii")
    signature = base64.b64encode(b"s" * 64).decode("ascii")
    ec_prekey = PublicPreKeyMaterial(
        key_type="ecPreKey", key_id=1, public_key_base64=ec_public
    )
    kem_prekey = PublicPreKeyMaterial(
        key_type="kemOneTimePreKey",
        key_id=2,
        public_key_base64=kem_public,
        signature_base64=signature,
    )

    assert ec_prekey.key_type == "ecPreKey"
    assert kem_prekey.signature_base64 == signature
    assert ec_public not in repr(ec_prekey)
    assert signature not in repr(kem_prekey)

    with pytest.raises(ValidationError):
        PublicPreKeyMaterial(
            key_type="kemOneTimePreKey",
            key_id=3,
            public_key_base64=kem_public,
        )
    with pytest.raises(ValidationError):
        PublicPreKeyMaterial(
            key_type="ecPreKey",
            key_id=4,
            public_key_base64=ec_public,
            signature_base64=signature,
        )
    with pytest.raises(ValidationError):
        PublicPreKeyMaterial(
            key_type="ecPreKey", key_id=5, public_key_base64="not-base64!"
        )
    with pytest.raises(ValidationError):
        PublicPreKeyMaterial(
            key_type="ecPreKey",
            key_id=6,
            public_key_base64=base64.b64encode(b"short").decode("ascii"),
        )


def test_prekey_batch_rejects_duplicate_ids_and_limits_batch_size():
    """A batch has bounded unique IDs so publication can be all-or-none."""
    ec_public = base64.b64encode(b"e" * 32).decode("ascii")
    prekey = {
        "key_type": "ecPreKey",
        "key_id": 7,
        "public_key_base64": ec_public,
    }
    request = PublicPreKeyBatchRequest(
        key_version=1,
        prekeys=[prekey],
        operation_id="00000000-0000-4000-8000-000000000001",
    )
    assert len(request.prekeys) == 1

    with pytest.raises(ValidationError):
        PublicPreKeyBatchRequest(
            key_version=1,
            prekeys=[prekey, prekey],
            operation_id="00000000-0000-4000-8000-000000000002",
        )
    with pytest.raises(ValidationError):
        PublicPreKeyBatchRequest(
            key_version=1,
            prekeys=[prekey] * 201,
            operation_id="00000000-0000-4000-8000-000000000003",
        )


def test_member_prekey_response_accepts_only_matching_optional_key_types():
    """The selected EC and KEM response slots cannot be swapped by callers."""
    from uuid import uuid4

    ec_public = base64.b64encode(b"e" * 32).decode("ascii")
    ed_public = base64.b64encode(b"d" * 32).decode("ascii")
    kem_public = base64.b64encode(b"k" * 1569).decode("ascii")
    signature = base64.b64encode(b"s" * 64).decode("ascii")
    common = {
        "key_bundle": {
            "user_id": uuid4(),
            "protocol_id": "open-e2ee-signal",
            "protocol_version": "13.0.0",
            "key_version": 1,
            "registration_id": 1,
            "device_id": 1,
            "identity": {
                "version": 1,
                "x25519_public_key_base64": ec_public,
                "ed25519_public_key_base64": ed_public,
            },
            "ec_signed_prekey": {
                "key_id": 1,
                "public_key_base64": ec_public,
                "signature_base64": signature,
            },
            "kem_last_resort_prekey": {
                "key_id": 2,
                "public_key_base64": kem_public,
                "signature_base64": signature,
            },
        },
        "registration_id": 1,
        "device_id": 1,
    }
    ec = {
        "key_type": "ecPreKey",
        "key_id": 8,
        "public_key_base64": ec_public,
    }
    kem = {
        "key_type": "kemOneTimePreKey",
        "key_id": 9,
        "public_key_base64": kem_public,
        "signature_base64": signature,
    }

    assert MemberPreKeyBundle(**common, ec_one_time_prekey=ec, kem_one_time_prekey=kem)
    with pytest.raises(ValidationError):
        MemberPreKeyBundle(**common, ec_one_time_prekey=kem)
    with pytest.raises(ValidationError):
        MemberPreKeyBundle(**common, kem_one_time_prekey=ec)
    with pytest.raises(ValidationError):
        MemberPreKeyBundle(**{**common, "registration_id": 2})


def test_public_key_registration_uses_explicit_sdk_material_and_exact_lengths():
    """Registration exposes SDK bundle parts and rejects malformed key bytes."""
    key32 = base64.b64encode(b"x" * 32).decode("ascii")
    kem_key = base64.b64encode(b"k" * 1569).decode("ascii")
    signature = base64.b64encode(b"s" * 64).decode("ascii")
    bundle = {
        "protocol_id": "open-e2ee-signal",
        "protocol_version": "13.0.0",
        "registration_id": 7,
        "device_id": 1,
        "identity": {
            "version": 1,
            "x25519_public_key_base64": key32,
            "ed25519_public_key_base64": key32,
        },
        "ec_signed_prekey": {
            "key_id": 8,
            "public_key_base64": key32,
            "signature_base64": signature,
        },
        "kem_last_resort_prekey": {
            "key_id": 9,
            "public_key_base64": kem_key,
            "signature_base64": signature,
        },
        "operation_id": "00000000-0000-4000-8000-000000000004",
    }

    request = PublicKeyBundleRequest(**bundle)
    assert request.identity.version == 1
    assert key32 not in repr(request)

    invalid_identity = {
        **bundle,
        "identity": {
            "version": 1,
            "x25519_public_key_base64": base64.b64encode(b"short").decode("ascii"),
            "ed25519_public_key_base64": key32,
        },
    }
    with pytest.raises(ValidationError):
        PublicKeyBundleRequest(**invalid_identity)
