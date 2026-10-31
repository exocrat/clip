"""Freeze/verify NEXT-06 inputs and actual evidence; no cloud, inference or reset.

This release records immutable data/label/source/model/index bindings and their
provenance. Content freeze is separate from human/peer/CI DATA-READY acceptance.
Never overwrite a release or silently rewrite labels after seeing measurements.
"""

import argparse
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

from data.generators import reference, files
from data.generators.manifest import canonical_json
from data.generators.reference_cloud import CloudTarget
from scripts.evaluation import reference_labels as labels
from scripts.evaluation.search import validate_labels

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = "docs/evaluation/domain/next-06/frozen-dataset.json"
INDEX = "data/transfer/next06-reference-20261030.json"
EVIDENCE = "docs/evaluation/domain/next-06/transfer"
IMAGE_ROOT = Path("/Users/mohitmahapatra/Desktop/clip-dataset-images")


def require(value, code):
    """Emit fixed safe diagnostics rather than rows, credentials or exceptions."""
    if not value:
        raise ValueError(code)


def sha(path):
    """Hash an exact local artifact, with no network or content output."""
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def verify_archive(index, archive):
    """Check all52ordinary unique members against the published transfer index.

    Read bounded member bodies without extracting or executing anything. Reject
    traversal/links/duplicates/changed bytes; original photos are never modified.
    """
    require(
        archive.stat().st_size == index["archive_bytes"]
        and hashlib.sha256(archive.read_bytes()).hexdigest() == index["archive_sha256"],
        "archive_bytes_changed",
    )
    expected = {r["path"]: r for r in index["files"]}
    require(len(expected) == len(index["files"]) == 52, "archive_member_count_changed")
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        require(
            len(members) == 52 and {m.name for m in members} == set(expected),
            "archive_member_scope_changed",
        )
        for member in members:
            name = PurePosixPath(member.name)
            require(
                member.isfile() and not name.is_absolute() and ".." not in name.parts,
                "unsafe_archive_member",
            )
            record = expected[member.name]
            require(member.size == record["bytes"], "archive_member_size_changed")
            with source.extractfile(member) as stream:
                content = stream.read(member.size + 1)
            require(
                len(content) == member.size
                and hashlib.sha256(content).hexdigest() == record["sha256"],
                "archive_member_hash_changed",
            )
    require(
        sum(name.startswith("images/") for name in expected) == 45,
        "archive_photo_count_changed",
    )
    return {
        "archive": "data/transfer/" + index["archive"],
        "bytes": index["archive_bytes"],
        "sha256": index["archive_sha256"],
        "members_verified": 52,
        "source_photos": 45,
    }


def verify_ledger(rows, bundle, target):
    """Reconcile actual create-only upload receipts with all1000approved keys.

    This verifies retained write/GET evidence, not a new S3 inventory. Never
    upload, retry or delete anything from an already populated target.
    """
    require(
        Counter(r["state"] for r in rows)
        == {
            "target_checked": 1,
            "put_planned": 1000,
            "bytes_verified": 1000,
            "sql_planned": 1,
            "sql_committed": 1,
        },
        "actual_load_ledger_states_changed",
    )
    header = next(r for r in rows if r["state"] == "target_checked")
    require(
        (header["account"], header["bucket"], header["prefix"])
        == (target.account, target.bucket, target.prefix),
        "ledger_target_changed",
    )
    expected = {
        target.object_key_for(row["upload_id"]): row["sha256"]
        for row in bundle["image_plan"]
    }
    for stage in ("put_planned", "bytes_verified"):
        selected = [r for r in rows if r["state"] == stage]
        require(
            len({r["key"] for r in selected}) == 1000
            and {r["key"]: r["sha256"] for r in selected} == expected,
            "ledger_image_mapping_changed",
        )
    require(
        next(r for r in rows if r["state"] == "sql_committed")["fingerprint"]
        == bundle["manifest"]["logical_data_fingerprint"],
        "ledger_committed_corpus_changed",
    )
    return {
        "objects_verified": 1000,
        "sql_commits_verified": 1,
        "logical_object_bytes": sum(r["size_bytes"] for r in bundle["image_plan"]),
    }


