"""Prove domain public declarations are generated, explicit, and behavior-free."""

import ast
import importlib
import inspect
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from scripts.generate_contracts import DOMAINS, load_sources

ROOT = Path(__file__).resolve().parents[2]
BOUND_IDENTITY = {
    "check_account_eligibility": ["AccountEligibility", "user_id", "required_class"],
    "get_shareable_contact_options": [
        "ShareableContactOptions",
        "caller",
        "conversation_id",
    ],
    "get_selected_own_contacts": [
        "SelectedOwnContacts",
        "caller",
        "conversation_id",
        "fields",
    ],
}

EXPECTED_CALLABLES = {
    "identity": {
        "check_account_eligibility",
        "get_shareable_contact_options",
        "get_selected_own_contacts",
        "resolve_notification_recipient",
    },
    "listings": {
        "query_available_listings",
        "read_save_target",
        "read_saved_listing_summaries",
        "read_active_categories",
        "read_category_display",
    },
    "search": set(),
    "conversations": {
        "open_or_create_listing_conversation",
        "find_existing_listing_conversation",
        "open_or_create_wanted_conversation",
        "find_existing_wanted_conversation",
        "check_listing_thread_participant",
        "persist_listing_offer",
        "get_origin_activity",
        "mark_origin_retired",
        "claim_due_notification_intents",
        "read_notification_dispatch_context",
        "record_notification_attempt",
    },
}


def test_public_callable_names_match_reviewed_registry():
    """Import paths and stable operation names remain tied to Step 9 tables."""
    sources = {
        name: importlib.import_module(f"contracts.source.{name}") for name in DOMAINS
    }
    for domain in DOMAINS:
        public = importlib.import_module(f"app.domains.{domain}.public")
        names = {
            node.name
            for node in ast.parse(
                (ROOT / f"contracts/source/{domain}.py").read_text()
            ).body
            if isinstance(node, ast.AsyncFunctionDef)
        }
        assert names == EXPECTED_CALLABLES[domain]
        assert all(inspect.iscoroutinefunction(getattr(public, name)) for name in names)
        assert sources[domain].HTTP_OPERATIONS

    contract = (ROOT / "contracts/combined.md").read_text()
    documented = {}
    for domain in DOMAINS:
        documented[domain] = set(
            re.findall(rf"app\.domains\.{domain}\.public\.([a-z_]+)\(", contract)
        )
    assert documented == EXPECTED_CALLABLES


def test_conversations_protocol_matches_internal_callable_signatures():
    """The injectable Conversations protocol stays aligned with declarations."""
    public = importlib.import_module("app.domains.conversations.public")
    protocol = public.ConversationsPublic
    declaration_names = EXPECTED_CALLABLES["conversations"]
    protocol_names = {
        name
        for name, value in vars(protocol).items()
        if inspect.iscoroutinefunction(value)
    }

    assert protocol_names == declaration_names
    for name in declaration_names:
        declared = inspect.signature(getattr(public, name))
        method = inspect.signature(getattr(protocol, name))
        assert tuple(method.parameters.values())[1:] == tuple(
            declared.parameters.values()
        )
        assert method.return_annotation == declared.return_annotation


def test_http_registry_matches_combined_contract_and_openapi():
    """All documented HTTP operations map explicitly to generated OpenAPI routes."""
    _, sources = load_sources()
    registered = {
        operation["operation_id"]
        for module in sources.values()
        for operation in module.HTTP_OPERATIONS
    }
    documented = set(
        re.findall(
            r" — ((?:identity|listings|search|conversations)_[a-z_]+) \|",
            (ROOT / "contracts/combined.md").read_text(),
        )
    )
    assert registered == documented


def test_domain_routes_declare_shared_internal_error_envelope():
    """Document the stable 500 envelope for every generated HTTP operation."""
    import json

    schema = json.loads((ROOT / "contracts/generated/openapi.json").read_text())
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            if (
                not isinstance(operation, dict)
                or "operationId" not in operation
                or operation["operationId"] == "health_health_get"
            ):
                continue
            response = operation["responses"]["500"]
            assert response["content"]["application/json"]["schema"]["$ref"] == (
                "#/components/schemas/ErrorEnvelope"
            )


def test_every_generated_callable_fails_closed_without_implementation():
    """Generated domain modules cannot return placeholders or fabricated success."""
    for domain in DOMAINS:
        tree = ast.parse(
            (ROOT / f"apps/api/app/domains/{domain}/public.py").read_text()
        )
        functions = [
            node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
        ]
        assert {node.name for node in functions} == EXPECTED_CALLABLES[domain]
        for function in functions:
            assert ast.get_docstring(function)
            assert len(function.body) == 2
            refusal = function.body[1]
            if domain == "identity" and function.name in BOUND_IDENTITY:
                assert isinstance(refusal, ast.Return) and isinstance(
                    refusal.value, ast.Await
                )
                call = refusal.value.value
                assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                assert call.func.id == "_dispatch_runtime"
                assert ast.literal_eval(call.args[0]) == "identity." + function.name
                assert [argument.id for argument in call.args[1:]] == BOUND_IDENTITY[
                    function.name
                ]
            else:
                assert isinstance(refusal, ast.Raise)
                assert isinstance(refusal.exc, ast.Call)
                assert isinstance(refusal.exc.func, ast.Name)
                assert refusal.exc.func.id == "NotImplementedError"


