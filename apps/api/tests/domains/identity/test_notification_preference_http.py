"""Own-account conversation preference with real synthetic sessions and DB."""

import pytest

from apps.api.tests.domains.identity.test_capabilities_http import (
    client,
    protected_headers,
    regular,
    temporary,
)


@pytest.mark.parametrize("kind", ["regular", "temporary"])
def test_preference_default_own_account_and_csrf(identity_runtime, signed_tokens, kind):
    """Only an authenticated account can toggle its strict boolean preference."""
    state = identity_runtime
    path = "/me/conversation-email-preference"
    with client(state) as browser:
        assert browser.get(path).status_code == 401
        (
            regular(browser, signed_tokens)
            if kind == "regular"
            else temporary(state, browser)
        )
        headers = protected_headers(browser)
        assert browser.get(path).json() == {"enabled": True}
        assert browser.put(path, json={"enabled": False}).status_code == 403
        assert (
            browser.put(path, headers=headers, json={"enabled": "false"}).status_code
            == 422
        )
        assert (
            browser.put(
                path, headers=headers, json={"enabled": False, "user_id": "forged"}
            ).status_code
            == 422
        )
        assert browser.put(path, headers=headers, json={"enabled": False}).json() == {
            "enabled": False
        }
        assert browser.get(path).json() == {"enabled": False}
        assert browser.put(path, headers=headers, json={"enabled": True}).json() == {
            "enabled": True
        }