def materialize(image_root=IMAGE_ROOT, model_root=ROOT / ".tools/semantic/model"):
    """Build a deterministic release from independently verified real inputs.

    Generator manifests keep truthful generated-only flags; actual cloud/native
    execution and human-reported workflow evidence remain separate inputs. A/B
    source records and52member archive are checked, without another rebuild.
    """
    expected_labels, label_manifest, binding = labels.materialize(image_root)
    actual_labels = files._read_json(ROOT / labels.LABELS)
    require(
        canonical_json(actual_labels) == canonical_json(expected_labels),
        "reviewed_labels_changed",
    )
    require(
        canonical_json(files._read_json(ROOT / labels.MANIFEST))
        == canonical_json(label_manifest),
        "actual_label_binding_changed",
    )
    cases = validate_labels(actual_labels, binding)
    bundles = [
        files._read_json(
            ROOT / f"data/runs/next06-transfer-42-20261030-{suffix}/dataset.json"
        )
        for suffix in ("a", "b")
    ]
    for bundle in bundles:
        reference.validate_reference(bundle, image_root=image_root)
        require(
            bundle["manifest"]["logical_data_fingerprint"]
            == binding.logical_data_fingerprint,
            "repeated_generation_fingerprint_changed",
        )
    require(
        all(
            canonical_json(bundles[0][key]) == canonical_json(bundles[1][key])
            for key in ("users", "listings", "image_plan")
        ),
        "repeated_generation_records_changed",
    )
    index = files._read_json(ROOT / INDEX)
    require(
        hashlib.sha256(
            labels.revision_bytes(binding.source_revision, INDEX)
        ).hexdigest()
        == sha(INDEX),
        "published_transfer_index_changed",
    )
    archive = verify_archive(index, ROOT / "data/transfer" / index["archive"])
    target_path = EVIDENCE + "/cloud-load-20261031/approved-target.json"
    target = CloudTarget(**files._read_json(ROOT / target_path))
    ledger_path = EVIDENCE + "/cloud-load-20261031/object-load-ledger.jsonl"
    ledger = verify_ledger(
        [json.loads(row) for row in (ROOT / ledger_path).read_text().splitlines()],
        bundles[0],
        target,
    )
    native_path = EVIDENCE + "/dataset-current-native-rebuild.json"
    snapshot_path = EVIDENCE + "/dataset-snapshot-20261031/result.json"
    native = files._read_json(ROOT / native_path)
    snapshot = files._read_json(ROOT / snapshot_path)
    require(
        native["cluster_stopped"] is True
        and all(
            native["reset_reload"][key] is True
            for key in (
                "same_owned_target",
                "fresh_schema_reloaded",
                "logical_records_media_identical",
                "readonly_snapshot_reader_identical",
                "vectors_indexes_identical",
            )
        ),
        "real_reset_reload_proof_incomplete",
    )
    model_path = "scripts/evaluation/semantic/model-manifest.json"
    model = files._read_json(ROOT / model_path)
    for entry in model["files"]:
        file = model_root / entry["filename"]
        require(
            file.stat().st_size == entry["bytes"]
            and hashlib.sha256(file.read_bytes()).hexdigest() == entry["sha256"],
            "pinned_model_artifact_changed",
        )
    paths = [
        labels.LABELS,
        labels.MANIFEST,
        labels.RUN + "/manifest.json",
        labels.RUN + "/dataset.json",
        "data/runs/next06-transfer-42-20261030-b/manifest.json",
        "data/runs/next06-transfer-42-20261030-b/dataset.json",
        INDEX,
        archive["archive"],
        ledger_path,
        target_path,
        native_path,
        snapshot_path,
        model_path,
        EVIDENCE + "/vector-production-20261031/result.json",
        EVIDENCE + "/step-03-human-reported-completion.json",
        EVIDENCE + "/step-05-label-binding-decisions.json",
        "scripts/evaluation/reference_labels.py",
        "scripts/evaluation/reference_release.py",
        "scripts/evaluation/search.py",
    ]
    manifest = bundles[0]["manifest"]
    return {
        "format_version": "1",
        "task": "NEXT-06",
        "release_status": "frozen_inputs_verified_acceptance_pending",
        "final_freeze": True,
        "data_ready": False,
        "source_revision": binding.source_revision,
        "search_contract_revision": binding.search_contract_revision,
        "logical_data_fingerprint": binding.logical_data_fingerprint,
        "schema_version": binding.schema_version,
        "seed": manifest["seed"],
        "generator_version": manifest["generator_version"],
        "measurement_window": manifest["measurement_window"],
        "distribution_counts": manifest["observed_counts"],
        "cloud_target": {
            k: getattr(target, k)
            for k in ("account", "region", "database", "bucket", "prefix")
        },
        "image_state": ledger,
        "transfer": archive,
        "model": model,
        "pipeline": label_manifest["pipeline"],
        "vector_index_snapshot": label_manifest["vector_index_snapshot"],
        "labels": {
            "path": labels.LABELS,
            "sha256": sha(labels.LABELS),
            "queries": len(cases),
            "included": sum(case.included for case in cases),
            "review": actual_labels["review"],
        },
        "reproducibility": {
            "both_generated_record_sets_identical": True,
            "real_isolated_reset_reload": True,
            "cloud_native_vectors_indexes_match": True,
        },
        "normal_workflow_provenance": "Completed by another executor per explicit Mohit report; not proven by our incomplete local attempt",
        "last_cloud_snapshot_ended_utc": snapshot["ended_utc"],
        "fresh_cloud_state_claimed": False,
        "scoring_executed": False,
        "inputs": [{"path": path, "sha256": sha(path)} for path in paths],
        "acceptance_pending": [
            "Human Step6 verification",
            "Current-head CI and independent human peer review",
            "Explicit merge authorization and recorded accepted revision",
        ],
        "retention": "Keep reference objects/data; no new uploads/reset/cloud policy changes. Recheck dataset/window before measurements. New source/schema/model/data/labels require reviewed revalidation/versioning.",
    }


