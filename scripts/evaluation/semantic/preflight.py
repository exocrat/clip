"""Resolve artifact sizes/tags/licenses/advisories before an isolated probe install.

Reads official public metadata only, never credentials or model weights. Requires
an already hash-pinned helper requirements file and writes only the fixed local
preflight manifest. No public API/runtime imports this tool.
"""

import hashlib
import json
from pathlib import Path
import re
import urllib.request

from packaging.tags import compatible_tags, cpython_tags, mac_platforms
from packaging.utils import parse_wheel_filename

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / ".tools/semantic"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_FILES = (
    "onnx/model.onnx",
    "tokenizer.json",
    "tokenizer_config.json",
    "config.json",
    "1_Pooling/config.json",
    "sentence_bert_config.json",
    "README.md",
)


def metadata(url):
    """Read bounded official JSON; failed/incomplete metadata blocks preparation."""
    with urllib.request.urlopen(url, timeout=20) as response:
        payload = response.read(8 * 1024 * 1024 + 1)
    if len(payload) > 8 * 1024 * 1024:
        raise ValueError("Metadata exceeds bound")
    return json.loads(payload)


def main():
    """Select compatible Mac wheels and refuse advisories/unknown hashes/size overflow."""
    lock = LOCAL / "resolved-mac.txt"
    content = lock.read_text()
    packages = re.findall(r"^([a-zA-Z0-9_.-]+)==([^\s]+)", content, flags=re.M)
    if not packages:
        raise ValueError("No pinned packages")
    platforms = list(mac_platforms(version=(13, 0), arch="arm64"))
    tags = list(cpython_tags((3, 13), platforms=platforms))
    tags.extend(compatible_tags((3, 13), interpreter="cp313", platforms=platforms))
    priority = {tag: index for index, tag in enumerate(tags)}
    artifacts = []
    for name, version in packages:
        data = metadata(f"https://pypi.org/pypi/{name}/{version}/json")
        if data.get("vulnerabilities"):
            raise ValueError("Package advisories require review: " + name)
        choices = []
        for file in data["urls"]:
            if file.get("yanked") or not file["filename"].endswith(".whl"):
                continue
            wheel_tags = parse_wheel_filename(file["filename"])[3]
            compatible = [priority[tag] for tag in wheel_tags if tag in priority]
            if compatible:
                choices.append((min(compatible), file))
        if not choices:
            raise ValueError("No compatible binary wheel: " + name)
        file = min(choices, key=lambda item: item[0])[1]
        digest = file["digests"]["sha256"]
        if digest not in content or not file["url"].startswith(
            "https://files.pythonhosted.org/"
        ):
            raise ValueError("Wheel not bound to lock/official artifact host")
        info = data["info"]
        artifacts.append(
            {
                "kind": "wheel",
                "package": name,
                "version": version,
                "filename": file["filename"],
                "url": file["url"],
                "bytes": file["size"],
                "sha256": digest,
                "license_expression": info.get("license_expression"),
                "license_classifiers": [
                    value
                    for value in info.get("classifiers", [])
                    if value.startswith("License ::")
                ],
                "pypi_advisories": [],
            }
        )
    model = metadata(
        f"https://huggingface.co/api/models/{MODEL}/revision/{REVISION}?blobs=true"
    )
    if (
        model["sha"] != REVISION
        or model.get("cardData", {}).get("license") != "apache-2.0"
    ):
        raise ValueError("Model pin/license mismatch")
    siblings = {file["rfilename"]: file for file in model["siblings"]}
    for name in MODEL_FILES:
        file = siblings[name]
        artifacts.append(
            {
                "kind": "model",
                "filename": name,
                "bytes": file["size"],
                "url": f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}",
                "sha256": file.get("lfs", {}).get("sha256"),
                "git_blob": file["blobId"],
            }
        )
    # uv's selected managed interpreter archive, not a global OS installer.
    release = metadata(
        "https://api.github.com/repos/astral-sh/python-build-standalone/releases/tags/20260211"
    )
    archive_name = (
        "cpython-3.13.12+20260211-aarch64-apple-darwin-install_only_stripped.tar.gz"
    )
    archive = next(file for file in release["assets"] if file["name"] == archive_name)
    total = sum(file["bytes"] for file in artifacts) + archive["size"]
    if total > 300 * 1024 * 1024:
        raise ValueError("Download budget exceeded")
    manifest = {
        "status": "preflight_only",
        "runtime_verified": False,
        "target": "CPython 3.13 macOS 13 ARM64",
        "model_revision": REVISION,
        "requirements_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
        "artifacts": artifacts,
        "interpreter_archive_bytes": archive["size"],
        "interpreter_archive_url": archive["browser_download_url"],
        "projected_artifact_bytes": total,
        "security_limit": "PyPI reported advisories checked; not a comprehensive security audit",
    }
    (LOCAL / "preflight.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "wheels": len(packages),
                "projected_artifact_bytes": total,
                "model_bytes": siblings["onnx/model.onnx"]["size"],
                "runtime_verified": False,
            }
        )
    )


if __name__ == "__main__":
    main()
