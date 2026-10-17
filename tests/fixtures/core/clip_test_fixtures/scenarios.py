"""Reusable synthetic scenario inputs, not domain retry/authorization policies."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Generic, Literal, TypeVar

from app.core.auth import CallerContext
from clip_test_fixtures.providers import Fail, Return
from clip_test_fixtures.samples import SyntheticClock, SyntheticIds

T = TypeVar("T")


@dataclass(frozen=True)
class ProviderScenarios(Generic[T]):
    """Immutable scripts; values are hidden by Return and no script runs itself."""

    retry: tuple[Fail | Return[T], ...]
    duplicate: tuple[Return[T], ...]
    concurrent: tuple[Return[T], ...]
    primary: tuple[Return[T], ...]
    downstream: tuple[Fail, ...]


def make_provider_scenarios(first: T, second: T) -> ProviderScenarios[T]:
    """Supply explicit retry/duplicate/concurrent/partial-failure inputs.

    Duplicate outcomes repeat a value, not a promise of application idempotency.
    Primary/downstream scripts must be connected separately by the consuming test.
    """
    return ProviderScenarios(
        retry=(Fail("unavailable"), Return(first)),
        duplicate=(Return(first), Return(first)),
        concurrent=(Return(first), Return(second)),
        primary=(Return(first),),
        downstream=(Fail("unavailable"),),
    )


class AsyncBarrier:
    """One-use rendezvous for a known number of tasks on one asyncio loop.

    Tests must bound waits with wait_for. Cancellation does not reset the barrier;
    construct a new instance for another run. No thread-safety is promised.
    """

    def __init__(self, parties: int = 2) -> None:
        """Validate the task count and create a fresh gate without starting tasks."""
        if type(parties) is not int or parties < 1:
            raise ValueError("Barrier requires a positive integer task count")
        self._parties = parties
        self._arrived = 0
        self._ready = asyncio.Event()

    async def wait(self) -> None:
        """Release exactly the declared participants after all have entered."""
        if self._arrived >= self._parties:
            raise AssertionError("Barrier participant limit exceeded")
        self._arrived += 1
        if self._arrived == self._parties:
            self._ready.set()
        await self._ready.wait()


def make_unauthenticated_callers(
    ids: SyntheticIds, clock: SyntheticClock
) -> Mapping[str, object]:
    """Return missing, untyped and expired contexts without inventing ownership rules.

    Expiry must be checked against clock.now explicitly. A different valid user is
    not universally unauthorized: domain tests decide resource/action permission.
    """
    return MappingProxyType(
        {
            "missing": None,
            "untyped": MappingProxyType({"user_id": ids.regular_user_id}),
            "expired": CallerContext(ids.regular_user_id, "regular", clock.expired_at),
        }
    )


@dataclass(frozen=True)
class ValidationCase:
    """Named format/boundary input; hide values in parameter/failure representations."""

    name: str
    rule: Literal["uuid", "timestamp", "money", "page", "page_size"]
    value: object = field(repr=False)
    valid: bool


def make_validation_cases() -> tuple[ValidationCase, ...]:
    """Return only shared technical boundaries; domain ranges/fields are excluded."""
    return (
        ValidationCase(
            "uuid-valid", "uuid", "00000000-0000-4000-8000-000000000001", True
        ),
        ValidationCase("uuid-malformed", "uuid", "synthetic-invalid-id", False),
        ValidationCase("timestamp-aware", "timestamp", "2026-01-01T12:00:00Z", True),
        ValidationCase("timestamp-naive", "timestamp", "2026-01-01T12:00:00", False),
        ValidationCase("money-zero", "money", 0, True),
        ValidationCase("money-whole-rupee", "money", 100, True),
        ValidationCase("money-fractional-rupee", "money", 99, False),
        ValidationCase("money-float", "money", 100.0, False),
        ValidationCase("money-boolean", "money", True, False),
        ValidationCase("page-first", "page", 1, True),
        ValidationCase("page-zero", "page", 0, False),
        ValidationCase("size-20", "page_size", 20, True),
        ValidationCase("size-50", "page_size", 50, True),
        ValidationCase("size-100", "page_size", 100, True),
        ValidationCase("size-too-small", "page_size", 19, False),
        ValidationCase("size-too-large", "page_size", 101, False),
    )
