"""Synthetic own-data and controlled sharing checks; no actual CN membership claim."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from datetime import timedelta
from uuid import uuid4

import pytest

from app.contracts.domain_types import ContactSharingContext, ProfilePatch
from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.core.runtime_bindings import runtime_claim, runtime_claims, runtime_scope
from app.domains.identity.contacts import contact_value
from app.domains.identity.public import (
    get_selected_own_contacts,
    get_shareable_contact_options,
)
from apps.api.tests.domains.identity.session_fixtures import activate
from apps.api.tests.domains.identity.test_capabilities_postgres import regular

VALUES = {
    "email": "Synthetic+Share@EXAMPLE.com",
    "phone": "+919876543210",
    "upi_id": "synthetic.demo@oktest",
}


@pytest.mark.parametrize("kind,value", VALUES.items())
def test_contact_trim_keeps_synthetic_spelling(kind, value):
    assert contact_value(kind, "  " + value + "  ") == value


@pytest.mark.parametrize(
    "kind,value",
    [
        ("email", "not-an-email"),
        ("email", "Display <test@example.com>"),
        ("email", "a@localhost"),
        ("email", "a" * 255 + "@example.com"),
        ("phone", "919876543210"),
        ("phone", "+012345678"),
        ("phone", "+1234567"),
        ("phone", "+" + "1" * 16),
        ("phone", "+９１９８７６５４３２１０"),
        ("upi_id", "missing-handle"),
        ("upi_id", "a@"),
        ("upi_id", "a b@handle"),
        ("upi_id", "é@handle"),
        ("upi_id", "a" * 100 + "@h"),
        ("email", "\ud800@example.com"),
        ("email", " "),
        ("unknown", "PRIVATE_INPUT"),
    ],
)
def test_bad_contact_syntax_is_safe422(kind, value):
    with pytest.raises(PublicError) as error:
        contact_value(kind, value)
    assert error.value.spec.status == 422
    assert value not in str(error.value)


def test_email_validation_disables_dns_and_supports_unicode(monkeypatch):
    from app.domains.identity import contacts

    actual = contacts.validate_email
    seen = []

    def validator(value, **kwargs):
        seen.append(kwargs)
        return actual(value, **kwargs)

    monkeypatch.setattr(contacts, "validate_email", validator)
    assert contact_value("email", "δοκιμή@example.com") == "δοκιμή@example.com"
    assert seen == [
        {
            "check_deliverability": False,
            "allow_smtputf8": True,
            "allow_display_name": False,
        }
    ]


@pytest.mark.parametrize("kind", ["regular", "temporary"])
def test_own_profile_and_independent_contacts(identity_runtime, signed_tokens, kind):
    state = identity_runtime
    caller = (
        regular(state, signed_tokens) if kind == "regular" else activate(state)
    ).identity.caller
    other = activate(state, email="other-profile@example.invalid").identity.caller
    service = state.service.contacts
    with state.connect() as c:
        before = c.execute(
            "SELECT activated_at,expires_at,status,(SELECT login_email_key FROM identity.temporary_credentials WHERE user_id=u.id),(SELECT subject FROM identity.external_identities WHERE user_id=u.id) FROM identity.users u WHERE id=%s",
            (caller.user_id,),
        ).fetchone()
    assert service.read_contacts(caller).model_dump() == dict.fromkeys(VALUES)
    assert (
        service.update_profile(
            caller, ProfilePatch(display_name="  Synthetic 名  ")
        ).display_name
        == "Synthetic 名"
    )
    assert service.update_profile(caller, ProfilePatch()).display_name == "Synthetic 名"
    for field, value in VALUES.items():
        service.set_contact(caller, field, " " + value + " ")
        service.set_contact(caller, field, value)  # Repeat-safe field-only upsert.
    assert service.read_contacts(caller).model_dump() == VALUES
    assert service.read_contacts(other).model_dump() == dict.fromkeys(VALUES)
    assert (
        service.update_profile(caller, ProfilePatch(display_name=None)).display_name
        is None
    )
    service.delete_contact(caller, "phone")
    assert service.read_contacts(caller).model_dump() == VALUES | {"phone": None}
    for field in VALUES:
        service.delete_contact(caller, field)
        service.delete_contact(caller, field)
    with state.connect() as c:
        assert c.execute("SELECT count(*) FROM identity.contacts").fetchone()[0] == 0
        assert (
            c.execute(
                "SELECT activated_at,expires_at,status,(SELECT login_email_key FROM identity.temporary_credentials WHERE user_id=u.id),(SELECT subject FROM identity.external_identities WHERE user_id=u.id) FROM identity.users u WHERE id=%s",
                (caller.user_id,),
            ).fetchone()
            == before
        )


@pytest.mark.parametrize("name", [" "])
def test_profile_invalid_trim_or_encoding(identity_runtime, name):
    caller = activate(identity_runtime).identity.caller
    with pytest.raises(PublicError) as error:
        identity_runtime.service.contacts.update_profile(
            caller, ProfilePatch(display_name=name)
        )
    assert error.value.spec.status == 422


def test_profile_unicode_boundary(identity_runtime):
    caller = activate(identity_runtime).identity.caller
    service = identity_runtime.service.contacts
    assert (
        service.update_profile(
            caller, ProfilePatch(display_name="名" * 80)
        ).display_name
        == "名" * 80
    )
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProfilePatch(display_name="名" * 81)


@pytest.mark.parametrize(
    "mode", ["expired", "revoked", "wrong_class", "missing", "stale"]
)
def test_fresh_account_state_denies_all_own_operations(identity_runtime, mode):
    state = identity_runtime
    caller = activate(state).identity.caller
    if mode == "expired":
        state.clock[0] += timedelta(days=14)
        caller = CallerContext(
            caller.user_id, "temporary", state.clock[0] + timedelta(hours=1)
        )
    elif mode == "revoked":
        state.service.revoke_account(caller.user_id)
    elif mode == "wrong_class":
        caller = CallerContext(caller.user_id, "regular", caller.valid_until)
    elif mode == "missing":
        caller = CallerContext(uuid4(), "temporary", caller.valid_until)
    else:
        caller = CallerContext(caller.user_id, "temporary", state.clock[0])
    service = state.service.contacts
    for operation in (
        lambda: service.read_contacts(caller),
        lambda: service.update_profile(caller, ProfilePatch(display_name="Synthetic")),
        lambda: service.set_contact(caller, "phone", VALUES["phone"]),
        lambda: service.delete_contact(caller, "phone"),
    ):
        with pytest.raises(PublicError) as error:
            operation()
        assert error.value.spec.status == 401


def bindings(state):
    """Install real Identity ports; claims below remain controlled CN fixtures."""
    return runtime_scope(
        {
            "identity.get_shareable_contact_options": state.service.contacts.get_shareable_contact_options,
            "identity.get_selected_own_contacts": state.service.contacts.get_selected_own_contacts,
        }
    )


def test_scoped_public_sharing_only_confirmed_present_fields(identity_runtime, caplog):
    state = identity_runtime
    caller = activate(state).identity.caller
    conversation = uuid4()
    service = state.service.contacts
    for field, value in VALUES.items():
        service.set_contact(caller, field, value)

    async def scenario():
        with bindings(state):
            with runtime_claims(
                {
                    "identity.contact_share": ContactSharingContext(
                        caller.user_id, conversation
                    )
                }
            ):
                options = await get_shareable_contact_options(caller, conversation)
                assert options.model_dump() == {
                    "user_id": caller.user_id,
                    "has_email": True,
                    "has_phone": True,
                    "has_upi_id": True,
                }
                with pytest.raises(PublicError) as error:
                    await get_selected_own_contacts(
                        caller, conversation, frozenset({"email"})
                    )
                assert error.value.spec.status == 403
            scope = ContactSharingContext(
                caller.user_id, conversation, frozenset({"email", "phone"})
            )
            with runtime_claims({"identity.contact_share": scope}):
                selected = await get_selected_own_contacts(
                    caller, conversation, frozenset({"email"})
                )
                assert selected.model_dump() == {
                    "email": VALUES["email"],
                    "phone": None,
                    "upi_id": None,
                }
                assert VALUES["email"] not in repr(selected)
                for fields, status in [
                    (frozenset({"upi_id"}), 403),
                    (frozenset(), 422),
                    (frozenset({"unknown"}), 422),
                ]:
                    with pytest.raises(PublicError) as error:
                        await get_selected_own_contacts(caller, conversation, fields)
                    assert error.value.spec.status == status
                service.delete_contact(caller, "email")
                assert not (
                    await get_shareable_contact_options(caller, conversation)
                ).has_email
                with pytest.raises(PublicError) as error:
                    await get_selected_own_contacts(
                        caller, conversation, frozenset({"email"})
                    )
                assert error.value.spec.status == 422
                state.service.revoke_account(caller.user_id)
                with pytest.raises(PublicError) as error:
                    await get_shareable_contact_options(caller, conversation)
                assert error.value.spec.status == 401
        assert runtime_claim("identity.contact_share") is None

    asyncio.run(scenario())
    assert all(value not in caplog.text for value in VALUES.values())


def test_missing_forged_or_mismatched_scope_fails_closed(identity_runtime):
    state = identity_runtime
    caller = activate(state).identity.caller
    conversation = uuid4()

    async def scenario():
        with pytest.raises(PublicError) as error:
            await get_shareable_contact_options(caller, conversation)
        assert error.value.spec.status == 503
        with bindings(state):
            for scope in (
                None,
                {"actor_id": caller.user_id},
                ContactSharingContext(uuid4(), conversation),
                ContactSharingContext(caller.user_id, uuid4()),
            ):
                with runtime_claims({"identity.contact_share": scope}):
                    with pytest.raises(PublicError) as error:
                        await get_shareable_contact_options(caller, conversation)
                    assert error.value.spec.status == 403

    asyncio.run(scenario())


def test_parallel_field_updates_preserve_each_other_and_profile(identity_runtime):
    state = identity_runtime
    caller = activate(state).identity.caller
    service = state.service.contacts

    def write(field):
        service.set_contact(caller, field, VALUES[field])
        service.update_profile(caller, ProfilePatch(display_name="Synthetic " + field))

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(write, VALUES))
    assert service.read_contacts(caller).model_dump() == VALUES
    assert service.update_profile(caller, ProfilePatch()).display_name in {
        "Synthetic " + field for field in VALUES
    }


def test_sharing_context_is_private_frozen_and_not_wire_schema():
    from json import loads
    from pathlib import Path

    scope = ContactSharingContext(uuid4(), uuid4(), frozenset({"phone"}))
    assert repr(scope) == "ContactSharingContext()"
    with pytest.raises(FrozenInstanceError):
        scope.actor_id = uuid4()
    for fields in (frozenset(), frozenset({"unknown"}), {"phone"}):
        with pytest.raises(ValueError):
            ContactSharingContext(uuid4(), uuid4(), fields)
    schema = loads(Path("contracts/generated/openapi.json").read_text())
    assert "ContactSharingContext" not in schema["components"]["schemas"]


def test_parallel_claim_scopes_and_nested_reset():
    async def worker(index):
        with runtime_claims({"identity.contact_share": index}):
            await asyncio.sleep(0)
            with runtime_claims({}):
                assert runtime_claim("identity.contact_share") is None
            return runtime_claim("identity.contact_share")

    async def scenario():
        assert await asyncio.gather(*(worker(i) for i in range(8))) == list(range(8))
        assert runtime_claim("identity.contact_share") is None

    asyncio.run(scenario())


def test_delete_and_disclosure_are_serialized_and_never_substitute(identity_runtime):
    state = identity_runtime
    caller = activate(state).identity.caller
    conversation = uuid4()
    service = state.service.contacts
    service.set_contact(caller, "email", VALUES["email"])
    service.set_contact(caller, "phone", VALUES["phone"])

    def share():
        async def read():
            with (
                bindings(state),
                runtime_claims(
                    {
                        "identity.contact_share": ContactSharingContext(
                            caller.user_id, conversation, frozenset({"email"})
                        )
                    }
                ),
            ):
                try:
                    selected = await get_selected_own_contacts(
                        caller, conversation, frozenset({"email"})
                    )
                    assert selected.model_dump() == {
                        "email": VALUES["email"],
                        "phone": None,
                        "upi_id": None,
                    }
                except PublicError as error:
                    assert error.spec.status == 422

        asyncio.run(read())

    with ThreadPoolExecutor(max_workers=2) as pool:
        reads = pool.submit(share)
        deletion = pool.submit(service.delete_contact, caller, "email")
        reads.result()
        deletion.result()
    assert service.read_contacts(caller).model_dump() == {
        "email": None,
        "phone": VALUES["phone"],
        "upi_id": None,
    }


def test_dependency_errors_do_not_expose_contact_values(identity_runtime):
    from app.domains.identity.contacts import PostgresContacts

    caller = activate(identity_runtime).identity.caller

    def unavailable():
        raise RuntimeError(VALUES["email"])

    service = PostgresContacts(unavailable, lambda: identity_runtime.clock[0])
    with pytest.raises(PublicError) as error:
        service.read_contacts(caller)
    assert error.value.spec.status == 503 and VALUES["email"] not in str(error.value)
