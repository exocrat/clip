"""Technical context-scoped async dispatch; no domain/provider discovery or policy.

Only trusted composition supplies callbacks. Contexts are immutable snapshots,
reset on exit and inherited safely by async tasks/threadpool context copying.
No caller input, environment flag or import installs a provider automatically.
"""

from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
import inspect
import re
from types import MappingProxyType
from typing import TypeVar

from pydantic import BaseModel

from app.core.errors import ERRORS, PublicError

RuntimeCallback = Callable[..., Awaitable[object]]
RuntimeBindings = Mapping[str, RuntimeCallback]
Result = TypeVar("Result", bound=BaseModel)
_active: ContextVar[RuntimeBindings] = ContextVar(
    "clip_runtime_bindings", default=MappingProxyType({})
)


_claims: ContextVar[Mapping[str, object]] = ContextVar(
    "clip_runtime_claims", default=MappingProxyType({})
)


@contextmanager
def runtime_claims(claims: Mapping[str, object]) -> Iterator[None]:
    """Install server-only claim objects after the owner checks its preconditions.

    This technical scope authenticates nothing. Claim records must be immutable
    and validated by their owning provider; HTTP input never installs them.
    Nested/parallel scopes cannot overwrite or silently inherit one another.
    """
    snapshot = dict(claims)
    if any(
        not isinstance(name, str)
        or not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", name)
        for name in snapshot
    ):
        raise ValueError("Explicit runtime claim names required")
    token = _claims.set(MappingProxyType(snapshot))
    try:
        yield
    finally:
        _claims.reset(token)


def runtime_claim(name: str) -> object | None:
    """Read only the current trusted claim object; no discovery or default proof."""
    return _claims.get().get(name)


@contextmanager
def runtime_scope(bindings: RuntimeBindings) -> Iterator[None]:
    """Install a trusted immutable callback snapshot only for the enclosing scope.

    Async callbacks prevent accidental blocking provider work at the public
    boundary. Nested scopes replace rather than silently inherit missing ports.
    The original context is restored even after cancellation/provider failure.
    """
    snapshot = dict(bindings)
    for name, callback in snapshot.items():
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", name)
            or not inspect.iscoroutinefunction(callback)
        ):
            raise ValueError("Explicit named async runtime bindings required")
    token = _active.set(MappingProxyType(snapshot))
    try:
        yield
    finally:
        _active.reset(token)


async def dispatch_runtime(
    operation: str, result_type: type[Result], *args: object, **kwargs: object
) -> Result:
    """Delegate a generated typed port and strictly validate its reviewed result.

    Missing providers and malformed/coercible/private results fail closed. This
    validates shape only: owning providers enforce all authorization/transactions.
    No raw dependency/input/validation error is propagated or logged.
    """
    callback = _active.get().get(operation)
    if callback is None:
        raise PublicError(ERRORS[503])
    try:
        result = await callback(*args, **kwargs)
        if isinstance(result, BaseModel):
            # Pydantic otherwise trusts existing model instances, including
            # model_construct bypasses. Revalidate data without private warnings.
            result = result.model_dump(mode="python", warnings=False)
        return result_type.model_validate(result, strict=True)
    except PublicError:
        raise
    except Exception:
        raise PublicError(ERRORS[503]) from None
