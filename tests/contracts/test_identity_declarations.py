"""Check internal Identity declarations without contact values or a provider."""

import ast
import asyncio
import importlib.util
import inspect
import json
from pathlib import Path
from uuid import UUID

import pytest

from app.core.identifiers import UserId, new_id

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "clip_identity_contract_source", ROOT / "contracts/source/identity.py"
)
identity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(identity)


def test_required_contact_type_shapes():
    """Preserve required names/nullable semantics using only field metadata."""
    assert identity.UserId is UserId is UUID
    assert set(identity.ShareableContactOptions.model_fields) == {
        "user_id",
        "has_email",
        "has_phone",
        "has_upi_id",
    }
    for name, field in identity.ShareableContactOptions.model_fields.items():
        assert field.annotation is (UUID if name == "user_id" else bool)
        assert field.is_required()
    fields = identity.SelectedOwnContacts.model_fields
    assert set(fields) == {"email", "phone", "upi_id"}
    for field in fields.values():
        assert field.annotation == str | None
        assert field.is_required()
        assert field.repr is False


def test_required_signatures_remain_internal():
    """Keep the two specified async call signatures without guessing actor inputs."""
    options = inspect.signature(identity.get_shareable_contact_options)
    selected = inspect.signature(identity.get_selected_own_contacts)
    assert list(options.parameters) == ["user_id"]
    assert list(selected.parameters) == ["user_id", "fields"]
    assert options.parameters["user_id"].annotation is UserId
    assert selected.parameters["user_id"].annotation is UserId
    assert selected.parameters["fields"].annotation == set[str]
    assert options.return_annotation is identity.ShareableContactOptions
    assert selected.return_annotation is identity.SelectedOwnContacts


@pytest.mark.parametrize("selected", [False, True])
def test_declaration_calls_never_return_fake_success(selected):
    """Accidental calls fail before any data access, with synthetic IDs only."""
    coroutine = (
        identity.get_selected_own_contacts(new_id(), set())
        if selected
        else identity.get_shareable_contact_options(new_id())
    )
    with pytest.raises(NotImplementedError, match="declaration-only"):
        asyncio.run(coroutine)


def test_source_contains_only_required_declarations():
    """Functions contain no executable provider/DB behavior beyond explicit refusal."""
    tree = ast.parse((ROOT / "contracts/source/identity.py").read_text())
    functions = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    assert len(functions) == 2
    for node in functions:
        assert not node.decorator_list
        assert len(node.body) == 2
        assert isinstance(node.body[0], ast.Expr) and ast.get_docstring(node)
        assert isinstance(node.body[1], ast.Raise)
    assert not (ROOT / "apps/api/app/domains/identity/public.py").exists()


def test_private_contacts_are_absent_from_http_artifacts():
    """Internal declaration names do not enter health OpenAPI/TypeScript outputs."""
    schema = json.loads((ROOT / "contracts/generated/openapi.json").read_text())
    assert set(schema["paths"]) == {"/health"}
    assert set(schema["components"]["schemas"]) == {"HealthResponse"}
    types = (ROOT / "contracts/generated/types.gen.ts").read_text()
    for name in (
        "SelectedOwnContacts",
        "ShareableContactOptions",
        "get_selected_own_contacts",
        "get_shareable_contact_options",
    ):
        assert name not in types
