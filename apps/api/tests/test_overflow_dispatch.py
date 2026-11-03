"""Offline checks of the Lambda-first decision, without app or AWS traffic."""

import asyncio

import pytest

from app.overflow_dispatch import LambdaAtCapacity, dispatch_read


def test_lambda_success_does_not_call_ecs():
    calls = []

    async def invoke():
        calls.append("lambda")
        return "private synthetic response"

    async def ecs():
        calls.append("ecs")
        return "ecs"

    result = asyncio.run(dispatch_read(invoke, ecs))
    assert result.backend == "lambda"
    assert result.response == "private synthetic response"
    assert "private synthetic response" not in repr(result)
    assert calls == ["lambda"]


def test_capacity_rejection_invokes_ecs_once():
    calls = []

    async def invoke():
        calls.append("lambda")
        raise LambdaAtCapacity()

    async def ecs():
        calls.append("ecs")
        return "ecs result"

    result = asyncio.run(dispatch_read(invoke, ecs))
    assert (result.backend, result.response) == ("ecs", "ecs result")
    assert calls == ["lambda", "ecs"]


@pytest.mark.parametrize("failure", [TimeoutError, RuntimeError])
def test_other_failures_do_not_retry_on_ecs(failure):
    calls = []

    async def invoke():
        calls.append("lambda")
        raise failure()

    async def ecs():
        calls.append("ecs")
        return "ecs"

    with pytest.raises(failure):
        asyncio.run(dispatch_read(invoke, ecs))
    assert calls == ["lambda"]
