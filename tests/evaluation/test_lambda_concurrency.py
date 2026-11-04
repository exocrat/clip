"""The pilot must fail closed if account-wide concurrency or competition changes."""

from types import SimpleNamespace
import pytest
from scripts.evaluation.k6.lambda_concurrency import validate_binding, verify

ARN = "arn:aws:lambda:ap-south-1:335523638354:function:clip-exp03-exp261103"
BINDING = {"mode": "unreserved", "maximum": 10}


def fake(reserved=None, maximum=10, unreserved=10, functions=None):
    return SimpleNamespace(
        get_function_concurrency=lambda **_: (
            {} if reserved is None else {"ReservedConcurrentExecutions": reserved}
        ),
        get_account_settings=lambda: {
            "AccountLimit": {
                "ConcurrentExecutions": maximum,
                "UnreservedConcurrentExecutions": unreserved,
            }
        },
        get_paginator=lambda _: SimpleNamespace(
            paginate=lambda: [
                {
                    "Functions": [
                        {"FunctionArn": x}
                        for x in ([ARN] if functions is None else functions)
                    ]
                }
            ]
        ),
    )


def test_single_function_unreserved_and_historical_reserved():
    validate_binding(None, "A")
    validate_binding(BINDING, "B")
    verify(fake(), ARN, BINDING)
    verify(fake(reserved=10), ARN, {"mode": "reserved", "maximum": 10})
    verify(fake(reserved=10), ARN, None)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"maximum": 1000, "unreserved": 1000},
        {"unreserved": 9},
        {"reserved": 10},
        {"functions": [ARN, ARN + "-other"]},
        {"functions": []},
    ],
)
def test_drift_rejected(kwargs):
    with pytest.raises(ValueError, match="lambda_unreserved"):
        verify(fake(**kwargs), ARN, BINDING)


@pytest.mark.parametrize(
    "binding",
    [
        None,
        {"mode": "unreserved", "maximum": 20},
        {"mode": "reserved", "maximum": True},
        {"mode": "reserved", "maximum": 0},
    ],
)
def test_ambiguous_bindings_rejected(binding):
    with pytest.raises(ValueError):
        validate_binding(binding, "B")
