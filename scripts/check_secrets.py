"""Scan a tracked/nonignored source snapshot with pinned, network-isolated Gitleaks.

Ignored local environments, provider credentials and generated build caches are
never mounted. New untracked source is included; deleted files are omitted.
Only file/line/rule metadata is printed. The explicit project configuration
retains default rules and one exact historical checksum exception.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "ghcr.io/gitleaks/gitleaks:v8.30.1"


def main():
    """Copy source without following symlinks and run the redacted default rules."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    env = {key: os.environ[key] for key in ("HOME", "PATH")}
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=True,
        timeout=30,
    )
    context = subprocess.run(
        ["docker", "context", "show"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout.strip()
    details = subprocess.run(
        ["docker", "context", "inspect", context],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    if not json.loads(details.stdout)[0]["Endpoints"]["docker"]["Host"].startswith(
        "unix://"
    ):
        raise RuntimeError("A local Unix-socket Docker context is required")
    with tempfile.TemporaryDirectory(prefix="clip-secret-scan-") as directory:
        snapshot = Path(directory)
        for name in set(result.stdout.decode().split("\0")) - {""}:
            source = ROOT / name
            if source.is_symlink() or any(
                parent.is_symlink() for parent in source.parents
            ):
                raise RuntimeError("Source symlinks require explicit scanner review")
            if source.is_file():
                target = snapshot / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        # Select the reviewed project config; ignore ambient config/inline bypasses.
        shutil.copyfile(ROOT / ".gitleaks.toml", snapshot / ".gitleaks.toml")
        # Only the verified local context; no credential/provider env forwarding.
        result = subprocess.run(
            [
                "docker",
                "--context",
                context,
                "run",
                "--rm",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--mount",
                f"type=bind,src={snapshot},dst=/source,readonly",
                IMAGE,
                "dir",
                "/source",
                "--config",
                "/source/.gitleaks.toml",
                "--no-color",
                "--redact=100",
                "--report-format",
                "json",
                "--report-path",
                "-",
                "--no-banner",
                "--ignore-gitleaks-allow",
                "--gitleaks-ignore-path",
                "/dev/null",
            ],
            capture_output=True,
            text=True,
            cwd=directory,
            env=env,
            timeout=180,
            check=False,
        )
        if result.returncode == 1:
            for finding in json.loads(result.stdout):
                print(
                    f"Secret finding: {finding['File']}:{finding['StartLine']} ({finding['RuleID']})"
                )
        if result.returncode:
            raise RuntimeError(
                "Secret scan failed; resolve redacted findings or tool failure"
            )
        print("PASS: Gitleaks 8.30.1 source snapshot (not Git history)")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError, OSError, subprocess.SubprocessError, ValueError:
        import sys

        print(
            "Secret scan failed; inspect redacted scanner diagnostics.", file=sys.stderr
        )
        raise SystemExit(1)