def test_generated_modules_preserve_source_except_approved_dispatch():
    """Only import rewrites and the reviewed selected-function technical body may differ."""
    for domain in DOMAINS:
        source = (ROOT / f"contracts/source/{domain}.py").read_text()
        expected = source.replace(
            "from contracts.source.types import",
            "from app.contracts.domain_types import",
        )
        generated = (ROOT / f"apps/api/app/domains/{domain}/public.py").read_text()
        if domain != "identity":
            assert generated.splitlines()[0].startswith("# Generated declaration-only")
            assert generated.partition("\n")[2].lstrip("\n") == expected
            continue
        assert generated.splitlines()[0].startswith(
            "# Generated typed runtime identity"
        )
        original = ast.parse(expected)
        actual = ast.parse(generated.partition("\n")[2])
        before = {
            node.name: node
            for node in original.body
            if isinstance(node, ast.AsyncFunctionDef)
        }
        after = {
            node.name: node
            for node in actual.body
            if isinstance(node, ast.AsyncFunctionDef)
        }
        # The independent structural test above verifies exactly what the one
        # replacement does; restore it here to prove everything else is unchanged.
        for name in BOUND_IDENTITY:
            after[name].body[1] = before[name].body[1]
        assert ast.dump(actual, include_attributes=False) == ast.dump(
            original, include_attributes=False
        )


def test_only_implemented_domain_http_routes_are_installed():
    """Mount only implemented Listings/wanted routes, leaving future declarations out."""
    from app.main import app

    # Inspect the public schema instead of FastAPI's internal router objects.
    # Newer FastAPI versions can keep included routers as a single internal
    # object, while OpenAPI still shows the actual installed endpoints.
    paths = set(app.openapi()["paths"])
    assert paths == {
        "/conversations",
        "/conversations/unread-count",
        "/conversations/{conversation_id}",
        "/conversations/{conversation_id}/entries",
        "/conversations/{conversation_id}/messages",
        "/conversations/{conversation_id}/offer",
        "/conversations/{conversation_id}/contact-options",
        "/conversations/{conversation_id}/contact-preparations",
        "/conversations/{conversation_id}/contact-shares",
        "/conversations/{conversation_id}/read-state",
        "/conversations/{conversation_id}/keys",
        "/conversations/{conversation_id}/prekey-bundle",
        "/me/conversation-key",
        "/me/conversation-prekeys",
        "/me/saved-listings",
        "/me/saved-listings/{listing_id}",
        "/wanted-requests",
        "/wanted-requests/draft-matches",
        "/me/wanted-requests",
        "/wanted-requests/{request_id}",
        "/wanted-requests/{request_id}/availability",
        "/wanted-requests/{request_id}/conversations",
        "/health",
        "/catalogue",
        "/listings",
        "/listings/{listing_id}",
        "/me/listings",
        "/listings/{listing_id}/availability",
        "/listings/{listing_id}/conversations",
        "/listings/{listing_id}/selection",
        "/listings/{listing_id}/conversations/{conversation_id}/offer",
        "/listings/{listing_id}/conversations/{conversation_id}/offer-withdrawals",
        "/image-uploads",
        "/image-uploads/{upload_id}/confirm",
        "/image-uploads/{upload_id}",
        "/images/{image_id}/delivery",
    }
    assert not any(path.startswith("/auth/") for path in paths)


def test_contract_timestamps_are_aware_and_serialize_as_canonical_utc():
    """Domain contract instants reject ambiguity and serialize at fixed precision."""
    from contracts.source.types import SessionView

    session = SessionView(
        user_id=uuid4(),
        account_class="regular",
        valid_until="2030-01-02T03:04:05.12+05:30",
    )
    assert session.valid_until == datetime(2030, 1, 1, 21, 34, 5, 120000, tzinfo=UTC)
    assert session.model_dump(mode="json")["valid_until"] == (
        "2030-01-01T21:34:05.120000Z"
    )

    for invalid in (
        "2030-01-02T03:04:05",
        "2030-01-02T03:04:05.1234567Z",
        datetime(2030, 1, 2, 3, 4, 5),
    ):
        with pytest.raises(ValidationError):
            SessionView(user_id=uuid4(), account_class="regular", valid_until=invalid)


def test_contract_paise_values_are_whole_rupee_multiples():
    """Every paise-denominated contract field enforces the approved price unit."""
    from contracts.source import types as shared_types
    from contracts.source.types import CreateListingRequest

    request = {
        "title": "Desk lamp",
        "description": "Working lamp",
        "category_code": "home",
        "condition_code": "good",
        "negotiable": False,
        "pickup_area": "Campus",
        "image_upload_ids": [uuid4()],
        "operation_id": uuid4(),
    }
    with pytest.raises(ValidationError):
        CreateListingRequest(**request, asking_price_paise=1050)
    assert CreateListingRequest(**request, asking_price_paise=1100)

    paise_fields = [
        (model.__name__, name, field)
        for model in vars(shared_types).values()
        if inspect.isclass(model) and issubclass(model, BaseModel)
        for name, field in model.model_fields.items()
        if name.endswith("_paise")
    ]
    assert paise_fields
    assert all(
        any(
            getattr(metadata, "multiple_of", None) == 100 for metadata in field.metadata
        )
        for _, _, field in paise_fields
    )
