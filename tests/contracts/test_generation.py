"""DL-00 generation drift, live/API boundary and TypeScript consumer checks.

Negative generation probes run only in temporary synthetic repository trees.
The source repository/generated artifacts are never changed by these tests.
Local locked Node dependencies are required; tests never download tools.
"""

import asyncio
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = (
    "apps/api/app/contracts/health.py",
    "apps/api/app/contracts/domain_types.py",
    "apps/api/app/domains/identity/public.py",
    "apps/api/app/domains/listings/public.py",
    "apps/api/app/domains/search/public.py",
    "apps/api/app/domains/conversations/public.py",
    "contracts/generated/openapi.json",
    "contracts/generated/types.gen.ts",
)
SOURCE_FILES = (
    "contracts/__init__.py",
    "contracts/source/__init__.py",
    "contracts/source/health.py",
    "contracts/source/types.py",
    "contracts/source/identity.py",
    "contracts/source/listings.py",
    "contracts/source/search.py",
    "contracts/source/conversations.py",
)


@pytest.fixture(autouse=True)
def isolated_contract_environment(monkeypatch):
    """Keep real API import independent of developer credentials/settings."""
    for name in tuple(os.environ):
        if name.startswith(("CLIP_", "AWS_")):
            monkeypatch.delenv(name)
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")


