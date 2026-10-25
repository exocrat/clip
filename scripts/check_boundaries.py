"""Static Python import/table guard for PD-11's declared domain boundary.

Scans application code and editable contract source without importing either.
Literal SQL, common ORM schema declarations and recognized dynamic imports are
checked. Arbitrary reflection, computed SQL and semantic business call graphs
still require review and integration tests. Database migrations/tests are not
runtime consumers and are deliberately outside the scan.
"""

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re

DOMAINS = frozenset({"identity", "listings", "search", "conversations"})
# The ASGI composition root wires reviewed Identity HTTP bindings, Listings
# implementation modules and Conversations public declarations. Keep imports exact.
COMPOSITION_IMPORTS: dict[str, frozenset[str]] = {
    "apps/api/app/main.py": frozenset(
        {
            "app.domains.listings.s3_storage",
            "app.domains.listings.s3_storage.S3ListingsImageStorage",
        }
    ),
    "apps/api/app/application.py": frozenset(
        {
            "app.domains.identity.http",
            "app.domains.identity.http.IdentityHttpDependencies",
            "app.domains.identity.http.install_identity_http",
            "app.domains.search.saved_routes",
            "app.domains.search.saved_routes.router",
            "app.domains.search.saved_store",
            "app.domains.search.saved_store.PostgresSavedStore",
            "app.domains.search.wanted_routes",
            "app.domains.search.wanted_routes.router",
            "app.domains.search.wanted_store",
            "app.domains.search.wanted_store.PostgresWantedStore",
            "app.domains.listings.routes",
            "app.domains.listings.routes.router",
            "app.domains.listings.integrations",
            "app.domains.listings.integrations.PublicListingsIdentity",
            "app.domains.listings.postgres_store",
            "app.domains.listings.postgres_store.PostgresListingsStore",
            "app.domains.listings.search_access",
            "app.domains.listings.search_access.ListingsSearchAccess",
            "app.domains.listings.search_runtime",
            "app.domains.listings.search_runtime.search_runtime",
            "app.domains.listings.search_runtime.finish_search_cleanup",
            "app.domains.listings.s3_storage",
            "app.domains.listings.s3_storage.S3ListingsImageStorage",
            "app.domains.listings.isolated_test",
            "app.domains.listings.isolated_test.require_isolated_test_database",
            "app.domains.listings.isolated_test.IsolatedListingsTestIdentity",
            "app.domains.listings.isolated_test.isolated_test_caller",
        }
    ),
}
SQL_TABLE = re.compile(
    r'\b(?:FROM|JOIN|UPDATE|INTO|TRUNCATE(?:\s+TABLE)?)\s+"?(identity|listings|search|conversations)"?\s*\.\s*"?[a-z_][a-z_0-9]*',
    re.IGNORECASE,
)
SEARCH_PATH = re.compile(
    r'\bSET\s+(?:LOCAL\s+|SESSION\s+)?search_path\s*(?:=|TO)\s*"?(identity|listings|search|conversations)\b',
    re.IGNORECASE,
)


@dataclass(frozen=True, order=True)
class Finding:
    """Safe location/rule metadata; never include SQL or literal data in output."""

    path: str
    line: int
    rule: str


def dotted(node):
    """Resolve a syntactic name/attribute chain without evaluating source code."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted(node.value)
        return f"{parent}.{node.attr}" if parent else ""
    return ""


def literal(node):
    """Resolve constant string concatenation and literal portions of f-strings."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return literal(node.left) + literal(node.right)
    if isinstance(node, ast.JoinedStr):
        return "".join(
            literal(value) if isinstance(value, ast.Constant) else "?"
            for value in node.values
        )
    return ""


