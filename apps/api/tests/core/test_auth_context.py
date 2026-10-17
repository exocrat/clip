"""Internal context types and validity without pretending to authenticate."""

import asyncio
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from starlette.requests import Request

from app.core.auth import CallerContext, require_caller
from app.core.errors import PublicError

USER_ID = UUID("123e4567-e89b-42d3-a456-426614174000")
NOW = datetime(2026, 10, 17, 6, 30, tzinfo=UTC)


@pytest.mark.parametrize("account_class", ["regular", "temporary"])
def test_valid_context_normalizes_and_is_immutable(account_class):
    """Context holds validated facts without deciding domain permissions."""
    expiry = NOW.astimezone(timezone(timedelta(hours=5, minutes=30))) + timedelta(
        seconds=1
    )
    caller = CallerContext(USER_ID, account_class, expiry)
    assert caller.valid_until.tzinfo is UTC
    caller.require_current(NOW)
    with pytest.raises(FrozenInstanceError):
        caller.account_class = "regular"


@pytest.mark.parametrize("delta", [-1, 0])
def test_expiry_is_exclusive(delta):
    """A context is unauthenticated at, or after, its validity deadline."""
    caller = CallerContext(USER_ID, "regular", NOW + timedelta(seconds=delta))
    with pytest.raises(PublicError) as captured:
        caller.require_current(NOW)
    assert captured.value.spec.status == 401
    assert captured.value.spec.code == "unauthenticated"


@pytest.mark.parametrize(
    ("user_id", "account_class", "expiry"),
    [
        (str(USER_ID), "regular", NOW),
        (UUID(int=0), "regular", NOW),
        (USER_ID, "owner", NOW),
        (USER_ID, "regular", datetime(2026, 10, 17)),
        (USER_ID, "regular", None),
    ],
)
def test_invalid_internal_context_fails_construction(user_id, account_class, expiry):
    """Do not silently coerce identity, trust class, or timezone-free deadlines."""
    with pytest.raises(ValueError):
        CallerContext(user_id, account_class, expiry)


def test_naive_validity_comparison_is_rejected():
    """Even internal clock inputs cannot introduce local-time assumptions."""
    with pytest.raises(ValueError):
        CallerContext(USER_ID, "regular", NOW).require_current(NOW.replace(tzinfo=None))


def test_dependency_consumes_only_internal_context():
    """Test-owned server wiring supplies context; this proves no real sign-in."""
    caller = CallerContext(USER_ID, "regular", datetime(2100, 1, 1, tzinfo=UTC))
    request = Request({"type": "http", "clip.caller": caller})
    assert asyncio.run(require_caller(request)) is caller


@pytest.mark.parametrize(
    "value", [None, {"user_id": str(USER_ID)}, "synthetic-context"]
)
def test_missing_or_untyped_internal_context_is_denied(value):
    """An unset or structurally similar slot is not a CallerContext."""
    with pytest.raises(PublicError) as captured:
        asyncio.run(require_caller(Request({"type": "http", "clip.caller": value})))
    assert captured.value.spec.status == 401
