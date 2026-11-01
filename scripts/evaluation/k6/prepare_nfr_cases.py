"""Build non-executable NFR case drafts from the verified synthetic archive.

Optional ordered Hybrid inputs must pass the existing reference binder. Neither
this module nor its output verifies human review or authorizes a measurement.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_ordered_results import bind_ordered_results
from scripts.evaluation.k6.prepare_comparison_corpus import build_corpus

MAX_REFERENCE_BYTES = 1_000_000


def build_nfr_drafts(
    reference: Any | None = None, search_revision: str | None = None
) -> dict[str, Any]:
    """Select exact browse and Hybrid cases, preserving their review limitations."""
    if (reference is None) != (search_revision is None):
        raise ValueError("ordered_reference_and_revision_must_be_supplied_together")
    corpus = (
        build_corpus()
        if reference is None
        else bind_ordered_results(reference, search_revision or "")
    )
    result: dict[str, Any] = {
        "format_version": 1,
        "purpose": "nfr-case-drafts-not-executable",
        "execution_permitted": False,
        "nfr_accepted": False,
        "dataset": deepcopy(corpus["dataset"]),
        "reference_review": deepcopy(corpus["review"]),
        "nfr_01": [],
        "nfr_02": [],
    }
    for case in corpus["cases"]:
        kind = case["request"]["kind"]
        if kind not in {"browse", "search"}:
            continue
        selected = deepcopy(case)
        selected["expected_status"] = 200
        result["nfr_01" if kind == "browse" else "nfr_02"].append(selected)
    if len(result["nfr_01"]) != 5 or len(result["nfr_02"]) != 3:
        raise ValueError("unexpected_candidate_case_mix")
    return result


def main() -> None:
    """Write a new draft bundle; never overwrite an existing artifact."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ordered-reference", type=Path)
    parser.add_argument("--search-revision")
    args = parser.parse_args()
    try:
        if args.ordered_reference is None:
            reference = None
        else:
            if args.ordered_reference.stat().st_size > MAX_REFERENCE_BYTES:
                raise ValueError("ordered_reference_too_large")
            reference = json.loads(args.ordered_reference.read_text(encoding="utf-8"))
        bundle = build_nfr_drafts(reference, args.search_revision)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(bundle, output, indent=2, ensure_ascii=False)
            output.write("\n")
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "NFR case draft failed; no workload was started\n")


if __name__ == "__main__":
    main()
