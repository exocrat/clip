"""Prevent temporary startup diagnostics from leaking into measured runs."""

from copy import deepcopy

import pytest

from scripts.evaluation.k6.real_target_preflight import verify_lambda_startup


def configuration():
    """AWS configuration metadata only; no credentials or live cloud access."""
    return {
        "Timeout": 5,
        "LastUpdateStatus": "Successful",
        "Environment": {"Variables": {"AWS_LWA_ASYNC_INIT": "true"}},
    }


def test_async_startup_preserves_reviewed_image_and_five_second_deadline():
    verify_lambda_startup(configuration())
    value = configuration()
    value["ImageConfigResponse"] = {"ImageConfig": {"Command": [], "EntryPoint": []}}
    verify_lambda_startup(value)


@pytest.mark.parametrize(
    "change",
    [
        {"Timeout": 30},
        {"Timeout": None},
        {"LastUpdateStatus": "InProgress"},
        {"Environment": {"Variables": {}}},
        {"Environment": {"Variables": {"AWS_LWA_ASYNC_INIT": "false"}}},
        {"ImageConfigResponse": {"Error": {"ErrorCode": "InvalidImage"}}},
        {"ImageConfigResponse": {"ImageConfig": {"Command": ["python", "trace.py"]}}},
        {"ImageConfigResponse": {"ImageConfig": {"EntryPoint": ["wrapper"]}}},
        {"ImageConfigResponse": {"ImageConfig": {"WorkingDirectory": "/tmp"}}},
    ],
)
def test_diagnostic_or_drifted_configuration_is_rejected(change):
    value = deepcopy(configuration())
    value.update(change)
    with pytest.raises(ValueError, match="lambda_startup_configuration_mismatch"):
        verify_lambda_startup(value)
