"""Real Conversation membership/HTTP and Identity contacts; synthetic request auth."""

from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest

from app.contracts.domain_types import SelectedOwnContacts
from app.core.auth import require_caller
from app.core.runtime_bindings import runtime_claim, runtime_scope
from app.domains.identity.capabilities import PostgresCapabilities
from app.domains.identity.contacts import PostgresContacts
from test_conversation_offers import offer_environment, snapshot
from test_thread_creation import TEST_DATABASE_DSN, caller, run_scenario

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_DSN is None, reason="use disposable Conversations harness"
)
SYNTHETIC = {
    "email": "synthetic-contact@example.com",
    "phone": "+919876543210",
    "upi_id": "synthetic@oktest",
}


@contextmanager
def contacts_runtime():
    """Bind actual Identity services rather than copying own-contact answers."""
    connect = lambda: psycopg.connect(TEST_DATABASE_DSN)
    clock = lambda: datetime.now(UTC)
    contacts = PostgresContacts(connect, clock)
    capabilities = PostgresCapabilities(connect, clock)
    with runtime_scope(
        {
            "identity.check_account_eligibility": capabilities.check_account_eligibility,
            "identity.get_shareable_contact_options": contacts.get_shareable_contact_options,
            "identity.get_selected_own_contacts": contacts.get_selected_own_contacts,
        }
    ):
        yield contacts


@pytest.mark.parametrize("temporary", [False, True])
def test_real_own_contact_selection_no_writes_and_current_field_removal(temporary):
    async def scenario(pool):
        async with offer_environment(pool, temporary=temporary) as state:
            with contacts_runtime() as contacts:
                for field, value in SYNTHETIC.items():
                    contacts.set_contact(state.actor, field, value)
                root = f"/conversations/{state.thread}"
                before = await snapshot(pool, state.thread)
                options = await state.client.get(root + "/contact-options")
                assert options.status_code == 200
                assert options.json() == {
                    "email_available": True,
                    "phone_available": True,
                    "upi_available": True,
                }
                assert options.headers["cache-control"] == "no-store"
                response = await state.client.post(
                    root + "/contact-preparations", json={"fields": ["email", "upi_id"]}
                )
                assert response.status_code == 200
                matches = response.json() == {
                    "email": SYNTHETIC["email"],
                    "phone": None,
                    "upi_id": SYNTHETIC["upi_id"],
                }
                assert matches, "selected own-contact projection mismatch"
                assert response.headers["cache-control"] == "no-store"
                assert runtime_claim("identity.contact_share") is None
                contacts.delete_contact(state.actor, "email")
                missing = await state.client.post(
                    root + "/contact-preparations", json={"fields": ["email", "phone"]}
                )
                assert missing.status_code == 422
                assert await snapshot(pool, state.thread) == before
                # The other member sees their own empty contact collection.
                state.app.dependency_overrides[require_caller] = lambda: caller(
                    state.owner
                )
                other = await state.client.get(root + "/contact-options")
                assert other.json() == {
                    "email_available": False,
                    "phone_available": False,
                    "upi_available": False,
                }

    run_scenario(scenario)


def test_nonmember_and_retired_thread_refuse_before_identity_and_unbound_fails_closed():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            root = f"/conversations/{state.thread}"
            # Only eligibility is bound by the fixture; contacts remain unbound.
            assert (
                await state.client.get(root + "/contact-options")
            ).status_code == 503
            state.app.dependency_overrides[require_caller] = lambda: caller(uuid4())
            for suffix, body in [
                ("contact-options", None),
                ("contact-preparations", {"fields": ["phone"]}),
            ]:
                response = (
                    await state.client.get(root + "/" + suffix)
                    if body is None
                    else await state.client.post(root + "/" + suffix, json=body)
                )
                assert response.status_code == 404
            state.app.dependency_overrides[require_caller] = lambda: state.actor
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE conversations.threads SET participant_writes_disabled_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (state.thread,),
                )
            assert (
                await state.client.post(
                    root + "/contact-preparations", json={"fields": ["phone"]}
                )
            ).status_code == 409

    run_scenario(scenario)


def test_invalid_fields_provider_leak_and_provider_failure_are_safe():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            url = f"/conversations/{state.thread}/contact-preparations"
            for body in [
                {"fields": []},
                {"fields": ["email", "email"]},
                {"fields": ["unknown"]},
                {"fields": ["email"], "user_id": str(state.owner)},
            ]:
                assert (await state.client.post(url, json=body)).status_code == 422

            async def broken(*args):
                return SelectedOwnContacts(
                    email=None, phone=SYNTHETIC["phone"], upi_id=None
                )

            async def failed(*args):
                raise RuntimeError("private-provider-diagnostic")

            for provider in (broken, failed):
                with runtime_scope({"identity.get_selected_own_contacts": provider}):
                    response = await state.client.post(url, json={"fields": ["email"]})
                    assert response.status_code == 503
                    safe = all(
                        value not in response.text
                        for value in [
                            *SYNTHETIC.values(),
                            "private-provider-diagnostic",
                        ]
                    )
                    assert safe, "private data in error response"
                    assert runtime_claim("identity.contact_share") is None

    run_scenario(scenario)
