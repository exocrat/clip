"""Narrow runtime adapter generation constraints; no provider or application import."""

import ast

import pytest

from scripts.generate_contracts import runtime_public

SOURCE = '''"""Synthetic typed declaration."""
from app.core.runtime_bindings import dispatch_runtime as _dispatch_runtime

async def read(value: object) -> Checked:
    """Declare one reviewed result model."""
    raise NotImplementedError("declaration-only")
'''


def test_only_selected_refusal_body_becomes_typed_dispatch():
    generated = runtime_public(SOURCE, "sample", frozenset({"read"}))
    node = next(
        node
        for node in ast.parse(generated).body
        if isinstance(node, ast.AsyncFunctionDef)
    )
    assert (
        len(node.body) == 2
        and ast.get_docstring(node) == "Declare one reviewed result model."
    )
    call = node.body[1].value.value
    assert call.func.id == "_dispatch_runtime"
    assert ast.literal_eval(call.args[0]) == "sample.read"
    assert [argument.id for argument in call.args[1:]] == ["Checked", "value"]
    assert runtime_public(SOURCE, "sample", frozenset()) == SOURCE


@pytest.mark.parametrize(
    "source,bindings",
    [
        (SOURCE, {"read"}),
        (SOURCE, frozenset({"missing"})),
        (
            SOURCE.replace(
                'raise NotImplementedError("declaration-only")', 'return "fabricated"'
            ),
            frozenset({"read"}),
        ),
        (
            SOURCE.replace("dispatch_runtime as _dispatch_runtime", "dispatch_runtime"),
            frozenset({"read"}),
        ),
        (SOURCE.replace("value: object", "*value: object"), frozenset({"read"})),
        (SOURCE.replace("value: object", "*, value: object"), frozenset({"read"})),
        (SOURCE.replace("-> Checked", "-> Checked | None"), frozenset({"read"})),
    ],
)
def test_unsupported_binding_never_silently_generates(source, bindings):
    with pytest.raises(ValueError):
        runtime_public(source, "sample", bindings)
