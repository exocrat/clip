"""Prove domain public declarations are generated, explicit, and behavior-free."""

import ast
import importlib
import inspect
import re
from pathlib import Path

from scripts.generate_contracts import DOMAINS, load_sources

ROOT = Path(__file__).resolve().parents[2]
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
            assert isinstance(refusal, ast.Raise)
            assert isinstance(refusal.exc, ast.Call)
            assert isinstance(refusal.exc.func, ast.Name)
            assert refusal.exc.func.id == "NotImplementedError"


def test_generated_modules_are_byte_for_byte_source_derivatives():
    """Only the controlled editable-source import rewrite differs from source."""
    for domain in DOMAINS:
        source = (ROOT / f"contracts/source/{domain}.py").read_text()
        expected = source.replace(
            "from contracts.source.types import",
            "from app.contracts.domain_types import",
        )
        generated = (ROOT / f"apps/api/app/domains/{domain}/public.py").read_text()
        assert generated.splitlines()[0].startswith("# Generated declaration-only")
        assert generated.partition("\n")[2].lstrip("\n") == expected


def test_declarations_do_not_install_unimplemented_http_routes():
    """Only implemented health is reachable; generated domain routes stay offline."""
    from app.main import app

    assert {route.path for route in app.routes} == {"/health"}
    assert not any(route.path.startswith("/auth/") for route in app.routes)