def inspect_source(path, source):
    """Return violations and cross-domain dependency edges for one relative path."""
    findings = set()
    edges = set()
    parts = Path(path).parts
    domain = (
        parts[4]
        if len(parts) > 5 and parts[:4] == ("apps", "api", "app", "domains")
        else None
    )
    public = domain is not None and parts[5:] == ("public.py",)
    core = parts[:4] == ("apps", "api", "app", "core")
    contract = parts[:2] == ("contracts", "source")
    module = (
        ".".join(parts[2:])[:-3]
        if parts[:3] == ("apps", "api", "app")
        else ".".join(parts)[:-3]
    )
    package = (
        module.removesuffix(".__init__")
        if parts[-1] == "__init__.py"
        else module.rpartition(".")[0]
    )
    aliases = {}

    def report(node, rule):
        """Deduplicate a fixed finding without echoing arbitrary source values."""
        findings.add(Finding(str(path), getattr(node, "lineno", 1), rule))

    def target(node, name, symbols=()):
        """Apply the same ownership policy to absolute, relative and dynamic imports."""
        if public and (
            name == "sqlalchemy"
            or name.startswith("sqlalchemy.")
            or name.startswith("fastapi")
            and any(symbol in {"Request", "Response", "Depends"} for symbol in symbols)
        ):
            report(node, "public-implementation-type")
        if not (name == "app.domains" or name.startswith("app.domains.")):
            if (
                contract
                and name.startswith("app.")
                and not name.startswith("app.core.")
            ):
                report(node, "contract-implementation-import")
            if core and name.startswith("app.") and not name.startswith("app.core."):
                report(node, "core-application-import")
            return
        segments = name.split(".")
        owner = segments[2] if len(segments) > 2 else None
        if owner not in DOMAINS:
            report(node, "undeclared-domain-import")
            return
        if domain and owner != domain:
            edges.add((domain, owner))
        is_public = len(segments) >= 4 and segments[3] == "public"
        if core or contract:
            report(node, "technical-domain-import")
        elif public or owner != domain:
            if not is_public and name not in COMPOSITION_IMPORTS.get(str(path), ()):
                report(node, "private-domain-import")
            if is_public and (
                any(symbol == "*" or symbol.startswith("_") for symbol in symbols)
                or any(segment.startswith("_") for segment in segments[4:])
            ):
                report(node, "private-public-symbol")

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [Finding(str(path), exc.lineno or 1, "invalid-python")], edges
    # Docstrings explain SQL examples but are not executable SQL declarations.
    docstrings = set()
    for node in ast.walk(tree):
        if (
            isinstance(
                node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            )
            and node.body
        ):
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(id(first.value))
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
                target(node, alias.name)
        if isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                levels = package.split(".")
                if node.level > len(levels):
                    report(node, "invalid-relative-import")
                    continue
                base = ".".join(
                    levels[: len(levels) - node.level + 1] + ([base] if base else [])
                )
            target(node, base, tuple(alias.name for alias in node.names))
            for alias in node.names:
                full = base + "." + alias.name
                aliases[alias.asname or alias.name] = full
                if base == "app.domains" or base in {
                    "app.domains." + d for d in DOMAINS
                }:
                    target(node, full)
                if public and alias.name == "*":
                    report(node, "public-wildcard-import")

    def expand(name):
        """Expand known syntactic aliases for recognized attribute/call checks."""
        head, dot, tail = name.partition(".")
        return aliases.get(head, head) + (dot + tail if dot else "")

    def table_owner(node, owner):
        """Only owning domain code may name its authoritative runtime tables."""
        if owner in DOMAINS and (owner != domain or public):
            report(node, "private-table-access")

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            name = expand(dotted(node))
            if name.startswith("app.domains."):
                target(node, name)
        if isinstance(node, ast.Call):
            name = expand(dotted(node.func))
            if name in {"importlib.import_module", "__import__", "builtins.__import__"}:
                value = literal(node.args[0]) if node.args else ""
                if not value:
                    report(node, "computed-dynamic-import")
                elif value.startswith("."):
                    report(node, "relative-dynamic-import")
                else:
                    target(node, value)
            for keyword in node.keywords:
                if keyword.arg == "schema":
                    table_owner(node, literal(keyword.value).lower())
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if key is not None and literal(key) == "schema":
                    table_owner(node, literal(value).lower())
        if (
            isinstance(node, (ast.Constant, ast.BinOp, ast.JoinedStr))
            and id(node) not in docstrings
        ):
            text = literal(node)
            for pattern in (SQL_TABLE, SEARCH_PATH):
                for match in pattern.finditer(text):
                    table_owner(node, match.group(1).lower())
    return sorted(findings), edges


def scan(root):
    """Scan fixed production/source roots and detect cycles in declared imports."""
    findings, edges = [], set()
    for directory in (root / "apps/api/app", root / "contracts/source"):
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            found, dependencies = inspect_source(
                path.relative_to(root).as_posix(), path.read_text()
            )
            findings.extend(found)
            edges.update(dependencies)

    def reaches(start, goal, visited):
        """Bound graph traversal by four domains, including declaration-only edges."""
        if start == goal:
            return True
        if start in visited:
            return False
        return any(
            reaches(right, goal, visited | {start})
            for left, right in edges
            if left == start
        )

    if any(reaches(right, left, set()) for left, right in edges):
        findings.append(Finding("apps/api/app/domains", 1, "domain-dependency-cycle"))
    return sorted(set(findings))


def main():
    """Expose a local read-only CLI; nonzero means policy violation or scan error."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    root = parser.parse_args().root.resolve()
    if not (root / "apps/api/app").is_dir():
        parser.error("Expected repository API source root")
    findings = scan(root)
    for finding in findings:
        print(f"{finding.path}:{finding.line}: {finding.rule}")
    print(f"Python boundary check: {len(findings)} violation(s)")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
