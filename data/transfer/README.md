# NEXT-06 complete transfer bundle

`next06-reference-20261030.tar.gz` is deliberately tracked under Mohit's explicit
instruction to include the images and everything needed by the cloud operator.
It contains45approved original photo copies (unchanged), both synthetic dataset/
manifest pairs, approved recipe/inventory and the22accepted judgments. No local
credentials, sessions, private keys, toolchains or database directories are included.
Original photos stay unchanged in Mohit's external folder. Earlier outside-Git
photo guidance has this explicit one-archive transfer exception.

Archive size: 42463902 bytes (about42.5MB).
SHA256: `2c9c88d103f3329c794c1efa857268a7120c7f1549250d3e28278d5e1eb0b2ea`.
`next06-reference-20261030.json` lists all52member hashes/sizes.

## Restore into a fresh directory and install the ignored payloads

From the root of a full Git clone of this PR's reviewed branch, using its
repository-local Python3.14 (no AWS operation):

```sh
.venv/bin/python - <<'PY'
from pathlib import Path
import hashlib, json, tarfile
root = Path.cwd()
folder = root / "data/transfer"
info = json.loads((folder / "next06-reference-20261030.json").read_text())
archive = folder / info["archive"]
assert hashlib.sha256(archive.read_bytes()).hexdigest() == info["archive_sha256"]
destination = root / "data-transfer-next06"
destination.mkdir(mode=0o700, exist_ok=False)
with tarfile.open(archive) as tar:
    members = tar.getmembers()
    assert {m.name for m in members} == {f["path"] for f in info["files"]}
    assert all(m.isfile() for m in members)
    tar.extractall(destination, filter="data")
for item in info["files"]:
    content = (destination / item["path"]).read_bytes()
    assert len(content) == item["bytes"]
    assert hashlib.sha256(content).hexdigest() == item["sha256"]
for suffix in ("a", "b"):
    relative = Path(f"data/runs/next06-transfer-42-20261030-{suffix}/dataset.json")
    content = (destination / relative).read_bytes()
    target = root / relative
    if target.exists():
        assert target.read_bytes() == content, "Existing payload differs; do not overwrite"
    else:
        with target.open("xb") as stream:
            stream.write(content)
print("Verified52members and installed both ignored payloads; images at", destination / "images")
PY
.venv/bin/python -m data.generators.reference validate --name next06-transfer-42-20261030-a --image-root "$PWD/data-transfer-next06/images"
.venv/bin/python -m data.generators.reference validate --name next06-transfer-42-20261030-b --image-root "$PWD/data-transfer-next06/images"
```

Use a fresh extraction directory; never overwrite an earlier transfer. The raw
payload ignore rule remains unchanged; manifests are directly tracked.
Source-only rebinding for publication-safe ancestor validation preserves every
user/listing/image-plan record and accepted query ID/context/relevant ID set.
The new fingerprint is `sha256:7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98`.
Validator still rejects changed source/schema/config/photos and unknown ancestry.
A full clone with the recorded base commit is needed; a source ZIP without Git
history is not the supported validation environment.

Continue with the [cloud handoff](../../docs/evaluation/domain/next-06/cloud-handoff.md)
and [review package](../../docs/evaluation/domain/next-06/pre-cloud-review.md).
Only account335523638354 is permitted. This bundle does not authorize deployment
or accept real Identity/S3/IAM/worker/source-contract/final-freeze gates. Both
matched measurements must finish before2026-12-01T00:00Z. Source changes require
review/revalidation; don't relabel queries to improve scores.

The archive remains byte-for-byte unchanged after final label/freeze preparation. Current Git now additionally supplies canonical `data/evaluation/query-labels.json`, `docs/evaluation/domain/next-06/frozen-dataset.json` and the release/label verification tools; use them together with this archive. Source/model/index/label bindings and exact remaining acceptance gates are in the [task-wide review](../../docs/evaluation/domain/next-06/task-wide-review.md). No new image download/upload or cloud reset is required merely to verify the retained release.
