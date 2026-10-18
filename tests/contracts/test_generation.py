"""PD-11 generation drift, actual API schema and TypeScript consumer checks.

Negative generation probes run only in temporary synthetic repository trees.
The source repository/generated artifacts are never changed by these tests.
Local locked Node dependencies are required; tests never download tools.
"""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = (
    "apps/api/app/contracts/health.py",
    "contracts/generated/openapi.json",
    "contracts/generated/types.gen.ts",
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
    """Copy minimal generation inputs/outputs; share installed tools read-only."""
    root = tmp_path / "project"
    for relative in (
        "package.json",
        "package-lock.json",
        "contracts/source/health.py",
        "scripts/generate_contracts.py",
        "scripts/generate_types.mjs",
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


def test_actual_api_schema_matches_generated_contract():
    """Compare the actual app's routes/schema; never install the generated schema."""
    from app.main import app

    actual = app.openapi()
    declared = json.loads((ROOT / "contracts/generated/openapi.json").read_text())
    assert declared["x-clip-generator-format"] == 1
    assert without_provenance(actual) == without_provenance(declared)
    assert set(actual["paths"]) == {"/health"}
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        for path in ("/openapi.json", "/docs", "/redoc"):
            assert client.get(path).status_code == 404


@pytest.mark.parametrize("mutation", ["extra", "missing", "response", "operation"])
def test_schema_comparison_detects_contract_changes(mutation):
    """Prove parity comparison detects added/missing routes and changed wire shapes."""
    from app.main import app

    actual = deepcopy(app.openapi())
    expected = json.loads((ROOT / "contracts/generated/openapi.json").read_text())
    if mutation == "extra":
        actual["paths"]["/synthetic-extra"] = deepcopy(actual["paths"]["/health"])
    elif mutation == "missing":
        actual["paths"].pop("/health")
    elif mutation == "response":
        actual["components"]["schemas"]["HealthResponse"]["properties"]["status"][
            "const"
        ] = "changed"
    else:
        actual["paths"]["/health"]["get"]["operationId"] = "syntheticChanged"
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
    schema = generator.declared_schema(generator.health_source())
    assert set(schema["paths"]) == {"/health"}


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
        command + [str(sample)], env=env, capture_output=True, text=True, timeout=30
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
