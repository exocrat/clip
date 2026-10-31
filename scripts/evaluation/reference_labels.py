"""Bind unchanged human judgments to the actual NEXT-06 corpus; no scoring/AWS.

The adapter verifies generator inputs, committed source bytes and independent
retained load/vector/rebuild receipts before constructing DatasetBinding. Label
metadata alone cannot construct a trusted binding. Explicit human timestamp and
source decisions are retained separately; this never invents either approval.
"""

import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from uuid import UUID

from data.generators import reference, files
from data.generators.manifest import canonical_json
from scripts.evaluation.search import DatasetBinding, validate_labels

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = "docs/evaluation/domain/next-06/transfer"
MANIFEST = EVIDENCE + "/final-label-binding.json"
LABELS = "data/evaluation/query-labels.json"
RUN = "data/runs/next06-transfer-42-20261030-a"
CONTEXT = {"sort": "relevance", "search_mode": "hybrid", "page": 1, "page_size": 20}


def require(value, code):
    """Raise only a fixed error code, never source rows or supplied values."""
    if not value:
        raise ValueError(code)


def file_digest(path):
    """Bind exact retained input bytes; never print raw inputs or judgments."""
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def revision_bytes(revision, path):
    """Read a committed producer/contract blob without changing Git or the tree."""
    require(bool(re.fullmatch(r"[0-9a-f]{40}", revision)), "invalid_source_revision")
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True, check=True
    )
    return result.stdout


def eligible_reference_ids(bundle):
    """Derive actual available regular-owner scope for the whole fixed window.

    This intentionally supports only the already accepted default contexts; do
    not reinterpret labels or guess filter eligibility for a new context.
    """
    window = bundle["manifest"]["measurement_window"]
    start, end = (datetime.fromisoformat(window[key]) for key in ("from", "before"))
    owners = {
        u["id"]
        for u in bundle["users"]
        if u["account_class"] == "regular"
        and u["status"] == "active"
        and u["expires_at"] is None
        and u["handle_ready"] is True
        # activated_at belongs to temporary activation; regular users legally
        # have NULL here. Use their actual creation/class/status instead.
        and datetime.fromisoformat(u["created_at"]) <= start
    }
    eligible = frozenset(
        UUID(row["id"])
        for row in bundle["listings"]
        if row["owner_id"] in owners
        and row["availability"] == "available"
        and datetime.fromisoformat(row["available_from"]) <= start
        and row["available_until"] is not None
        and datetime.fromisoformat(row["available_until"]) >= end
    )
    require(
        len(bundle["users"]) == 5000
        and len(bundle["listings"]) == 1000
        and len(eligible) == 800,
        "reference_counts_or_eligibility_changed",
    )
    return eligible


