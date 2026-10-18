"""Verify the deliberately simple CI workflow calls the shared check sequence.

This is a command-parity guard, not a general YAML/security validator. It accepts
only the existing single-line run fields and the three reviewed setup commands;
new shell blocks or command forms require explicit review and a guard update.
"""

from pathlib import Path
import re

from check import CHECKS

ROOT = Path(__file__).resolve().parents[1]
SETUP = [
    "test \"$(npm --version)\" = '11.19.1'",
    "uv sync --locked --python 3.14.3",
    "npm ci",
]


def verify(root):
    """Compare every run field with setup plus each shared check in exact order."""
    source = (root / ".github/workflows/ci.yml").read_text()
    fields = [
        line for line in source.splitlines() if re.match(r"\s*(?:-\s*)?run\s*:", line)
    ]
    commands = []
    for line in fields:
        match = re.fullmatch(r"        run: (.+)", line)
        if not match:
            raise ValueError("CI run fields must retain reviewed single-line form")
        commands.append(match[1])
    expected = SETUP + [
        f"uv run --locked python scripts/check.py {name}" for name in CHECKS
    ]
    if commands != expected:
        raise ValueError(
            "CI commands differ from shared check order; update workflow/runner together"
        )
    if CHECKS["web"] != ("npm", "run", "check"):
        raise ValueError("The registered npm run check must remain the web gate")
    makefile = (root / "Makefile").read_text()
    if not re.search(
        r"^check:\n\tuv run --locked python scripts/check\.py\n", makefile, re.MULTILINE
    ):
        raise ValueError("make check must call the complete shared runner")


def main():
    """Report command drift without executing workflow or application commands."""
    try:
        verify(ROOT)
    except (OSError, ValueError) as error:
        print(f"CI parity failed: {error}")
        return 1
    print(
        f"PASS: make check and CI share {len(CHECKS)} ordered checks, including npm run check"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
