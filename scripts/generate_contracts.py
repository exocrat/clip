"""Generate/check typed public interfaces and explicit HTTP contract artifacts.

The contract-only FastAPI app is used only to render OpenAPI. Its generated
endpoints refuse invocation and are never installed in the running API.
"""

import argparse
import ast
import importlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from fastapi import Body, FastAPI, Path as ApiPath, Query
from pydantic import BaseModel
from starlette.responses import Response

ROOT = Path(__file__).resolve().parents[1]
FORMAT_VERSION = 2
TS_VERSION = "0.99.0"
COMPILER_VERSION = "5.9.3"
TS_PACKAGE = "@hey-api/openapi-ts"
DOMAINS = ("identity", "listings", "search", "conversations")
PUBLIC_OUTPUTS = tuple(f"apps/api/app/domains/{domain}/public.py" for domain in DOMAINS)
OUTPUTS = (
    "apps/api/app/contracts/health.py",
    "apps/api/app/contracts/domain_types.py",
    *PUBLIC_OUTPUTS,
    "contracts/generated/openapi.json",
    "contracts/generated/types.gen.ts",
)
ERROR_STATUSES = (400, 401, 403, 404, 409, 422, 429, 500, 503)


def load_sources():
    """Import only editable declaration modules, with the app core on the path."""
    for path in (str(ROOT), str(ROOT / "apps/api")):
        if path not in sys.path:
            sys.path.insert(0, path)
    health = importlib.import_module("contracts.source.health")
    domains = {
        name: importlib.import_module(f"contracts.source.{name}") for name in DOMAINS
    }
    return health, domains


def _path_names(path):
    """Return the declared dynamic path fields in their URL order."""
    return re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", path)


def _endpoint(operation):
    """Build a refusing synthetic callable with the declared FastAPI signature."""
    parameters = []
    for name, annotation in operation.get("path_parameters", {}).items():
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=ApiPath(...),
                annotation=annotation,
            )
        )
    query = operation.get("query")
    if query is not None:
        parameters.append(
            inspect.Parameter(
                "query",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=Query(),
                annotation=query,
            )
        )
    body = operation.get("body")
    if body is not None:
        parameters.append(
            inspect.Parameter(
                "payload",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=Body(...),
                annotation=body,
            )
        )

    async def declaration_only(**kwargs):
        """Reject accidental use; declarations never return fake success."""
        del kwargs
        raise NotImplementedError("Contract declaration has no implementation")

    declaration_only.__name__ = operation["operation_id"]
    declaration_only.__qualname__ = declaration_only.__name__
    declaration_only.__signature__ = inspect.Signature(parameters)
    return declaration_only


def _validate_operation(domain, operation, seen):
    """Reject ambiguous or implicit HTTP mappings before emitting a schema."""
    method = operation.get("method")
    path = operation.get("path")
    operation_id = operation.get("operation_id")
    if (
        method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        or not isinstance(path, str)
        or not isinstance(operation_id, str)
        or not re.fullmatch(r"[a-z][a-z0-9_]+", operation_id)
    ):
        raise ValueError("Invalid explicit HTTP operation metadata")
    key = (method, path)
    if key in seen or operation_id in seen.values():
        raise ValueError("Duplicate HTTP operation mapping")
    seen[key] = operation_id
    path_fields = set(_path_names(path))
    declared_path_fields = set(operation.get("path_parameters", {}))
    if path_fields != declared_path_fields:
        raise ValueError("Path fields and typed path parameters disagree")
    if operation.get("status_code", 200) == 204 and operation.get("response"):
        raise ValueError("HTTP 204 operation cannot declare a response body")
    for name in ("body", "query", "response"):
        value = operation.get(name)
        if value is not None and name in ("body", "query"):
            if not isinstance(value, type) or not issubclass(value, BaseModel):
                raise ValueError("HTTP input must use an explicit Pydantic model")
    if not domain:
        raise ValueError("Domain tag is required")


