"""Verify Identity's reviewed private contact declarations and safe outputs."""

import ast
import inspect
import json
from pathlib import Path

import pytest

from app.core.auth import CallerContext
from app.core.identifiers import UserId
from contracts.source import identity
from contracts.source.types import (
    NotificationRecipient,
    SelectedOwnContacts,
    ShareableContactOptions,
)

ROOT = Path(__file__).resolve().parents[2]


def test_required_contact_type_shapes():
    """Retain owner IDs/availability only and hide private values in repr."""
    assert identity.UserId is UserId
    assert set(ShareableContactOptions.model_fields) == {
        "user_id",
        "has_email",
        "has_phone",
        "has_upi_id",
    }
    assert all(
        field.is_required() for field in ShareableContactOptions.model_fields.values()
    )
    for model in (SelectedOwnContacts,):
        fields = model.model_fields
        assert set(fields) == {"email", "phone", "upi_id"}
        for field in fields.values():
            assert field.annotation == str | None
            assert field.is_required()
            assert field.repr is False
    assert NotificationRecipient.model_fields["email"].repr is False


def test_identity_internal_signatures_use_trusted_actor_context():
    """Bind the two contact operations and recipient resolution to server context."""
    options = inspect.signature(identity.get_shareable_contact_options)
    selected = inspect.signature(identity.get_selected_own_contacts)
    recipient = inspect.signature(identity.resolve_notification_recipient)
    assert list(options.parameters) == ["caller", "conversation_id"]
    assert options.parameters["caller"].annotation is CallerContext
    assert selected.parameters["caller"].annotation is CallerContext
    assert list(selected.parameters) == ["caller", "conversation_id", "fields"]
    assert selected.parameters["fields"].annotation == frozenset[identity.ContactField]
    assert (
        recipient.parameters["context"].annotation is identity.NotificationWorkerContext
    )
    assert list(recipient.parameters) == ["context", "recipient_id"]
    assert options.return_annotation is ShareableContactOptions
    assert selected.return_annotation is SelectedOwnContacts
    assert recipient.return_annotation == NotificationRecipient | None


def test_every_identity_function_is_declaration_only():
    """No Identity declaration reaches a provider, database or fake success."""
    tree = ast.parse((ROOT / "contracts/source/identity.py").read_text())
    functions = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    assert len(functions) == 4
    for node in functions:
        assert not node.decorator_list
        assert len(node.body) == 2
        assert isinstance(node.body[0], ast.Expr) and ast.get_docstring(node)
        assert isinstance(node.body[1], ast.Raise)
        assert isinstance(node.body[1].exc, ast.Call)
        assert isinstance(node.body[1].exc.func, ast.Name)
        assert node.body[1].exc.func.id == "NotImplementedError"


def test_internal_identity_contact_types_are_not_published_implicitly():
    """Only the explicitly mapped preparation response enters the web contract."""
    schema = json.loads((ROOT / "contracts/generated/openapi.json").read_text())
    schemas = schema["components"]["schemas"]
    assert "ShareableContactOptions" not in schemas
    assert "NotificationRecipient" not in schemas
    assert "SelectedOwnContacts" in schemas
    assert "identity_get_selected_own_contacts" not in str(schema)
    operations = [
        operation
        for path in schema["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert "identity_create_microsoft_session" in {
        operation["operationId"] for operation in operations
    }


@pytest.mark.parametrize("domain", ["identity", "listings", "search", "conversations"])
def test_generated_public_module_is_present(domain):
    """Generation materializes importable declaration modules for each owner."""
    path = ROOT / f"apps/api/app/domains/{domain}/public.py"
    assert path.is_file()
    assert "Generated declaration-only" in path.read_text().splitlines()[0]