@pytest.fixture
def tree(tmp_path):
    """Copy every canonical source/core input and output into an isolated project."""
    root = tmp_path / "project"
    for relative in (
        "package.json",
        "package-lock.json",
        "scripts/generate_contracts.py",
        "scripts/generate_types.mjs",
        "apps/api/app/__init__.py",
        *(
            f"apps/api/app/core/{path.name}"
            for path in (ROOT / "apps/api/app/core").glob("*.py")
        ),
        *SOURCE_FILES,
        *OUTPUTS,
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    (root / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)
    (root / "home").mkdir()
    return root


def run_generator(root, mode):
    """Run actual generation with bounded clean child settings and local tools."""
    return subprocess.run(
        [sys.executable, "-B", str(root / "scripts/generate_contracts.py"), mode],
        cwd=root,
        env={
            "PATH": os.environ["PATH"],
            "HOME": str(root / "home"),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=90,
    )


def bytes_of_outputs(root):
    """Snapshot every registered byte or absence to detect unintended mutation."""
    return {
        relative: (root / relative).read_bytes() if (root / relative).exists() else None
        for relative in OUTPUTS
    }


def test_generation_repeatability(tree):
    """Two fresh renders reproduce the committed bytes and check-only writes none."""
    original = bytes_of_outputs(tree)
    for _ in range(2):
        assert run_generator(tree, "generate").returncode == 0
        assert bytes_of_outputs(tree) == original
    assert run_generator(tree, "check").returncode == 0
    assert bytes_of_outputs(tree) == original


@pytest.mark.parametrize("relative", OUTPUTS)
@pytest.mark.parametrize("missing", [False, True])
def test_stale_or_missing_artifact_fails_without_writes(tree, relative, missing):
    """Reject stale/missing Python, JSON and TS artifacts and recover by generation."""
    path = tree / relative
    if missing:
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\nsynthetic-drift\n")
    before = bytes_of_outputs(tree)
    result = run_generator(tree, "check")
    assert result.returncode == 1
    assert relative in result.stdout
    assert bytes_of_outputs(tree) == before
    assert run_generator(tree, "generate").returncode == 0
    assert bytes_of_outputs(tree) == bytes_of_outputs(ROOT)


def test_source_change_is_not_accepted_by_stale_output(tree):
    """A changed declaration requires new outputs; check does not rewrite them."""
    source = tree / "contracts/source/health.py"
    source.write_text(
        source.read_text().replace(
            '"summary": "Health"', '"summary": "Synthetic change"'
        )
    )
    before = bytes_of_outputs(tree)
    assert run_generator(tree, "check").returncode == 1
    assert bytes_of_outputs(tree) == before


@pytest.mark.parametrize("package", ["typescript", "@hey-api/openapi-ts"])
def test_wrong_tool_pin_fails_closed(tree, package):
    """Reject mismatched manifest/lock/install instead of selecting an implicit tool."""
    path = tree / "package.json"
    manifest = json.loads(path.read_text())
    manifest["devDependencies"][package] = "0.0.0"
    path.write_text(json.dumps(manifest))
    before = bytes_of_outputs(tree)
    assert run_generator(tree, "generate").returncode == 1
    assert bytes_of_outputs(tree) == before


def test_missing_local_tool_does_not_fetch(tree):
    """Absent dependencies fail preflight; no npm/npx installation is attempted."""
    (tree / "node_modules").unlink()
    before = bytes_of_outputs(tree)
    result = run_generator(tree, "generate")
    assert result.returncode == 1
    assert "npm ci" in result.stderr
    assert not (tree / "node_modules").exists()
    assert bytes_of_outputs(tree) == before


@pytest.mark.parametrize(
    "source",
    [
        "raise ValueError('synthetic-source-detail')",
        "def invalid('synthetic-source-detail'):",
    ],
)
def test_source_failure_is_sanitized(tree, source):
    """Bad source fails without printing source text or changing any output."""
    (tree / "contracts/source/health.py").write_text(source)
    before = bytes_of_outputs(tree)
    result = run_generator(tree, "generate")
    assert result.returncode == 1
    assert "synthetic-source-detail" not in result.stdout + result.stderr
    assert bytes_of_outputs(tree) == before


def without_provenance(schema):
    """Ignore only explicit build provenance, preserving all HTTP schema details."""
    schema = deepcopy(schema)
    schema.pop("x-clip-generator-format", None)
    return schema


async def asgi_get(app, path):
    """Issue one in-process GET without opening sockets or starting threads."""
    messages = []
    request_received = False

    async def receive():
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}
        request_received = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    raw_path = path.encode("ascii")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": raw_path,
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    response_start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return response_start["status"], json.loads(response_body)


def test_actual_api_schema_matches_generated_contract():
    """Real API wire schemas match the implemented health/Listings/wanted subset."""
    from app.main import app

    actual = app.openapi()
    declared = json.loads((ROOT / "contracts/generated/openapi.json").read_text())
    assert declared["x-clip-generator-format"] == 2
    assert actual["info"] == declared["info"]
    implemented_paths = {
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
        "/listings/{listing_id}/selection",
        "/listings/{listing_id}/conversations/{conversation_id}/offer",
        "/listings/{listing_id}/conversations/{conversation_id}/offer-withdrawals",
        "/image-uploads",
        "/image-uploads/{upload_id}/confirm",
        "/image-uploads/{upload_id}",
        "/images/{image_id}/delivery",
    }
    assert set(actual["paths"]) == implemented_paths
    # Runtime subclasses add validation without changing the reviewed body
    # shape. Verify all constraints before normalizing only their local ref names.
    body_aliases = {
        "WantedCreate": "CreateWantedRequest",
        "DraftTitle": "DraftMatchRequest",
        "WantedPatch": "WantedRequestPatch",
        "WantedState": "WantedRequestStateChange",
    }
    for runtime, canonical in body_aliases.items():
        runtime_schema = deepcopy(actual["components"]["schemas"][runtime])
        canonical_schema = deepcopy(declared["components"]["schemas"][canonical])
        for schema in (runtime_schema, canonical_schema):
            schema.pop("title", None)
            schema.pop("description", None)
        assert runtime_schema == canonical_schema
    for path in implemented_paths:
        # Other declared operations remain unmounted. Compare every live
        # operation while retaining exact operation IDs and wire metadata.
        for method, operation in actual["paths"][path].items():
            if method in {"get", "put", "post", "delete", "patch", "options", "head"}:
                declared_operation = deepcopy(declared["paths"][path][method])
                actual_operation = deepcopy(operation)
                # Descriptions and tags are presentation metadata; the route
                # identifier and HTTP input/output schemas are the wire contract.
                for metadata in (declared_operation, actual_operation):
                    metadata.pop("description", None)
                    metadata.pop("tags", None)
                if "requestBody" in actual_operation:
                    schema = actual_operation["requestBody"]["content"][
                        "application/json"
                    ]["schema"]
                    for runtime, canonical in body_aliases.items():
                        if schema.get("$ref") == "#/components/schemas/" + runtime:
                            schema["$ref"] = "#/components/schemas/" + canonical
                assert declared_operation == actual_operation
    assert (
        actual["components"]["schemas"]["HealthResponse"]
        == declared["components"]["schemas"]["HealthResponse"]
    )
    contract_operation_ids = {
        operation["operationId"]
        for path in declared["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    assert len(contract_operation_ids) == 53
    assert {
        "identity_start_microsoft_login_attempt",
        "identity_read_csrf_token",
    } <= contract_operation_ids
    assert asyncio.run(asgi_get(app, "/health")) == (200, {"status": "ok"})
    for path in ("/openapi.json", "/docs", "/redoc"):
        status, _ = asyncio.run(asgi_get(app, path))
        assert status == 404


@pytest.mark.parametrize("mutation", ["extra", "missing", "response", "operation"])
def test_schema_comparison_detects_contract_changes(mutation):
    """Prove contract comparisons detect route and wire-shape drift."""
    from scripts.generate_contracts import declared_schema, load_sources

    health, domains = load_sources()
    actual = declared_schema(health, domains)
    expected = json.loads((ROOT / "contracts/generated/openapi.json").read_text())
    if mutation == "extra":
        actual["paths"]["/synthetic-extra"] = deepcopy(actual["paths"]["/health"])
    elif mutation == "missing":
        actual["paths"].pop("/listings")
    elif mutation == "response":
        actual["components"]["schemas"]["ListingSummary"]["properties"][
            "asking_price_paise"
        ]["minimum"] = 1
    else:
        actual["paths"]["/listings"]["get"]["operationId"] = "syntheticChanged"
    assert without_provenance(actual) != without_provenance(expected)


def test_schema_build_does_not_import_real_application(monkeypatch):
    """Import/generate only declarations, keeping real settings and services unused."""
    spec = importlib.util.spec_from_file_location(
        "clip_contract_generator_probe", ROOT / "scripts/generate_contracts.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    # Importing the real app would attempt to use this sentinel module.
    monkeypatch.setitem(sys.modules, "app.main", None)
    health, domains = generator.load_sources()
    schema = generator.declared_schema(health, domains)
    assert len(schema["paths"]) == 46
    assert "/auth/microsoft/login-attempts" in schema["paths"]
    assert "/auth/csrf" in schema["paths"]


def test_generated_types_accept_valid_consumer_reject_wrong_status(tmp_path):
    """Use the pinned compiler for valid consumer code and a wrong-literal control."""
    node = shutil.which("node")
    assert node
    command = [
        node,
        str(ROOT / "node_modules/typescript/bin/tsc"),
        "--noEmit",
        "--strict",
        "--skipLibCheck",
        "--target",
        "ES2022",
        "--module",
        "ESNext",
        "--moduleResolution",
        "Bundler",
    ]
    sample = ROOT / "tests/contracts/health_consumer.ts"
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path)}
    valid = subprocess.run(
        command
        + [str(sample), str(ROOT / "tests/contracts/search_response_consumer.ts")],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert valid.returncode == 0
    invalid = tmp_path / "invalid.ts"
    source = sample.read_text().replace(
        "../../contracts/generated/types.gen",
        (ROOT / "contracts/generated/types.gen").as_posix(),
    )
    invalid.write_text(source.replace("status: 'ok'", "status: 'synthetic-invalid'"))
    rejected = subprocess.run(
        command + [str(invalid)], env=env, capture_output=True, text=True, timeout=30
    )
    assert rejected.returncode != 0
    assert "TS2322" in rejected.stdout


@pytest.mark.parametrize(
    "reference",
    ["https://synthetic.invalid/schema", "file:///synthetic-private-schema"],
)
def test_types_helper_rejects_external_references(tmp_path, reference):
    """Reject remote/file refs before resolution, without echoing their values."""
    work = tmp_path / "clip-contracts-negative"
    work.mkdir()
    source = work / "openapi.json"
    source.write_text(
        json.dumps(
            {
                "openapi": "3.1.0",
                "info": {"title": "Synthetic", "version": "1"},
                "paths": {},
                "components": {"schemas": {"Bad": {"$ref": reference}}},
            }
        )
    )
    node = shutil.which("node")
    assert node
    result = subprocess.run(
        [
            node,
            str(ROOT / "scripts/generate_types.mjs"),
            str(source),
            str(work / "types"),
        ],
        cwd=work,
        env={"PATH": os.environ["PATH"], "HOME": str(work)},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0
    assert "Only local schema references are permitted" in result.stderr
    assert reference not in result.stdout + result.stderr
    assert not (work / "types").exists()


def test_version_has_one_editable_source():
    """Source, generated runtime and contract schema share HTTP version 0.1.0."""
    from app.contracts.health import CONTRACT_VERSION
    from app.main import app

    spec = importlib.util.spec_from_file_location(
        "clip_version_source", ROOT / "contracts/source/health.py"
    )
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    declared = json.loads((ROOT / "contracts/generated/openapi.json").read_text())
    assert (
        source.CONTRACT_VERSION
        == CONTRACT_VERSION
        == app.version
        == declared["info"]["version"]
    )