def main(argv=None):
    """Create the fixed immutable release once or revalidate it without mutation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "validate"))
    parser.add_argument("--image-root", type=Path, default=IMAGE_ROOT)
    parser.add_argument(
        "--model-root", type=Path, default=ROOT / ".tools/semantic/model"
    )
    args = parser.parse_args(argv)
    try:
        expected = materialize(args.image_root, args.model_root)
        output = ROOT / OUTPUT
        if args.action == "freeze":
            document = {
                **expected,
                "frozen_recorded_at": datetime.now(UTC)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            }
            with output.open("x") as stream:
                stream.write(json.dumps(document, indent=2) + "\n")
        else:
            document = files._read_json(output)
            stamp = document.pop("frozen_recorded_at")
            require(
                stamp.endswith("Z")
                and datetime.fromisoformat(stamp).tzinfo is not None,
                "invalid_freeze_timestamp",
            )
            require(
                canonical_json(document) == canonical_json(expected),
                "frozen_release_inputs_changed",
            )
        print(
            json.dumps(
                {
                    "state": "frozen_release_verified",
                    "manifest": OUTPUT,
                    "logical_data_fingerprint": expected["logical_data_fingerprint"],
                    "archive_members_verified": 52,
                    "queries": 22,
                    "data_ready": False,
                    "scoring_executed": False,
                    "cloud_calls": 0,
                }
            )
        )
        return 0
    except Exception as error:
        result = {"state": "release_refused", "failure_type": type(error).__name__}
        if isinstance(error, ValueError) and str(error).replace("_", "").isalpha():
            result["code"] = str(error)
        print(json.dumps(result))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
