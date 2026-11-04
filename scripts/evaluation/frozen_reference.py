"""Read the accepted NEXT-06 inputs without regenerating them from today's code.

The historical release/label producers deliberately validate their generation
inputs. Experiment consumers instead need the unchanged accepted archive and
judgments, even after additive API changes. Current runtime/schema/model revisions
still require separate run-manifest and target checks; this is no live-state proof.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from typing import Any
from uuid import UUID

from data.generators.manifest import canonical_json
from data.generators.reference import digest
from scripts.evaluation.reference_labels import eligible_reference_ids
from scripts.evaluation.reference_release import verify_archive
from scripts.evaluation.search import DatasetBinding, validate_labels

ROOT = Path(__file__).resolve().parents[2]
FROZEN = "docs/evaluation/domain/next-06/frozen-dataset.json"
LABELS = "data/evaluation/query-labels.json"
BINDING = "docs/evaluation/domain/next-06/transfer/final-label-binding.json"
INDEX = "data/transfer/next06-reference-20261030.json"
CONFIG_FIELDS = (
    "generator_version",
    "requested_counts",
    "source_revision",
    "seed",
    "logical_time",
    "schema_version",
    "source_binding",
    "recipe_digest",
    "image_source_digest",
    "sensitive_purchase_threshold_paise",
)


def load_frozen_reference() -> tuple[dict[str, Any], dict[str, Any], DatasetBinding]:
    """Verify published freeze/archive/member/label hashes, then bind all judgments.

    No input is rewritten, no generator is executed, and no human judgment or
    acceptance flag is inferred. Even absent ignored expanded dataset files are
    read directly from the verified archive. All45source photos are hash checked.
    """
    raw_freeze = (ROOT / FROZEN).read_bytes()
    published = subprocess.run(
        ["git", "show", "HEAD:" + FROZEN], cwd=ROOT, capture_output=True, check=True
    ).stdout
    if raw_freeze != published:
        raise ValueError("unpublished_frozen_reference_refused")
    frozen = json.loads(raw_freeze)
    if frozen.get("final_freeze") is not True or frozen.get("task") != "NEXT-06":
        raise ValueError("frozen_reference_required")
    records = {row["path"]: row["sha256"] for row in frozen["inputs"]}
    inputs = {}
    for name in (LABELS, BINDING, INDEX):
        raw = (ROOT / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != records[name]:
            raise ValueError("frozen_reference_input_changed")
        inputs[name] = json.loads(raw)
    index = inputs[INDEX]
    archive_path = ROOT / "data/transfer" / index["archive"]
    if (
        archive_path.name != "next06-reference-20261030.tar.gz"
        or records.get("data/transfer/" + index["archive"]) != index["archive_sha256"]
    ):
        raise ValueError("frozen_archive_binding_changed")
    verify_archive(index, archive_path)
    bundles = []
    with tarfile.open(archive_path) as source:
        for suffix in ("a", "b"):
            base = f"data/runs/next06-transfer-42-20261030-{suffix}/"
            content = source.extractfile(base + "dataset.json").read()
            raw_manifest = source.extractfile(base + "manifest.json").read()
            if (
                hashlib.sha256(content).hexdigest() != records[base + "dataset.json"]
                or hashlib.sha256(raw_manifest).hexdigest()
                != records[base + "manifest.json"]
            ):
                raise ValueError("frozen_dataset_member_changed")
            bundle = json.loads(content)
            manifest = json.loads(raw_manifest)
            logical = {
                "config": {key: manifest[key] for key in CONFIG_FIELDS},
                **{key: bundle[key] for key in ("users", "listings", "image_plan")},
            }
            if (
                canonical_json(bundle["manifest"]) != canonical_json(manifest)
                or digest(logical) != manifest["logical_data_fingerprint"]
                or manifest["logical_data_fingerprint"]
                != frozen["logical_data_fingerprint"]
            ):
                raise ValueError("frozen_dataset_fingerprint_changed")
            bundles.append(bundle)
    if any(
        canonical_json(bundles[0][key]) != canonical_json(bundles[1][key])
        for key in ("users", "listings", "image_plan")
    ):
        raise ValueError("frozen_repeated_data_differs")
    bundle = bundles[0]
    labels = inputs[LABELS]
    evidence = inputs[BINDING]
    eligible = eligible_reference_ids(bundle)
    if any(
        evidence[key] != frozen[key]
        for key in (
            "logical_data_fingerprint",
            "schema_version",
            "source_revision",
            "search_contract_revision",
        )
    ):
        raise ValueError("frozen_label_binding_changed")
    if labels["review"] != frozen["labels"]["review"] or evidence["counts"] != {
        "users": 5000,
        "listings": 1000,
        "images": 1000,
        "eligible": 800,
    }:
        raise ValueError("frozen_review_or_counts_changed")
    binding = DatasetBinding(
        frozen["logical_data_fingerprint"],
        BINDING,
        frozen["schema_version"],
        frozen["source_revision"],
        frozen["search_contract_revision"],
        frozenset(UUID(row["id"]) for row in bundle["listings"]),
        {UUID(row["query_id"]): eligible for row in labels["queries"]},
        preview_only=False,
    )
    cases = validate_labels(labels, binding)
    if (
        len(labels["queries"]) != frozen["labels"]["queries"]
        or sum(case.included for case in cases) != frozen["labels"]["included"]
    ):
        raise ValueError("frozen_reviewed_query_count_changed")
    return bundle, labels, binding
