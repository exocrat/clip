"""Install one checksum-pinned official k6 binary inside this repository only.

No shell, package manager, global link, PATH edit or privileged installation.
Inspect Mach-O minimum OS before executing; refuse incompatible hosts/artifacts.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
VERSION = "2.3.0"
ARCHIVE = "k6-v2.3.0-macos-arm64.zip"
SHA256 = "b2417a3038edc5fe81dc178a889237724b595c5c9cfed875822008e46e862c7d"
CHECKSUM_SHA256 = "8ebbfcd5a13d68ac67d488c2b5f28bf901ea22d2fbbfb15f5345d65c39163be2"
BASE = f"https://github.com/grafana/k6/releases/download/v{VERSION}"
TOOL_DIR = ROOT / ".tools/k6"
BINARY = TOOL_DIR / f"v{VERSION}/k6"


def minimum_macos(content: bytes) -> tuple[int, int, int]:
    """Read ARM64 Mach-O build minimum without executing downloaded code."""
    magic, cpu, _, _, count, _, _, _ = struct.unpack_from("<8I", content)
    if magic != 0xFEEDFACF or cpu != 0x0100000C:
        raise ValueError("Expected ARM64 Mach-O")
    offset = 32
    for _ in range(count):
        command, size = struct.unpack_from("<2I", content, offset)
        if size < 8 or offset + size > len(content):
            raise ValueError("Invalid Mach-O command")
        if command == 0x32:
            target, minimum = struct.unpack_from("<2I", content, offset + 8)
            if target != 1:
                raise ValueError("Expected macOS target")
            return minimum >> 16, (minimum >> 8) & 255, minimum & 255
        if command == 0x24:
            minimum = struct.unpack_from("<I", content, offset + 8)[0]
            return minimum >> 16, (minimum >> 8) & 255, minimum & 255
        offset += size
    raise ValueError("Missing minimum OS metadata")


def download(name: str, digest: str, maximum: int) -> Path:
    """Fetch fixed official artifact to ignored local cache; never replace mismatches."""
    target = TOOL_DIR / name
    if not target.exists():
        request = urllib.request.Request(
            f"{BASE}/{name}", headers={"User-Agent": "clip-se01-pinned-k6"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(maximum + 1)
        if len(data) > maximum or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("Artifact size/checksum mismatch")
        target.write_bytes(data)
    if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise ValueError("Cached artifact mismatch")
    return target


def main() -> None:
    """Verify official checksums, native minimum OS, local destination and version."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("This pinned install target is macOS ARM64 only")
    if TOOL_DIR.is_symlink() or (ROOT / ".tools").is_symlink():
        raise ValueError("Local tool paths must not be symlinks")
    TOOL_DIR.mkdir(parents=True, exist_ok=True)
    sums = download(f"k6-v{VERSION}-checksums.txt", CHECKSUM_SHA256, 4096)
    lines = [line.split() for line in sums.read_text().splitlines()]
    if [SHA256, ARCHIVE] not in lines:
        raise ValueError("Release checksum binding mismatch")
    archive = download(ARCHIVE, SHA256, 35_000_000)
    with zipfile.ZipFile(archive) as bundle:
        names = [name for name in bundle.namelist() if name.endswith("/k6")]
        if len(names) != 1 or bundle.getinfo(names[0]).file_size > 120_000_000:
            raise ValueError("Unexpected archive binary")
        content = bundle.read(names[0])
    minimum = minimum_macos(content)
    current = tuple(map(int, platform.mac_ver()[0].split(".")))
    if current < minimum:
        raise ValueError("Pinned k6 is incompatible with this macOS")
    BINARY.parent.mkdir(exist_ok=True)
    if BINARY.parent.is_symlink() or BINARY.is_symlink():
        raise ValueError("Local binary path must not be a symlink")
    if BINARY.exists() and BINARY.read_bytes() != content:
        raise ValueError("Existing binary mismatch")
    BINARY.write_bytes(content)
    BINARY.chmod(0o700)
    version = subprocess.check_output(
        [str(BINARY), "version"], env={"PATH": "/usr/bin:/bin"}, text=True, timeout=5
    ).strip()
    if not version.startswith(f"k6 v{VERSION} "):
        raise ValueError("Installed version mismatch")
    report = {
        "version": VERSION,
        "archive_sha256": SHA256,
        "binary_sha256": hashlib.sha256(content).hexdigest(),
        "minimum_macos": minimum,
        "host_macos": current,
        "version_output": version,
        "binary": str(BINARY.relative_to(ROOT)),
        "source": f"{BASE}/{ARCHIVE}",
    }
    (TOOL_DIR / "install.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
