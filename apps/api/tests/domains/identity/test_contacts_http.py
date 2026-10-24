"""Real session-backed own endpoints and fixture-only trusted sharing composition."""

from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import Depends
import pytest

from app.contracts.domain_types import ContactSharingContext
from app.core.auth import require_caller
from app.core.runtime_bindings import runtime_claims
from app.domains.identity.public import (
    get_shareable_contact_options,
    get_selected_own_contacts,
)
from apps.api.tests.domains.identity.test_capabilities_http import (
    client,
    temporary,
    regular,
    protected_headers,
)
from apps.api.tests.domains.identity.test_contacts import VALUES


@pytest.mark.parametrize("kind", ["regular", "temporary"])
def test_own_http_crud_security_and_no_session_disclosure(
    identity_runtime, signed_tokens, kind
):
    state = identity_runtime
    with client(state) as browser:
        assert browser.get("/me/contacts").status_code == 401
        (
            regular(browser, signed_tokens)
            if kind == "regular"
            else temporary(state, browser)
        )
        headers = protected_headers(browser)
        assert browser.get("/me/contacts").json() == dict.fromkeys(VALUES)
        assert (
            browser.patch(
                "/me/profile",
                headers=headers,
                json={"display_name": "  Synthetic 名  "},
            ).json()["display_name"]
            == "Synthetic 名"
        )
        assert (
            browser.patch("/me/profile", headers=headers, json={}).json()[
                "display_name"
            ]
            == "Synthetic 名"
        )
        assert (
            browser.patch(
                "/me/profile", headers=headers, json={"display_name": None}
            ).json()["display_name"]
            is None
        )
        for field, value in VALUES.items():
            assert (
                browser.put(
                    "/me/contacts/" + field, headers=headers, json={"value": value}
                ).status_code
                == 204
            )
            assert (
                browser.put("/me/contacts/" + field, json={"value": value}).status_code
                == 403
            )
        assert browser.get("/me/contacts").json() == VALUES
        assert all(value not in browser.get("/me").text for value in VALUES.values())
        for payload in (
            {"display_name": " "},
            {"display_name": "名" * 81},
            {"display_name": "a", "user_id": str(uuid4())},
        ):
            assert (
                browser.patch("/me/profile", headers=headers, json=payload).status_code
                == 422
            )
        for path, body in [
            ("phone", {"value": "bad-private-phone"}),
            ("unsupported", {"value": "private"}),
            ("email", {"value": "a@example.com", "user_id": str(uuid4())}),
        ]:
            result = browser.put("/me/contacts/" + path, headers=headers, json=body)
            assert result.status_code == 422
            assert body["value"] not in result.text
        for field in VALUES:
            assert (
                browser.delete("/me/contacts/" + field, headers=headers).status_code
                == 204
            )
        assert browser.get("/me/contacts").json() == dict.fromkeys(VALUES)
        state.clock[0] += timedelta(days=14)
        # Regular sessions also expire by this point; no stale source access.
        assert browser.get("/me/contacts").status_code == 401


def test_http_middleware_drops_ambient_sharing_and_trusted_fixture_can_scope(
    identity_runtime,
):
    state = identity_runtime
    conversation = uuid4()

    @state.app.get("/contact-fixture/options")
    async def options(caller=Depends(require_caller)):
        return await get_shareable_contact_options(caller, conversation)

    @state.app.post("/contact-fixture/prepare")
    async def prepare(caller=Depends(require_caller)):
        # Controlled fixture stands in only for reviewed CN participation and UI
        # confirmation preconditions. This does not prove actual CN integration.
        with runtime_claims(
            {
                "identity.contact_share": ContactSharingContext(
                    caller.user_id, conversation, frozenset({"email"})
                )
            }
        ):
            return await get_selected_own_contacts(
                caller, conversation, frozenset({"email"})
            )

    with client(state) as browser:
        session = temporary(state, browser)
        headers = protected_headers(browser)
        assert (
            browser.put(
                "/me/contacts/email", headers=headers, json={"value": VALUES["email"]}
            ).status_code
            == 204
        )

        with runtime_claims(
            {
                "identity.contact_share": ContactSharingContext(
                    UUID(session["user_id"]), conversation
                )
            }
        ):
            assert browser.get("/contact-fixture/options").status_code == 403
        result = browser.post("/contact-fixture/prepare", headers=headers)
        assert result.status_code == 200 and result.json() == {
            "email": VALUES["email"],
            "phone": None,
            "upi_id": None,
        }
        assert browser.get("/contact-fixture/options").status_code == 403
        assert (
            browser.get("/users/" + session["user_id"] + "/contacts").status_code == 404
        )
