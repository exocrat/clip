"""Bind supplied ordered Hybrid reference IDs to the frozen comparison corpus.

This offline preparation tool validates input bindings and reconstructs public
listing fields from the synthetic archive. It neither retrieves results nor
attests that the supplied human-review reference or DATA-READY is accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile
from typing import Any

from scripts.evaluation.k6.prepare_comparison_corpus import (
    ARCHIVE,
    FINGERPRINT,
    FROZEN,
    LABELS,
    REFERENCE_TIME,
    _read_json,
    _summary,
    build_corpus,
)

ROOT_KEYS = {
    "format_version",
    "dataset_fingerprint",
    "schema_version",
    "search_contract_revision",
    "search_implementation_revision",
    "model_revision",
    "review_record_reference",
    "queries",
}
QUERY_KEYS = {"query_id", "query_text", "ordered_listing_ids", "has_next"}


def bind_ordered_results(reference: Any, expected_revision: str) -> dict[str, Any]:
    """Bind reviewed pages to a separately supplied full search source revision."""
    if not isinstance(expected_revision, str) or not re.fullmatch(
        r"[0-9a-f]{40}", expected_revision
    ):
        raise ValueError("invalid_expected_search_revision")
    frozen = json.loads(FROZEN.read_text())
    labels = json.loads(LABELS.read_text())
    if not isinstance(reference, dict) or set(reference) != ROOT_KEYS:
        raise ValueError("invalid_reference_shape")
    if (
        type(reference["format_version"]) is not int
        or reference["format_version"] != 1
        or reference["dataset_fingerprint"] != FINGERPRINT
        or reference["schema_version"] != frozen["schema_version"]
        or reference["search_contract_revision"] != labels["search_contract_revision"]
        or reference["search_implementation_revision"] != expected_revision
        or reference["model_revision"] != frozen["model"]["revision"]
    ):
        raise ValueError("reference_binding_mismatch")
    review = reference["review_record_reference"]
    if (
        not isinstance(review, str)
        or not review.strip()
        or len(review) > 240
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", review)
        or ".." in Path(review).parts
    ):
        raise ValueError("review_record_reference_required")

    corpus = build_corpus()  # Verifies both archived dataset copies and the labels.
    searches = {
        item["relevance_reference"]["query_id"]: item
        for item in corpus["cases"]
        if item["request"]["kind"] == "search"
    }
    queries = reference["queries"]
    if not isinstance(queries, list) or len(queries) != len(searches):
        raise ValueError("three_reference_queries_required")
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        data = _read_json(
            archive, "data/runs/next06-transfer-42-20261030-a/dataset.json"
        )
    rows = {row["id"]: row for row in data["listings"]}
    images = {item["listing_id"]: item["image_id"] for item in data["image_plan"]}
    seen_queries = set()
    for query in queries:
        if not isinstance(query, dict) or set(query) != QUERY_KEYS:
            raise ValueError("invalid_reference_query")
        query_id = query["query_id"]
        if (
            not isinstance(query_id, str)
            or query_id not in searches
            or query_id in seen_queries
        ):
            raise ValueError("unknown_or_duplicate_query")
        case = searches[query_id]
        if query["query_text"] != case["request"]["query"]["q"]:
            raise ValueError("query_text_mismatch")
        ids = query["ordered_listing_ids"]
        has_next = query["has_next"]
        if (
            not isinstance(ids, list)
            or any(not isinstance(item, str) for item in ids)
            or len(set(ids)) != len(ids)
            or len(ids) > 20
            or type(has_next) is not bool
            or (has_next and len(ids) != 20)
        ):
            raise ValueError("invalid_ordered_page")
        items = []
        for listing_id in ids:
            row = rows.get(listing_id)
            if (
                row is None
                or listing_id not in images
                or row["availability"] != "available"
                or row["available_from"] > REFERENCE_TIME
                or row["available_until"] <= REFERENCE_TIME
            ):
                raise ValueError("unknown_or_unavailable_listing")
            items.append(_summary(row, images[listing_id]))
        case["expected"] = {
            "items": items,
            "page": 1,
            "page_size": 20,
            "has_next": has_next,
        }
        case["relevance_reference"][
            "ordered_response_state"
        ] = "supplied_review_reference_not_independently_verified"
        seen_queries.add(query_id)
    if seen_queries != set(searches):
        raise ValueError("reference_query_missing")
    corpus["status"] = "ordered_references_supplied_review_not_verified"
    corpus["review"][
        "hybrid"
    ] = "ordered references supplied; validate human review and final data binding before use"
    corpus["review"]["ordered_reference_record"] = review
    corpus["review"]["ordered_reference_binding"] = {
        "search_contract_revision": reference["search_contract_revision"],
        "search_implementation_revision": expected_revision,
        "model_revision": reference["model_revision"],
        "canonical_json_sha256": hashlib.sha256(
            json.dumps(reference, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    corpus["review"]["measurement_enabled"] = False
    corpus["purpose"] = "EXP-02 prepared reference cases; not authorization to run"
    return corpus


def main() -> int:
    """Read a non-secret reference file and exclusively create a new corpus."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("ordered_results", type=Path)
    parser.add_argument(
        "--search-revision", required=True, help="full intended search source commit"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        reference = json.loads(args.ordered_results.read_text(encoding="utf-8"))
        corpus = bind_ordered_results(reference, args.search_revision)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(corpus, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "Reference validation failed; no workload was started\n")
    print(json.dumps({"status": corpus["status"], "measurement_enabled": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
