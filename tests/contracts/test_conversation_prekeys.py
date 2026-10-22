"""Validate public prekey wire models without implementing crypto behavior."""

import pytest
from pydantic import ValidationError

from contracts.source.types import (
    MemberPreKeyBundle,
    PublicPreKeyBatchRequest,
    PublicPreKeyMaterial,
)


def test_public_prekey_material_enforces_open_e2ee_signature_shape():
    """KEM OTPs are identity-signed; EC OTPs carry no separate signature."""
    ec_prekey = PublicPreKeyMaterial(
        key_type="ecPreKey", key_id=1, public_key_base64="cHVi"
    )
    kem_prekey = PublicPreKeyMaterial(
        key_type="kemOneTimePreKey",
        key_id=2,
        public_key_base64="cHVi",
        signature_base64="c2ln",
    )

    assert ec_prekey.key_type == "ecPreKey"
    assert kem_prekey.signature_base64 == "c2ln"
    assert "cHVi" not in repr(ec_prekey)
    assert "c2ln" not in repr(kem_prekey)

    with pytest.raises(ValidationError):
        PublicPreKeyMaterial(
            key_type="kemOneTimePreKey", key_id=3, public_key_base64="cHVi"
        )
    with pytest.raises(ValidationError):
        PublicPreKeyMaterial(
            key_type="ecPreKey",
            key_id=4,
            public_key_base64="cHVi",
            signature_base64="c2ln",
        )
    with pytest.raises(ValidationError):
        PublicPreKeyMaterial(
            key_type="ecPreKey", key_id=5, public_key_base64="not-base64!"
        )


def test_prekey_batch_rejects_duplicate_ids_and_limits_batch_size():
    """A batch has bounded unique IDs so publication can be all-or-none."""
    prekey = {
        "key_type": "ecPreKey",
        "key_id": 7,
        "public_key_base64": "cHVi",
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

    common = {
        "key_bundle": {
            "user_id": uuid4(),
            "protocol_id": "open-e2ee-signal",
            "protocol_version": "13.0.0",
            "key_version": 1,
            "bundle_base64": "cHVibGljLWJ1bmRsZQ==",
        },
        "registration_id": 1,
        "device_id": 1,
    }
    ec = {"key_type": "ecPreKey", "key_id": 8, "public_key_base64": "cHVi"}
    kem = {
        "key_type": "kemOneTimePreKey",
        "key_id": 9,
        "public_key_base64": "cHVi",
        "signature_base64": "c2ln",
    }

    assert MemberPreKeyBundle(**common, ec_one_time_prekey=ec, kem_one_time_prekey=kem)
    with pytest.raises(ValidationError):
        MemberPreKeyBundle(**common, ec_one_time_prekey=kem)
    with pytest.raises(ValidationError):
        MemberPreKeyBundle(**common, kem_one_time_prekey=ec)