def materialize(image_root=Path("/Users/mohitmahapatra/Desktop/clip-dataset-images")):
    """Produce deterministic expected label/binding documents from verified inputs.

    Actual cloud receipts remain observations of their recorded windows, not a
    new live inventory. Step3 completion is explicitly human-reported. Step6
    freeze, formal readiness, independent review and NFRscoring stay separate.
    """
    accepted_path = EVIDENCE + "/accepted-judgments.json"
    decisions_path = EVIDENCE + "/step-05-label-binding-decisions.json"
    accepted = files._read_json(ROOT / accepted_path)
    decisions = files._read_json(ROOT / decisions_path)
    require(
        decisions.get("source_binding_accepted") is True
        and decisions.get("use_recorded_acceptance_time") is True,
        "human_label_binding_decisions_required",
    )
    require(
        decisions["reviewer"] == accepted["reviewer"]
        and decisions["reviewed_at"] == accepted["confirmation_recorded_at"],
        "human_review_provenance_changed",
    )
    bundle = files._read_json(ROOT / RUN / "dataset.json")
    reference.validate_reference(bundle, image_root=image_root)
    manifest = bundle["manifest"]
    require(
        canonical_json(manifest)
        == canonical_json(files._read_json(ROOT / RUN / "manifest.json")),
        "paired_input_manifest_differs",
    )
    require(
        accepted["input_fingerprint"] == manifest["logical_data_fingerprint"],
        "accepted_corpus_changed",
    )
    source, contract = (
        decisions["source_revision"],
        decisions["search_contract_revision"],
    )
    for path in (accepted_path, "data/evaluation/query-labels.draft.json"):
        require(
            hashlib.sha256(revision_bytes(source, path)).hexdigest()
            == file_digest(path),
            "published_human_judgments_or_query_order_changed",
        )
    for entry in manifest["source_binding"]["files"]:
        require(
            hashlib.sha256(revision_bytes(source, entry["path"])).hexdigest()
            == entry["sha256"],
            "committed_dataset_source_differs",
        )
    for path in (
        "contracts/source/types.py",
        "contracts/search.md",
        "contracts/listings.md",
    ):
        require(
            hashlib.sha256(revision_bytes(contract, path)).hexdigest()
            == file_digest(path),
            "committed_public_contract_differs",
        )

    load_path = EVIDENCE + "/cloud-load-20261031/result.json"
    vector_path = EVIDENCE + "/vector-production-20261031/result.json"
    snapshot_path = EVIDENCE + "/dataset-snapshot-20261031/result.json"
    native_path = EVIDENCE + "/dataset-current-native-rebuild.json"
    workflow_path = EVIDENCE + "/step-03-human-reported-completion.json"
    loaded = files._read_json(ROOT / load_path)["actual_load_result"]
    vectors = files._read_json(ROOT / vector_path)["vector_result"]
    snapshot = files._read_json(ROOT / snapshot_path)["snapshot"]
    native = files._read_json(ROOT / native_path)
    workflow = files._read_json(ROOT / workflow_path)
    require(
        workflow["state"] == "complete_on_human_report",
        "step3_integration_completion_required",
    )
    require(
        loaded["input_fingerprint"]
        == native["input_fingerprint"]
        == accepted["input_fingerprint"],
        "load_rebuild_fingerprint_differs",
    )
    require(
        all(
            loaded[key] == count
            for key, count in {
                "users_verified": 5000,
                "listings_verified": 1000,
                "objects_verified": 1000,
                "images_verified": 1000,
                "regular_owners_verified": 1000,
                "available_verified": 800,
            }.items()
        ),
        "actual_load_counts_differ",
    )
    coverage = vectors["coverage"]
    require(
        coverage["state"] == "serving"
        and coverage["live"] == coverage["ready"] == 1000
        and coverage["encoding_matches"]
        and not coverage["conflicting_serving"]
        and all(
            coverage[key] == 0
            for key in (
                "missing",
                "stale",
                "pending",
                "leased",
                "failed",
                "invalid_parts",
            )
        ),
        "actual_vector_coverage_incomplete",
    )
    require(
        snapshot["source"]["logical_projection_digest"]
        == loaded["logical_projection_digest"]
        and snapshot["cloud_native_rebuild_match"] is True
        and native["cluster_stopped"] is True
        and snapshot["vector_index_snapshot"] == native["reset_reload"]["after"],
        "actual_snapshot_or_rebuild_differs",
    )
    eligible = eligible_reference_ids(bundle)
    rows = deepcopy(accepted["queries"])
    draft = files._read_json(ROOT / "data/evaluation/query-labels.draft.json")[
        "queries"
    ]
    require(len(rows) == len(draft) == 22, "accepted_query_count_changed")
    require(
        all(
            a["query_id"] == b["query_id"]
            and a["query_text"] == b["query_text"]
            and a["context"] == b["context"] == CONTEXT
            for a, b in zip(rows, draft, strict=True)
        ),
        "accepted_query_or_context_changed",
    )
    inputs = [
        accepted_path,
        decisions_path,
        RUN + "/manifest.json",
        RUN + "/dataset.json",
        load_path,
        vector_path,
        snapshot_path,
        native_path,
        workflow_path,
    ]
    evidence = {
        "kind": "actual_reference_label_binding",
        "dataset_is_preview": False,
        "logical_data_fingerprint": manifest["logical_data_fingerprint"],
        "schema_version": manifest["schema_version"],
        "source_revision": source,
        "input_source_base_revision": manifest["source_revision"],
        "search_contract_revision": contract,
        "seed": manifest["seed"],
        "generator_version": manifest["generator_version"],
        "counts": {"users": 5000, "listings": 1000, "images": 1000, "eligible": 800},
        "pipeline": coverage,
        "vector_index_snapshot": snapshot["vector_index_snapshot"],
        "measurement_window": manifest["measurement_window"],
        "workflow_completion_provenance": "human report; external executor/receipt not supplied",
        "source_acceptance": "Explicit Mohit decision for published dataset source and merged public contract",
        "inputs": [{"path": path, "sha256": file_digest(path)} for path in inputs],
        "final_freeze": False,
        "data_ready": False,
        "scoring_executed": False,
        "scope": "Step5 label artifact; Step6 formal freeze/readiness/independent review remain separate",
    }
    binding = DatasetBinding(
        manifest["logical_data_fingerprint"],
        MANIFEST,
        manifest["schema_version"],
        source,
        contract,
        frozenset(UUID(row["id"]) for row in bundle["listings"]),
        {UUID(row["query_id"]): eligible for row in rows},
        preview_only=False,
    )
    labels = {
        "format_version": "1",
        "status": "reviewed",
        "dataset": {
            key: getattr(binding, key)
            for key in (
                "logical_data_fingerprint",
                "manifest_path",
                "schema_version",
                "source_revision",
            )
        },
        "search_contract_revision": contract,
        "review": {
            "reviewer": accepted["reviewer"],
            "reviewed_at": decisions["reviewed_at"],
            "inclusion_policy": accepted["inclusion_policy"],
        },
        "queries": rows,
    }
    return labels, evidence, binding


