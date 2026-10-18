"""Prove the PD-11 checker accepts legal boundaries and rejects violations.

All snippets are synthetic and parsed as data; CLI tests use temporary trees,
never modify application source and never access a database or provider.
"""

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "clip_boundary_checker", ROOT / "scripts/check_boundaries.py"
)
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)
SEARCH = "apps/api/app/domains/search/service.py"
PUBLIC = "apps/api/app/domains/search/public.py"


@pytest.mark.parametrize(
    "source",
    [
        "from app.domains.identity.service import User",
        "import app.domains.identity.models as m",
        "from app.domains.identity import User",
        "from app.domains import identity",
        "from ..identity.models import User",
        "from ..identity import public",
        "from app.domains.identity.public import *",
        "from app.domains.identity.public import _private",
        "from app.domains.identity.public._private import User",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n from app.domains.identity.models import User",
        "import importlib as i\ni.import_module('app.domains.identity.models')",
        "from importlib import import_module as load\nload('app.domains.identity.models')",
        "__import__('app.domains.identity.models')",
        "import importlib\nimportlib.import_module(module_name)",
        "import importlib\nimportlib.import_module('.models', 'app.domains.identity')",
        "import app.domains.identity.public\napp.domains.identity.models.User()",
        "import app.domains.identity.public as p\np._internal()",
        "from app.domains.unknown.public import Something",
    ],
)
def test_forbidden_imports(source):
    """Reject absolute, relative, aliased, type-only and recognized dynamic bypasses."""
    findings, _ = checker.inspect_source(SEARCH, source)
    assert findings


@pytest.mark.parametrize(
    "source",
    [
        "from app.domains.identity.public import UserId",
        "import app.domains.identity.public as identity",
        "from app.domains.search.internal import helper",
        "from .internal import helper",
        "from app.core.identifiers import parse_id",
        "from contracts.generated.types import SharedType",
        "import importlib\nimportlib.import_module('app.domains.identity.public')",
        "sql = 'SELECT * FROM search.wanted_requests'",
        "sql = 'UPDATE search.wanted_requests SET revision=2'",
        "table = Table('wanted_requests', schema='search')",
        "class Model:\n __table_args__ = {'schema': 'search'}",
        '"""Example: SELECT * FROM identity.users is forbidden."""\nfrom app.core import identifiers',
    ],
)
def test_allowed_domain_code(source):
    """Accept owning persistence/public consumers without false-positive docstrings."""
    findings, _ = checker.inspect_source(SEARCH, source)
    assert findings == []


@pytest.mark.parametrize(
    "source",
    [
        "sql = 'SELECT * FROM identity.users'",
        "sql = 'SELECT x FROM search.wanted_requests r JOIN listings.sale_listings s ON true'",
        "sql = 'UPDATE identity.users SET status=1'",
        "sql = 'INSERT INTO identity.users VALUES (1)'",
        "sql = 'DELETE FROM identity.users'",
        "sql = 'TRUNCATE TABLE identity.users'",
        'sql = \'SELECT * FROM "identity"."users"\'',
        "sql = 'SeLeCt * FrOm IDENTITY.users'",
        "sql = 'SELECT * FROM ' + 'identity.users'",
        "sql = f'SELECT * FROM identity.users WHERE id={user_id}'",
        "sql = 'SET search_path TO identity'",
        "sql = 'SET LOCAL search_path = identity'",
        "table = Table('users', metadata, schema='identity')",
        "class Model:\n __table_args__ = {'schema':'identity'}",
    ],
)
def test_foreign_table_access(source):
    """Recognize qualified literal SQL and common explicit ORM schema mappings."""
    findings, _ = checker.inspect_source(SEARCH, source)
    assert any(f.rule == "private-table-access" for f in findings)


