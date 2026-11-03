"""Local-only routing policy for the proposed Lambda-first comparison.

This module performs no HTTP or AWS calls and is not installed in the app.
An eventual reviewed transport must classify an invocation rejected before
execution as LambdaAtCapacity; no other error may be mapped to that signal.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

T = TypeVar("T")


class LambdaAtCapacity(Exception):
    """The Lambda service rejected this invocation before executing it."""


@dataclass(frozen=True, repr=False)
class OverflowResult(Generic[T]):
    """Carry the response and its actual backend without exposing the response in repr."""

    response: T
    backend: Literal["lambda", "ecs"]


async def dispatch_read(
    invoke_lambda: Callable[[], Awaitable[T]],
    serve_ecs: Callable[[], Awaitable[T]],
) -> OverflowResult[T]:
    """Try Lambda once; use ECS once only after an explicit capacity rejection.

    Other exceptions propagate unchanged: timeouts and accepted-but-failed
    invocations must not silently cause duplicate work or mask failures.
    The caller supplies an already selected read and owns authorization and
    privacy; this function has no route selection or transport side effects.
    """
    try:
        response = await invoke_lambda()
    except LambdaAtCapacity:
        return OverflowResult(response=await serve_ecs(), backend="ecs")
    return OverflowResult(response=response, backend="lambda")