def main(argv=None):
    """Write fixed Step5 outputs once, or independently revalidate existing bytes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("write", "validate"))
    parser.add_argument(
        "--image-root",
        type=Path,
        default=Path("/Users/mohitmahapatra/Desktop/clip-dataset-images"),
    )
    args = parser.parse_args(argv)
    try:
        labels, evidence, binding = materialize(args.image_root)
        target, witness = ROOT / LABELS, ROOT / MANIFEST
        if args.action == "write":
            require(
                not target.exists() and not witness.exists(),
                "existing_label_output_refused",
            )
            with witness.open("x") as stream:
                stream.write(json.dumps(evidence, indent=2) + "\n")
            cases = validate_labels(labels, binding)
            with target.open("x") as stream:
                stream.write(json.dumps(labels, indent=2) + "\n")
        else:
            require(
                canonical_json(files._read_json(witness)) == canonical_json(evidence),
                "label_binding_artifact_changed",
            )
            require(
                canonical_json(files._read_json(target)) == canonical_json(labels),
                "accepted_judgments_or_metadata_changed",
            )
            cases = validate_labels(files._read_json(target), binding)
        print(
            json.dumps(
                {
                    "label_status": "reviewed",
                    "queries": len(cases),
                    "included": sum(case.included for case in cases),
                    "eligible_listings": 800,
                    "source_revision": binding.source_revision,
                    "search_contract_revision": binding.search_contract_revision,
                    "judgments_changed": False,
                    "scoring_executed": False,
                    "data_ready": False,
                }
            )
        )
        return 0
    except Exception as error:
        result = {
            "state": "label_binding_refused",
            "failure_type": type(error).__name__,
        }
        if isinstance(error, ValueError) and re.fullmatch(r"[a-z_]{1,80}", str(error)):
            result["code"] = str(error)
        print(json.dumps(result))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
