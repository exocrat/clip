"""Approved capability matrix and public eligibility using actual account storage."""

import asyncio
from datetime import timedelta
from uuid import uuid4

from pydantic import SecretStr
import pytest

from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.core.runtime_bindings import runtime_scope
from app.domains.identity.capabilities import Capability, PostgresCapabilities
from app.domains.identity.public import check_account_eligibility
from apps.api.tests.domains.identity.session_fixtures import activate, SOURCE

# Independent expected policy, including temporary wanted authors' existing threads.
MATRIX = [
    ("browse", True, True),
    ("search", True, True),
    ("save_listings", True, True),
    ("manage_own_wanted", True, True),
    ("start_listing_conversation", True, True),
    ("use_authorized_conversations", True, True),
    ("submit_offers", True, True),
    ("read_own_profile", True, True),
    ("manage_own_profile", True, True),
    ("manage_own_contacts", True, True),
    ("share_own_contacts", True, True),
    ("manage_sale_listings", True, False),
    ("start_wanted_response", True, False),
]


def regular(state, signed_tokens):
    """Obtain trusted regular context through real nonce/RSA/account/session logic."""
    attempt = state.service.start_microsoft(SOURCE)
    token = SecretStr(signed_tokens.token({"nonce": attempt.nonce}))
    return state.service.microsoft_exchange(
        token, attempt.token.get_secret_value(), SOURCE, signed_tokens.validator()
    )


def denied(status, operation):
    with pytest.raises(PublicError) as error:
        operation()
    assert error.value.spec.status == status
    assert str(error.value) == error.value.spec.code


def test_capability_names_are_exactly_reviewed_matrix():
    assert {capability.value for capability in Capability} == {row[0] for row in MATRIX}


@pytest.mark.parametrize("account_class", ["regular", "temporary"])
@pytest.mark.parametrize("name,regular_allowed,temporary_allowed", MATRIX)
def test_regular_temporary_matrix_with_trusted_real_callers(
    identity_runtime,
    signed_tokens,
    account_class,
    name,
    regular_allowed,
    temporary_allowed,
):
    state = identity_runtime
    grant = (
        regular(state, signed_tokens) if account_class == "regular" else activate(state)
    )
    caller = grant.identity.caller
    allowed = regular_allowed if account_class == "regular" else temporary_allowed
    if allowed:
        assert (
            state.service.capabilities.require_capability(caller, Capability(name))
            is None
        )
    else:
        denied(
            403,
            lambda: state.service.capabilities.require_capability(
                caller, Capability(name)
            ),
        )


def test_public_boolean_shape_exact_class_and_missing_target(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    temporary = activate(state).identity.caller
    regular_caller = regular(state, signed_tokens).identity.caller

    async def scenario():
        with runtime_scope(
            {
                "identity.check_account_eligibility": state.service.capabilities.check_account_eligibility
            }
        ):
            for caller in (temporary, regular_caller):
                result = await check_account_eligibility(caller.user_id)
                assert result.model_dump() == {"eligible": True}
                assert (
                    await check_account_eligibility(
                        caller.user_id, caller.account_class
                    )
                ).eligible
                other = (
                    "regular" if caller.account_class == "temporary" else "temporary"
                )
                assert not (
                    await check_account_eligibility(caller.user_id, other)
                ).eligible
            assert (await check_account_eligibility(uuid4())).model_dump() == {
                "eligible": False
            }

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mode", ["expired", "revoked", "removed", "pending", "missing", "future"]
)
def test_current_account_state_overrides_stale_caller(identity_runtime, mode):
    state = identity_runtime
    caller = activate(state).identity.caller
    if mode == "expired":
        state.clock[0] += timedelta(days=14)
        caller = CallerContext(
            caller.user_id, "temporary", state.clock[0] + timedelta(days=1)
        )
    elif mode in {"revoked", "removed"}:
        state.service.revoke_account(caller.user_id)
        if mode == "removed":
            with state.connect() as c:
                c.execute(
                    "UPDATE identity.users SET profile_removed_at=%s WHERE id=%s",
                    (state.clock[0], caller.user_id),
                )
    elif mode == "missing":
        caller = CallerContext(uuid4(), "temporary", state.clock[0] + timedelta(days=1))
    else:
        identifier = uuid4()
        kind = "regular" if mode == "future" else "temporary"
        with state.connect() as c:
            c.execute(
                "INSERT INTO identity.users(id,account_class,status,created_at) VALUES (%s,%s,%s,%s)",
                (
                    identifier,
                    kind,
                    "active" if mode == "future" else "pending",
                    (
                        state.clock[0] + timedelta(hours=1)
                        if mode == "future"
                        else state.clock[0]
                    ),
                ),
            )
        caller = CallerContext(identifier, kind, state.clock[0] + timedelta(days=1))
    denied(
        401,
        lambda: state.service.capabilities.require_capability(
            caller, Capability.BROWSE
        ),
    )
    assert not asyncio.run(
        state.service.capabilities.check_account_eligibility(caller.user_id)
    ).eligible


