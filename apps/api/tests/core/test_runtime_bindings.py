"""Technical dispatcher isolation/failure tests; no domain or provider is selected."""

import asyncio

from pydantic import BaseModel, ConfigDict
import pytest

from app.core.errors import ERRORS, PublicError
from app.core.runtime_bindings import dispatch_runtime, runtime_scope


class Checked(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ready: bool


async def read():
    return {"ready": True}


def test_unbound_fails_closed_without_fake_success():
    with pytest.raises(PublicError) as error:
        asyncio.run(dispatch_runtime("sample.read", Checked))
    assert error.value.spec.status == 503


def test_scopes_are_immutable_nested_snapshots_and_reset_after_error():
    async def unavailable():
        return {"ready": False}

    async def scenario():
        bindings = {"sample.read": read}
        with runtime_scope(bindings):
            bindings["sample.read"] = unavailable
            assert (await dispatch_runtime("sample.read", Checked)).ready
            with runtime_scope({"sample.read": unavailable}):
                assert not (await dispatch_runtime("sample.read", Checked)).ready
            assert (await dispatch_runtime("sample.read", Checked)).ready
            with pytest.raises(RuntimeError):
                with runtime_scope({}):
                    raise RuntimeError("synthetic scoped exception")
            assert (await dispatch_runtime("sample.read", Checked)).ready
        with pytest.raises(PublicError):
            await dispatch_runtime("sample.read", Checked)

    asyncio.run(scenario())


def test_parallel_tasks_cannot_overwrite_other_runtime_bindings():
    async def scenario():
        async def worker(value):
            async def callback():
                await asyncio.sleep(0)
                return {"ready": value}

            with runtime_scope({"sample.read": callback}):
                # Both scopes must overlap before either dispatch lookup.
                await asyncio.sleep(0)
                first = await dispatch_runtime("sample.read", Checked)
                await asyncio.sleep(0)
                second = await dispatch_runtime("sample.read", Checked)
                return first.ready, second.ready

        assert await asyncio.gather(worker(True), worker(False)) == [
            (True, True),
            (False, False),
        ]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "result",
    [
        {"ready": "yes"},
        {"ready": 1},
        {"ready": True, "private": "PRIVATE_RESULT"},
        {},
        None,
    ],
)
def test_invalid_result_never_coerces_or_exposes_private_data(result):
    async def callback():
        return result

    with runtime_scope({"sample.read": callback}):
        with pytest.raises(PublicError) as error:
            asyncio.run(dispatch_runtime("sample.read", Checked))
    assert error.value.spec.status == 503
    assert str(error.value) == "dependency_unavailable"


def test_provider_error_is_safe_and_explicit_public_errors_preserved():
    async def private_failure():
        raise RuntimeError("PRIVATE_PROVIDER_ERROR")

    async def public_failure():
        raise PublicError(ERRORS[403])

    for callback, status in ((private_failure, 503), (public_failure, 403)):
        with runtime_scope({"sample.read": callback}):
            with pytest.raises(PublicError) as error:
                asyncio.run(dispatch_runtime("sample.read", Checked))
        assert error.value.spec.status == status
        assert "PRIVATE" not in str(error.value)


def test_scope_resets_after_cancellation():
    async def cancelled():
        raise asyncio.CancelledError

    async def scenario():
        with pytest.raises(asyncio.CancelledError):
            with runtime_scope({"sample.read": cancelled}):
                await dispatch_runtime("sample.read", Checked)
        with pytest.raises(PublicError) as error:
            await dispatch_runtime("sample.read", Checked)
        assert error.value.spec.status == 503

    asyncio.run(scenario())


def test_sync_or_unnamed_provider_is_not_installed():
    for bindings in (
        {"sample.read": lambda: True},
        {"bad": read},
        {"sample._private": read},
    ):
        with pytest.raises(ValueError):
            with runtime_scope(bindings):
                pytest.fail("Invalid bindings installed")


def test_preconstructed_model_cannot_bypass_strict_validation():
    async def callback():
        return Checked.model_construct(ready="PRIVATE_WRONG_TYPE")

    with runtime_scope({"sample.read": callback}):
        with pytest.raises(PublicError) as error:
            asyncio.run(dispatch_runtime("sample.read", Checked))
    assert error.value.spec.status == 503
    assert str(error.value) == "dependency_unavailable"