def declared_schema(health, domains):
    """Build contract-only OpenAPI using FastAPI's own route/schema machinery."""
    app = FastAPI(
        title="CLIP API",
        version=health.CONTRACT_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    async def health_declaration():
        """Refuse invocation: the real health handler is a separate API route."""
        raise NotImplementedError("Contract declaration has no implementation")

    app.get(**health.HEALTH_ROUTE)(health_declaration)
    shared_types = importlib.import_module("contracts.source.types")
    seen = {("GET", health.HEALTH_ROUTE["path"]): health.HEALTH_ROUTE["operation_id"]}
    for domain, module in domains.items():
        for operation in module.HTTP_OPERATIONS:
            _validate_operation(domain, operation, seen)
            responses = {
                status: {"model": shared_types.ErrorEnvelope}
                for status in ERROR_STATUSES
            }
            for status, response in operation.get("responses", {}).items():
                responses[status] = {"model": response} if response is not None else {}
            status_code = operation.get("status_code", 200)
            route_options = {}
            if status_code == 204:
                route_options["response_class"] = Response
            app.add_api_route(
                operation["path"],
                _endpoint(operation),
                methods=[operation["method"]],
                name=operation["operation_id"],
                operation_id=operation["operation_id"],
                tags=[domain],
                summary=operation.get("summary", operation["operation_id"]),
                response_model=operation.get("response"),
                status_code=status_code,
                responses=responses,
                **route_options,
            )
    schema = app.openapi()
    schema["x-clip-generator-format"] = FORMAT_VERSION
    return schema


def local_tool():
    """Require exact locally installed Node generator/compiler pins."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node 24 is required; follow the recorded toolchain setup")
    version = subprocess.run(
        [node, "--version"], capture_output=True, text=True, timeout=10, check=True
    ).stdout.strip()
    if not version.startswith("v24."):
        raise RuntimeError("Node 24 is required")
    manifest = json.loads((ROOT / "package.json").read_text())
    lock = json.loads((ROOT / "package-lock.json").read_text())
    for package, expected in (
        (TS_PACKAGE, TS_VERSION),
        ("typescript", COMPILER_VERSION),
    ):
        installed_path = ROOT / "node_modules" / package / "package.json"
        if not installed_path.exists():
            raise RuntimeError("Missing local generation tool; run npm ci")
        installed = json.loads(installed_path.read_text())
        if (
            manifest["devDependencies"].get(package) != expected
            or lock["packages"]["node_modules/" + package]["version"] != expected
            or installed["version"] != expected
        ):
            raise RuntimeError(
                "Generator/compiler pin, lock or install mismatch; run npm ci"
            )
    return node, ROOT / "scripts/generate_types.mjs"


def _generated_python(source, imports):
    """Copy one canonical source while rewriting its type-only package imports."""
    body = source.read_text()
    for old, new in imports.items():
        body = body.replace(old, new)
    if "contracts.source.types" in body:
        raise ValueError("Generated Python may not import editable source")
    return body


def runtime_public(body, domain, bindings):
    """Transform only approved refusing declarations into typed technical dispatch.

    Metadata is code-owned canonical source, never runtime/user configuration.
    Unsupported signatures/results fail generation rather than invent adapters.
    The source stays behavior-free; other providers retain exact refusal bodies.
    """
    if not isinstance(bindings, frozenset):
        raise ValueError("Runtime binding metadata must be an explicit frozen set")
    tree = ast.parse(body)
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
    }
    if not bindings <= functions.keys():
        raise ValueError("Runtime binding names must be declared operations")
    if bindings and not any(
        isinstance(node, ast.ImportFrom)
        and node.module == "app.core.runtime_bindings"
        and any(
            alias.name == "dispatch_runtime" and alias.asname == "_dispatch_runtime"
            for alias in node.names
        )
        for node in tree.body
    ):
        raise ValueError("Runtime adapter requires its reviewed technical import")
    lines = body.splitlines(keepends=True)
    for name in sorted(
        bindings, key=lambda value: functions[value].lineno, reverse=True
    ):
        node = functions[name]
        if (
            len(node.body) != 2
            or not ast.get_docstring(node)
            or not isinstance(node.body[1], ast.Raise)
            or not isinstance(node.body[1].exc, ast.Call)
            or not isinstance(node.body[1].exc.func, ast.Name)
            or node.body[1].exc.func.id != "NotImplementedError"
            or not isinstance(node.returns, ast.Name)
            or node.args.vararg
            or node.args.kwarg
            or node.args.kwonlyargs
            or node.decorator_list
        ):
            raise ValueError("Unsupported runtime declaration adapter")
        arguments = [
            argument.arg for argument in (*node.args.posonlyargs, *node.args.args)
        ]
        forwarded = "".join("        " + argument + ",\n" for argument in arguments)
        replacement = (
            "    return await _dispatch_runtime(\n"
            + f'        "{domain}.{name}",\n'
            + "        "
            + node.returns.id
            + ",\n"
            + forwarded
            + "    )\n"
        )
        refusal = node.body[1]
        lines[refusal.lineno - 1 : refusal.end_lineno] = [replacement]
    return "".join(lines)


def render(work):
    """Render every output in temporary space before the caller writes any file."""
    health, domains = load_sources()
    schema = declared_schema(health, domains)
    node, cli = local_tool()
    schema_path = work / "openapi.json"
    schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    output_directory = work / "types"
    output_path = output_directory / "types.gen.ts"
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(work),
        "NO_COLOR": "1",
        "TZ": "UTC",
    }
    result = subprocess.run(
        [node, str(cli), str(schema_path), str(output_directory)],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        raise RuntimeError(
            "Pinned TypeScript generation failed; inspect source/tool compatibility"
        )
    generated = {
        "apps/api/app/contracts/health.py": (
            f"# Generated from contracts/source/health.py; format {FORMAT_VERSION}. Do not edit.\n"
            + (ROOT / "contracts/source/health.py").read_text()
        ).encode(),
        "apps/api/app/contracts/domain_types.py": (
            f"# Generated from contracts/source/types.py; format {FORMAT_VERSION}. Do not edit.\n"
            + _generated_python(
                ROOT / "contracts/source/types.py",
                {"contracts.source.types": "app.contracts.domain_types"},
            )
        ).encode(),
    }
    for domain in DOMAINS:
        bindings = getattr(domains[domain], "RUNTIME_BINDINGS", frozenset())
        label = "typed runtime" if bindings else "declaration-only"
        public_body = runtime_public(
            _generated_python(
                ROOT / f"contracts/source/{domain}.py",
                {"contracts.source.types": "app.contracts.domain_types"},
            ),
            domain,
            bindings,
        )
        for name in bindings:
            result_type = inspect.signature(
                getattr(domains[domain], name)
            ).return_annotation
            if not inspect.isclass(result_type) or not issubclass(
                result_type, BaseModel
            ):
                raise ValueError("Runtime adapters require a reviewed result model")
        generated[PUBLIC_OUTPUTS[DOMAINS.index(domain)]] = (
            f"# Generated {label} {domain} interface; format {FORMAT_VERSION}. Do not edit.\n"
            + public_body
        ).encode()
    generated["contracts/generated/openapi.json"] = schema_path.read_bytes()
    generated["contracts/generated/types.gen.ts"] = (
        f"// CLIP generator format {FORMAT_VERSION}; source: contracts/source/.\n"
        + output_path.read_text()
    ).encode()
    if set(generated) != set(OUTPUTS):
        raise RuntimeError("Generated output registry mismatch")
    return generated


def main():
    """Generate exact registered files or compare without changing tracked output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "check"))
    mode = parser.parse_args().mode
    try:
        with tempfile.TemporaryDirectory(prefix="clip-contracts-") as directory:
            rendered = render(Path(directory))
            stale = []
            for relative, content in rendered.items():
                destination = ROOT / relative
                if destination.is_symlink():
                    raise RuntimeError(
                        "Generated destinations must not be symbolic links"
                    )
                if mode == "generate":
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(content)
                elif not destination.exists() or destination.read_bytes() != content:
                    stale.append(relative)
            if stale:
                for relative in stale:
                    print(f"Stale or missing: {relative}")
                return 1
    except Exception:
        print(
            "Contract generation failed: check reviewed source, Node 24 and pinned tools; run npm ci after lockfile updates.",
            file=sys.stderr,
        )
        return 1
    print(
        f"Contract {mode}: {len(OUTPUTS)} registered artifacts current (format {FORMAT_VERSION})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
