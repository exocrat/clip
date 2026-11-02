"""Offline planned-input cross-check; never obtains credentials or sends requests.

The existing run manifest is a post-run capture. This separate check compares
the intended source, dataset and corpus against the reviewed-reference envelope.
It does not attest review or a deployed application's identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.evaluation.k6.comparison_manifest import TEMPLATE, validate_manifest
from scripts.evaluation.k6.comparison_ordered_results import bind_ordered_results
from scripts.evaluation.k6.prepare_comparison_corpus import FINGERPRINT

MAX_INPUT_BYTES = 5_000_000
PLAN_KEYS = {
    "format_version",
    "purpose",
    "application_revision",
    "dataset_fingerprint",
    "case_corpus_sha256",
}


def validate_bindings(
    plan: Any, corpus_bytes: bytes, reference: Any, captured_manifest: Any = None
) -> dict[str, Any]:
    """Rebuild the corpus from the archive and compare all declared bindings."""
    if not isinstance(plan, dict) or set(plan) != PLAN_KEYS:
        raise ValueError("invalid_plan_shape")
    if (
        type(plan["format_version"]) is not int
        or plan["format_version"] != 1
        or plan["purpose"] != "offline-binding-check-not-authorization"
    ):
        raise ValueError("invalid_plan_kind")
    revision = plan["application_revision"]
    digest = plan["case_corpus_sha256"]
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("invalid_application_revision")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid_corpus_hash")
    if plan["dataset_fingerprint"] != FINGERPRINT:
        raise ValueError("dataset_fingerprint_mismatch")
    if (
        len(corpus_bytes) > MAX_INPUT_BYTES
        or hashlib.sha256(corpus_bytes).hexdigest() != digest
    ):
        raise ValueError("case_corpus_hash_mismatch")
    if captured_manifest is not None:
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        checked = validate_manifest(captured_manifest, template)
        if checked["state"] != "captured":
            raise ValueError("captured_manifest_required")
        if (
            captured_manifest["revisions"]["application_revision"] != revision
            or captured_manifest["dataset"]["logical_fingerprint"].removeprefix(
                "sha256:"
            )
            != FINGERPRINT.removeprefix("sha256:")
            or captured_manifest["workload"]["case_corpus_sha256"].removeprefix(
                "sha256:"
            )
            != digest
        ):
            raise ValueError("captured_manifest_binding_mismatch")
    corpus = json.loads(corpus_bytes)
    rebuilt = bind_ordered_results(reference, revision)
    # Compare JSON encodings, not Python values: Python considers True equal
    # to 1, but those are different response expectations in a workload case.
    if json.dumps(
        corpus, sort_keys=True, separators=(",", ":"), allow_nan=False
    ) != json.dumps(rebuilt, sort_keys=True, separators=(",", ":"), allow_nan=False):
        raise ValueError("case_corpus_does_not_match_reference")
    return {
        "bindings_match": True,
        "measurement_authorized": False,
        "reference_review_verified": False,
        "deployment_verified": False,
        "captured_manifest_checked": captured_manifest is not None,
        "note": "Offline input consistency only; remaining run gates still apply.",
    }


def _read_bounded(path: Path) -> bytes:
    """Read a local bounded artifact, without resolving remote resources."""
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("input_too_large")
    data = path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input_too_large")
    return data


def main() -> None:
    """Check three local JSON files and print only a sanitized result."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("plan", type=Path)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("ordered_reference", type=Path)
    parser.add_argument("--captured-manifest", type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(_read_bounded(args.plan))
        corpus_bytes = _read_bounded(args.corpus)
        reference = json.loads(_read_bounded(args.ordered_reference))
        captured = (
            json.loads(_read_bounded(args.captured_manifest))
            if args.captured_manifest is not None
            else None
        )
        if args.captured_manifest is not None and captured is None:
            raise ValueError("captured_manifest_required")
        result = validate_bindings(plan, corpus_bytes, reference, captured)
        print(json.dumps(result, sort_keys=True))
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "Binding preflight failed; no workload was started\n")


if __name__ == "__main__":
    main()
