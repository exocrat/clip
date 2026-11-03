"""Build a pinned k6 binary with the repository's monotonic elapsed timer.

The ordinary official k6 installer remains available for scenarios that do not
need this extension. Comparison and NFR workloads must use this custom binary;
its build metadata records the exact k6, xk6, Go and extension revisions.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
EXTENSION = ROOT / "scripts/evaluation/k6/monotonic"
K6_VERSION = "2.3.0"
XK6_VERSION = "v1.4.14"
MIN_GO = (1, 26, 0)
TOOL_ROOT = ROOT / ".tools/k6"
INSTALL_DIR = TOOL_ROOT / f"v{K6_VERSION}-monotonic"
BINARY = INSTALL_DIR / "k6"
MODULE = "clip.local/evaluation/monotonic"


def _extension_digest() -> str:
    """Bind the build record to every checked-in timer source/manifest byte."""
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in EXTENSION.iterdir()
        if path.is_file() and path.name not in {"go.sum"}
    )
    if not {"go.mod", "module.go", "timer.go"}.issubset({path.name for path in files}):
        raise ValueError("monotonic_extension_incomplete")
    for path in files:
        if path.is_symlink():
            raise ValueError("monotonic_extension_symlink")
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    sums = EXTENSION / "go.sum"
    if sums.is_file():
        digest.update(b"go.sum\0" + sums.read_bytes())
    return digest.hexdigest()


def _safe_env() -> dict[str, str]:
    """Pass only build-tool paths/cache settings, not cloud or app credentials."""
    env = {
        key: os.environ[key]
        for key in ("PATH", "HOME", "GOPROXY", "GOSUMDB", "GOCACHE", "GOMODCACHE")
        if key in os.environ
    }
    env.setdefault("PATH", "/usr/bin:/bin")
    env["GOTOOLCHAIN"] = "local"
    env["CGO_ENABLED"] = "0"
    return env


def _go_version(go: str, env: dict[str, str]) -> tuple[str, tuple[int, int, int]]:
    result = subprocess.run(
        [go, "version"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    match = re.fullmatch(r"go version go(\d+)\.(\d+)(?:\.(\d+))? \S+\n?", result.stdout)
    if result.returncode != 0 or match is None:
        raise ValueError("go_version_unavailable")
    version = (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3) or 0),
    )
    if version < MIN_GO:
        raise ValueError("go_version_too_old")
    return result.stdout.strip(), version


def _target() -> tuple[str, str]:
    """Support the repository's Linux x86-64 runner and macOS ARM64 workstation."""
    current = (platform.system(), platform.machine())
    supported = {
        ("Linux", "x86_64"): ("linux", "amd64"),
        ("Darwin", "arm64"): ("darwin", "arm64"),
    }
    if current not in supported:
        raise ValueError("unsupported_k6_build_host")
    return supported[current]


def install() -> dict[str, str]:
    """Build once to a private temporary path, then publish the verified binary."""
    go = shutil.which("go")
    if go is None:
        raise ValueError("go_toolchain_required")
    env = _safe_env()
    go_output, _ = _go_version(go, env)
    os_name, arch = _target()
    if TOOL_ROOT.is_symlink() or INSTALL_DIR.is_symlink() or BINARY.is_symlink():
        raise ValueError("k6_install_path_symlink")
    TOOL_ROOT.mkdir(parents=True, exist_ok=True)
    INSTALL_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    if BINARY.exists():
        raise ValueError("monotonic_k6_already_installed")

    with tempfile.TemporaryDirectory(prefix="clip-xk6-build-", dir=TOOL_ROOT) as tmp:
        output = Path(tmp) / "k6"
        command = [
            go,
            "run",
            f"go.k6.io/xk6/cmd/xk6@{XK6_VERSION}",
            "build",
            f"v{K6_VERSION}",
            "--with",
            f"{MODULE}={EXTENSION}",
            "--output",
            str(output),
            "--os",
            os_name,
            "--arch",
            arch,
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            timeout=1800,
            check=False,
        )
        if result.returncode != 0 or not output.is_file() or output.is_symlink():
            raise ValueError("monotonic_k6_build_failed")
        content = output.read_bytes()
        if not content or len(content) > 250_000_000:
            raise ValueError("monotonic_k6_binary_size_invalid")
        version_result = subprocess.run(
            [str(output), "version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if version_result.returncode != 0 or not version_result.stdout.startswith(
            f"k6 v{K6_VERSION} "
        ):
            raise ValueError("monotonic_k6_version_mismatch")
        BINARY.write_bytes(content)
        BINARY.chmod(0o700)

    record = {
        "k6_version": K6_VERSION,
        "xk6_version": XK6_VERSION,
        "go_version": go_output,
        "goos": os_name,
        "goarch": arch,
        "extension_sha256": _extension_digest(),
        "binary_sha256": hashlib.sha256(BINARY.read_bytes()).hexdigest(),
        "binary": str(BINARY.relative_to(ROOT)),
        "clock": "monotonic-time-time-subtraction",
    }
    metadata = INSTALL_DIR / "build.json"
    with metadata.open("x", encoding="utf-8") as target:
        json.dump(record, target, sort_keys=True, indent=2)
        target.write("\n")
    return record


def main() -> None:
    """Install the custom binary and print only version and fingerprint metadata."""
    try:
        print(json.dumps(install(), sort_keys=True))
    except OSError, ValueError, subprocess.TimeoutExpired:
        raise SystemExit("Monotonic k6 build refused or failed; no workload was run")


if __name__ == "__main__":
    main()
