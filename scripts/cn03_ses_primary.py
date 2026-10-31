"""Guarded email-route update; import never reads secrets or contacts AWS.

The caller supplies an approved private SSM port. This helper preserves the
existing Resend key and refuses unexpected parameter versions or shapes.
"""

import json
from typing import Callable

NAME = "/clip/test/identity/email-delivery"


class EmailRouteRefused(Exception):
    """Sanitized refusal; never include parameter contents in an error."""


def set_ses_primary(
    read: Callable[[], dict], write: Callable[[dict], dict], *, expected_version: int
) -> dict:
    """Set only the primary selector, with checked version and verification.

    SSM has no compare-and-swap in this interface. A second read narrows the
    race but cannot eliminate concurrent changes, so use only under the approved
    exclusive operator window. Unknown write outcome must never be retried blindly.
    """
    try:
        if type(expected_version) is not int or expected_version < 1:
            raise ValueError
        first = read()
        row = first["Parameter"]
        if (
            row["Name"] != NAME
            or row["Type"] != "SecureString"
            or row["Version"] != expected_version
        ):
            raise ValueError
        document = json.loads(row["Value"])
        if (
            not isinstance(document, dict)
            or set(document) != {"version", "primary", "resend_api_key"}
            or type(document["version"]) is not int
            or document["version"] != 1
            or document["primary"] != "resend"
            or not isinstance(document["resend_api_key"], str)
            or not document["resend_api_key"]
        ):
            raise ValueError
        check = read()["Parameter"]
        if check["Version"] != expected_version or check["Value"] != row["Value"]:
            raise ValueError
        document["primary"] = "ses"
        payload = {
            "Name": NAME,
            "Type": "SecureString",
            "KeyId": "alias/aws/ssm",
            "Overwrite": True,
            "Value": json.dumps(document, separators=(",", ":")),
        }
        result = write(payload)
        if result.get("Version") != expected_version + 1:
            raise ValueError
        verified = read()["Parameter"]
        if (
            verified["Version"] != expected_version + 1
            or json.loads(verified["Value"]) != document
        ):
            raise ValueError
        return {"version": verified["Version"], "primary": "ses", "verified": True}
    except Exception:
        raise EmailRouteRefused(
            "Email route update stopped; inspect before any retry"
        ) from None
