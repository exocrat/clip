"""Generate/check registered declaration artifacts without importing the real API.

Only the reviewed health HTTP mapping is registered in PD-11 step 5. Domain
public declarations are a later DL-00 output. Local Node tooling is required;
there is no network-install fallback or provider/database configuration read.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[1]
FORMAT_VERSION = 1
TS_VERSION = "0.99.0"
COMPILER_VERSION = "5.9.3"
TS_PACKAGE = "@hey-api/openapi-ts"
OUTPUTS = (
    "apps/api/app/contracts/health.py",
    "contracts/generated/openapi.json",
    "contracts/generated/types.gen.ts",
)


def health_source():
    """Load reviewed declarations only, never app.main or domain implementations."""
    source = ROOT / "contracts/source/health.py"
    spec = importlib.util.spec_from_file_location("clip_health_source", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def declared_schema(declaration):
    """Build schema from explicit HTTP metadata on an unserved contract-only app."""
    app = FastAPI(
        title="CLIP API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    async def declaration_only():
        """Reject accidental invocation: this is a schema declaration, not health."""
        raise RuntimeError("Contract declaration has no implementation")

    app.get(**declaration.HEALTH_ROUTE)(declaration_only)
    schema = app.openapi()
    schema["x-clip-generator-format"] = FORMAT_VERSION
    return schema


def local_tool():
    """Require the selected Node line and exact declared, locked, installed tool."""
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


def render(work):
    """Render all registered artifacts in temporary storage before writing any."""
    declaration = health_source()
    schema = declared_schema(declaration)
    node, cli = local_tool()
    schema_path = work / "openapi.json"
    schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    output_directory = work / "types"
    output_path = output_directory / "types.gen.ts"
    # Clean child configuration prevents provider credentials/config inheritance.
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
    header = f"# Generated from contracts/source/health.py; format {FORMAT_VERSION}. Do not edit.\n"
    python = header + (ROOT / "contracts/source/health.py").read_text()
    types = (
        f"// CLIP generator format {FORMAT_VERSION}; source: contracts/source/.\n"
        + output_path.read_text()
    )
    return dict(
        zip(
            OUTPUTS,
            (python.encode(), schema_path.read_bytes(), types.encode()),
            strict=True,
        )
    )


def main():
    """Generate exact registered files, or compare without changing tracked output."""
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
    except OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError:
        # No schema, source values or inherited configuration in diagnostics.
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
