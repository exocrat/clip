"""Offline checks for the guarded shared email-provider switch."""

import json
import pytest

from scripts.cn03_ses_primary import EmailRouteRefused, NAME, set_ses_primary


def test_ses_primary_preserves_secret_and_verifies_version():
    """Only the selector changes, and the next version is read back."""
    document = {"version": 1, "primary": "resend", "resend_api_key": "synthetic-key"}
    state = {
        "Name": NAME,
        "Type": "SecureString",
        "Version": 1,
        "Value": json.dumps(document),
    }

    def read():
        return {"Parameter": dict(state)}

    def write(payload):
        assert payload["Name"] == NAME and payload["Overwrite"] is True
        state.update(Version=2, Value=payload["Value"])
        return {"Version": 2}

    assert set_ses_primary(read, write, expected_version=1) == {
        "version": 2,
        "primary": "ses",
        "verified": True,
    }
    assert json.loads(state["Value"]) == {**document, "primary": "ses"}


def test_ses_primary_rejects_changed_version_before_write():
    """A stale or concurrently changed parameter must not be overwritten."""
    values = iter([1, 2])
    document = json.dumps(
        {"version": 1, "primary": "resend", "resend_api_key": "synthetic-key"}
    )

    def read():
        return {
            "Parameter": {
                "Name": NAME,
                "Type": "SecureString",
                "Version": next(values),
                "Value": document,
            }
        }

    def write(_payload):
        raise AssertionError("unexpected write")

    with pytest.raises(EmailRouteRefused):
        set_ses_primary(read, write, expected_version=1)
