"""Explicit test-only scripted providers; no real provider behavior or HTTP auth."""

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Generic, Literal, TypeVar, get_args

from app.core.config import ConfigurationError, Settings

T = TypeVar("T")
ProviderKind = Literal["identity", "email", "storage"]
FailureReason = Literal["unavailable", "timeout", "denied", "invalid"]
_SELECTORS = {
    "identity": "identity_provider",
    "email": "email_provider",
    "storage": "storage_provider",
}


@dataclass(frozen=True)
class Return(Generic[T]):
    """A test-owned result, excluded from repr to avoid dumping fixture values."""

    value: T = field(repr=False)


@dataclass(frozen=True)
class Fail:
    """A reviewed synthetic failure reason without arbitrary provider text."""

    reason: FailureReason

    def __post_init__(self) -> None:
        """Reject unknown reasons without echoing the supplied input."""
        if type(self.reason) is not str or self.reason not in get_args(FailureReason):
            raise ValueError("Unsupported synthetic provider failure reason")


class TestProviderFailure(RuntimeError):
    """Signal a scripted failure, not the exception contract of a real provider."""

    __test__ = False

    def __init__(self, reason: FailureReason) -> None:
        """Expose only a validated safe reason; never store arbitrary exception text."""
        Fail(reason)
        self.reason = reason
        super().__init__("Synthetic provider failure: " + reason)


class ScriptExhausted(AssertionError):
    """Report an unexpected extra provider call without inventing successful output."""


class ScriptedTestProvider(Generic[T]):
    """Consume scripted outcomes atomically on one asyncio loop; not thread safe.

    There are no awaits inside call, retries, sleeps, I/O, credentials or HTTP
    dependency bindings. Mutable return values remain the test author's concern.
    """

    __slots__ = ("_kind", "_outcomes", "_call_count")

    def __init__(
        self,
        settings: Settings,
        kind: ProviderKind,
        outcomes: Sequence[Return[T] | Fail],
    ) -> None:
        """Guard every construction path and copy the script without rendering values."""
        if type(kind) is not str or kind not in _SELECTORS:
            raise ValueError("Unsupported synthetic provider kind")
        if (
            not isinstance(settings, Settings)
            or settings.environment not in ("local", "test")
            or getattr(settings, _SELECTORS[kind]) != "fake"
        ):
            raise ConfigurationError(
                "Test provider requires explicit local/test fake selection"
            )
        if not isinstance(outcomes, Sequence) or not all(
            isinstance(outcome, (Return, Fail)) for outcome in outcomes
        ):
            raise ValueError("Expected a sequence of Return or Fail outcomes")
        self._kind = kind
        self._outcomes = deque(outcomes)
        self._call_count = 0

    @property
    def call_count(self) -> int:
        """Return attempts including failed calls and calls after script exhaustion."""
        return self._call_count

    @property
    def remaining(self) -> int:
        """Return unconsumed outcomes without exposing their values."""
        return len(self._outcomes)

    async def call(self) -> T:
        """Consume exactly one outcome, or fail visibly when the script is exhausted."""
        self._call_count += 1
        if not self._outcomes:
            raise ScriptExhausted("Synthetic provider script exhausted")
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Fail):
            raise TestProviderFailure(outcome.reason) from None
        return outcome.value

    def __repr__(self) -> str:
        """Show safe controls/counts only, even when return values cannot be rendered."""
        return f"ScriptedTestProvider(kind={self._kind!r}, calls={self.call_count}, remaining={self.remaining})"


def make_test_provider(
    settings: Settings,
    kind: ProviderKind,
    outcomes: Sequence[Return[T] | Fail],
) -> ScriptedTestProvider[T]:
    """Construct an explicitly selected fake; never choose a real adapter or fallback."""
    return ScriptedTestProvider(settings, kind, outcomes)
