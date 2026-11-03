"""Build non-executable NFR case drafts from the verified synthetic archive.

Hybrid cases are representative request inputs for the latency workload; they
do not need ordered expected results. This module and its output do not verify
human review or authorize a measurement.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.prepare_comparison_corpus import build_corpus


def build_nfr_drafts() -> dict[str, Any]:
    """Select expected browse pages and representative search inputs only."""
    corpus = build_corpus()
    result: dict[str, Any] = {
        "format_version": 1,
        "purpose": "nfr-case-drafts-not-executable",
        "execution_permitted": False,
        "nfr_accepted": False,
        "dataset": deepcopy(corpus["dataset"]),
        "reference_review": {
            "dataset": deepcopy(corpus["dataset"]),
            "browse": corpus["review"]["browse_and_detail"],
            "hybrid": "Representative query text/classes are bound to reviewed labels; ordered rankings are not required for NFR-02 latency. NFR-04 evaluates relevance separately.",
            "measurement_enabled": False,
        },
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
    args = parser.parse_args()
    try:
        bundle = build_nfr_drafts()
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(bundle, output, indent=2, ensure_ascii=False)
            output.write("\n")
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "NFR case draft failed; no workload was started\n")


if __name__ == "__main__":
    main()