@pytest.mark.parametrize(
    "path, source, rule",
    [
        (
            "apps/api/app/core/helper.py",
            "from app.domains.identity.public import User",
            "technical-domain-import",
        ),
        (
            "contracts/source/identity.py",
            "from app.domains.identity.public import User",
            "technical-domain-import",
        ),
        (
            "contracts/source/identity.py",
            "from app.main import app",
            "contract-implementation-import",
        ),
        (PUBLIC, "from .models import PrivateModel", "private-domain-import"),
        (PUBLIC, "from sqlalchemy import Session", "public-implementation-type"),
        (PUBLIC, "from fastapi import Request", "public-implementation-type"),
        (PUBLIC, "sql='SELECT * FROM search.wanted_requests'", "private-table-access"),
        (
            "apps/api/app/main.py",
            "from app.domains.identity.router import router",
            "private-domain-import",
        ),
    ],
)
def test_technical_and_public_boundaries(path, source, rule):
    """Keep core/source/public declarations free of domain implementation leakage."""
    findings, _ = checker.inspect_source(path, source)
    assert any(f.rule == rule for f in findings)


def test_source_and_public_shared_types():
    """Shared technical and public contract types remain usable before providers exist."""
    for path in ("contracts/source/identity.py", PUBLIC):
        findings, _ = checker.inspect_source(
            path,
            "from app.core.identifiers import parse_id\nfrom pydantic import BaseModel",
        )
        assert not findings


def test_syntax_failure():
    """Invalid syntax must fail the scan instead of silently skipping a file."""
    findings, _ = checker.inspect_source(SEARCH, "def invalid(:")
    assert findings[0].rule == "invalid-python"


def test_relative_package_public_reexport():
    """A generated public module cannot re-export its own private package objects."""
    findings, _ = checker.inspect_source(PUBLIC, "from . import internal")
    assert any(f.rule == "private-domain-import" for f in findings)


def put(root, relative, source):
    """Create only a temporary synthetic source tree for scanner and CLI tests."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def test_cycle_detection(tmp_path):
    """Reject transitive domain import cycles even through legal public paths."""
    for domain, target in (
        ("identity", "listings"),
        ("listings", "search"),
        ("search", "identity"),
    ):
        put(
            tmp_path,
            f"apps/api/app/domains/{domain}/public.py",
            f"from app.domains.{target}.public import Type",
        )
    assert any(f.rule == "domain-dependency-cycle" for f in checker.scan(tmp_path))


def test_scan_scope_without_execution(tmp_path):
    """Parse production/source files but exclude migrations and database tests."""
    put(tmp_path, SEARCH, "raise RuntimeError('must not execute')")
    put(
        tmp_path,
        "database/tests/probe.py",
        "from app.domains.identity.private import Thing",
    )
    put(
        tmp_path,
        "contracts/source/identity.py",
        "from app.domains.identity.private import Thing",
    )
    findings = checker.scan(tmp_path)
    assert findings and all(f.path.startswith("contracts/source/") for f in findings)


def test_exact_composition_exception(tmp_path, monkeypatch):
    """An explicit exact-file/module exception grants no broader private access."""
    monkeypatch.setattr(
        checker,
        "COMPOSITION_IMPORTS",
        {"apps/api/app/main.py": frozenset({"app.domains.identity.router"})},
    )
    assert not checker.inspect_source(
        "apps/api/app/main.py", "from app.domains.identity.router import router"
    )[0]
    assert checker.inspect_source(
        "apps/api/app/main.py", "from app.domains.identity.models import User"
    )[0]
    assert checker.inspect_source(
        SEARCH, "from app.domains.identity.router import router"
    )[0]


def test_cli_drift_and_recovery(tmp_path):
    """Real CLI rejects an introduced violation, preserves source, then passes recovery."""
    for source, expected in (
        ("from app.domains.identity.public import User", 0),
        ("from app.domains.identity.private import User", 1),
        ("from app.core.identifiers import parse_id", 0),
    ):
        put(tmp_path, SEARCH, source)
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "scripts/check_boundaries.py"),
                "--root",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        )
        assert result.returncode == expected, result.stderr
        assert (tmp_path / SEARCH).read_text() == source
        if expected:
            assert "private-domain-import" in result.stdout
            assert source not in result.stdout


def test_repository_boundaries():
    """Keep the actual foundation covered by the normal root pytest command."""
    assert checker.scan(ROOT) == []