def test_expired_or_forged_caller_class_and_raw_flags_cannot_authorize(
    identity_runtime,
):
    state = identity_runtime
    actual = activate(state).identity.caller
    for caller in (
        CallerContext(actual.user_id, "regular", actual.valid_until),
        CallerContext(actual.user_id, "temporary", state.clock[0]),
        {"user_id": actual.user_id, "account_class": "regular"},
    ):
        denied(
            401,
            lambda: state.service.capabilities.require_capability(
                caller, Capability.READ_OWN_PROFILE
            ),
        )
    denied(
        422,
        lambda: state.service.capabilities.require_capability(
            actual, "manage_sale_listings"
        ),
    )
    assert asyncio.run(
        state.service.capabilities.check_account_eligibility(actual.user_id)
    ).eligible


def test_eligibility_is_account_state_not_an_authentication_shortcut(identity_runtime):
    state = identity_runtime
    grant = activate(state)
    state.service.logout(grant.token.get_secret_value())
    assert asyncio.run(
        state.service.capabilities.check_account_eligibility(
            grant.identity.caller.user_id
        )
    ).eligible
    denied(401, lambda: state.service.authenticate(grant.token.get_secret_value()))


def test_dependency_failure_is503_never_false_or_private_error(identity_runtime):
    state = identity_runtime
    caller = activate(state).identity.caller

    def unavailable():
        raise RuntimeError("PRIVATE_DB_DETAIL")

    service = PostgresCapabilities(unavailable, lambda: state.clock[0])
    denied(503, lambda: service.require_capability(caller, Capability.BROWSE))

    async def scenario():
        with runtime_scope(
            {"identity.check_account_eligibility": service.check_account_eligibility}
        ):
            with pytest.raises(PublicError) as error:
                await check_account_eligibility(caller.user_id)
            assert (
                error.value.spec.status == 503
                and str(error.value) == "dependency_unavailable"
            )

    asyncio.run(scenario())


def test_public_scope_is_required_and_fresh_reads_are_not_cached(identity_runtime):
    state = identity_runtime
    caller = activate(state).identity.caller

    async def scenario():
        with pytest.raises(PublicError) as error:
            await check_account_eligibility(caller.user_id)
        assert error.value.spec.status == 503
        with runtime_scope(
            {
                "identity.check_account_eligibility": state.service.capabilities.check_account_eligibility
            }
        ):
            assert (await check_account_eligibility(caller.user_id)).eligible
            state.service.revoke_account(caller.user_id)
            assert not (await check_account_eligibility(caller.user_id)).eligible
        with pytest.raises(PublicError):
            await check_account_eligibility(caller.user_id)

    asyncio.run(scenario())


def test_parallel_real_runtime_providers_do_not_share_cached_state(identity_runtime):
    state = identity_runtime
    caller = activate(state).identity.caller
    later = PostgresCapabilities(
        state.connect, lambda: state.clock[0] + timedelta(days=14)
    )

    async def worker(provider):
        with runtime_scope(
            {"identity.check_account_eligibility": provider.check_account_eligibility}
        ):
            return (await check_account_eligibility(caller.user_id)).eligible

    async def scenario():
        assert await asyncio.gather(
            worker(state.service.capabilities), worker(later)
        ) == [True, False]

    asyncio.run(scenario())


def test_invalid_internal_identifier_or_class_fails_safely(identity_runtime):
    service = identity_runtime.service.capabilities
    for identifier, kind in (("not-an-id", None), (uuid4(), "admin")):
        denied(
            422,
            lambda: asyncio.run(service.check_account_eligibility(identifier, kind)),
        )
