"""Fetch preflight-bound wheels/model files locally with size and content checks.

No package is installed and no downloaded code is executed. Existing valid files
are reused; mismatches fail closed. Inputs/outputs are fixed to this probe tree.
"""

import hashlib
import json
from pathlib import Path
import time
import urllib.request

if __package__:
    from .preflight import LOCAL, MODEL, MODEL_FILES, REVISION
else:
    from preflight import LOCAL, MODEL, MODEL_FILES, REVISION


def checked_digest(path, artifact):
    """Check exact size and upstream SHA-256 or Git blob identity of a local file."""
    content = path.read_bytes()
    if len(content) != artifact["bytes"]:
        raise ValueError("Artifact size mismatch")
    sha256 = hashlib.sha256(content).hexdigest()
    expected = artifact.get("sha256")
    if expected:
        if sha256 != expected:
            raise ValueError("Artifact SHA-256 mismatch")
    elif (
        hashlib.sha1(
            b"blob " + str(len(content)).encode() + b"\0" + content
        ).hexdigest()
        != artifact["git_blob"]
    ):
        raise ValueError("Pinned model metadata identity mismatch")
    return sha256


def main():
    """Download only pinned official artifacts, bounded by metadata and elapsed time."""
    manifest = json.loads((LOCAL / "preflight.json").read_text())
    if (
        manifest["model_revision"] != REVISION
        or manifest["projected_artifact_bytes"] > 300 * 1024 * 1024
    ):
        raise ValueError("Preflight binding/budget mismatch")
    lock_hash = hashlib.sha256((LOCAL / "resolved-mac.txt").read_bytes()).hexdigest()
    if lock_hash != manifest["requirements_sha256"]:
        raise ValueError("Requirements changed since preflight")
    started = time.monotonic()
    retained = []
    for artifact in manifest["artifacts"]:
        name = artifact["filename"]
        if artifact["kind"] == "wheel":
            if (
                Path(name).name != name
                or not name.endswith(".whl")
                or not artifact["url"].startswith("https://files.pythonhosted.org/")
            ):
                raise ValueError("Unsafe wheel reference")
            path = LOCAL / "wheels" / name
        else:
            expected_url = f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}"
            if name not in MODEL_FILES or artifact["url"] != expected_url:
                raise ValueError("Unsafe model reference")
            path = LOCAL / "model" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            partial = path.with_name(path.name + ".partial")
            size = 0
            with (
                urllib.request.urlopen(artifact["url"], timeout=20) as response,
                partial.open("xb") as output,
            ):
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > artifact["bytes"] or time.monotonic() - started > 600:
                        raise ValueError("Artifact download/time budget exceeded")
                    output.write(chunk)
            checked_digest(partial, artifact)
            partial.rename(path)
        digest = checked_digest(path, artifact)
        retained.append(
            {
                "filename": name,
                "kind": artifact["kind"],
                "bytes": artifact["bytes"],
                "sha256": digest,
            }
        )
    (LOCAL / "artifacts.json").write_text(
        json.dumps({"model_revision": REVISION, "artifacts": retained}, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "verified_artifacts": len(retained),
                "verified_bytes": sum(file["bytes"] for file in retained),
            }
        )
    )


if __name__ == "__main__":
    main()
