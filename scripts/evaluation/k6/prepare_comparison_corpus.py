"""Prepare a dataset-bound EXP-02 case draft without inventing Hybrid rank.

Browse/detail expectations come only from the frozen synthetic archive and the
public response contract. Hybrid requests bind to accepted query labels, but
their ordered expected responses remain null until separately reviewed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "data/transfer/next06-reference-20261030.tar.gz"
FROZEN = ROOT / "docs/evaluation/domain/next-06/frozen-dataset.json"
LABELS = ROOT / "data/evaluation/query-labels.json"
DEFAULT_OUTPUT = ROOT / "data/evaluation/workloads/ecs-lambda-case-corpus-v1.json"
FINGERPRINT = "sha256:7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98"
REFERENCE_TIME = "2026-11-01T00:00:00.000000Z"
CATEGORY_LABELS = {
    "mobile_phone": "Mobile Phones",
    "laptop": "Laptops",
    "electronics": "Electronics",
    "furniture": "Furniture",
    "books": "Books and Study Materials",
    "bicycles": "Bicycles",
    "appliances": "Home Appliances",
    "sports_fitness": "Sports & Fitness",
    "other": "Other",
}
CONDITION_LABELS = {
    "new": "New / Unused",
    "like_new": "Like New",
    "good": "Good",
    "fair": "Fair",
}
SENSITIVE_CATEGORIES = {"mobile_phone", "laptop"}
SENSITIVE_PRICE_THRESHOLD_PAISE = 500_000


def _read_json(archive: tarfile.TarFile, member: str) -> Any:
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError("required_archive_member_missing")
    return json.load(stream)


def _summary(row: dict[str, Any], image_id: str) -> dict[str, Any]:
    category = row["category_code"]
    condition = row["condition_code"]
    return {
        "listing_id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "category_code": category,
        "category_label": CATEGORY_LABELS[category],
        "condition_code": condition,
        "condition_label": CONDITION_LABELS[condition],
        "asking_price_paise": row["asking_price_paise"],
        "original_price_paise": None,
        "negotiable": row["negotiable"],
        "pickup_area": row["pickup_area"],
        "available_from": row["available_from"],
        "available_until": row["available_until"],
        "availability": row["availability"],
        "sensitive_purchase": category in SENSITIVE_CATEGORIES
        or row["asking_price_paise"] > SENSITIVE_PRICE_THRESHOLD_PAISE,
        "image_ids": [image_id],
    }


def _case_page(
    rows: list[dict[str, Any]], images: dict[str, str], query: dict[str, Any]
) -> dict[str, Any]:
    page = query["page"]
    size = query["page_size"]
    offset = (page - 1) * size
    eligible = []
    for row in rows:
        if (
            row["availability"] != "available"
            or row["available_from"] > REFERENCE_TIME
            or row["available_until"] <= REFERENCE_TIME
            or "category_code" in query
            and row["category_code"] not in query["category_code"]
        ):
            continue
        eligible.append(row)
    eligible.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
    selected = eligible[offset : offset + size]
    return {
        "items": [_summary(row, images[row["id"]]) for row in selected],
        "page": page,
        "page_size": size,
        "has_next": offset + size < len(eligible),
    }


def _query_label_index(labels: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["query_text"]: item for item in labels["queries"]}


def build_corpus() -> dict[str, Any]:
    frozen = json.loads(FROZEN.read_text())
    labels = json.loads(LABELS.read_text())
    archive_sha = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if (
        frozen["logical_data_fingerprint"] != FINGERPRINT
        or frozen["transfer"]["sha256"] != archive_sha
        or labels["status"] != "reviewed"
        or labels["dataset"]["logical_data_fingerprint"] != FINGERPRINT
    ):
        raise ValueError("frozen_dataset_or_labels_binding_mismatch")

    with tarfile.open(ARCHIVE, "r:gz") as archive:
        datasets = {}
        for side in ("a", "b"):
            prefix = f"data/runs/next06-transfer-42-20261030-{side}"
            manifest = _read_json(archive, f"{prefix}/manifest.json")
            dataset = _read_json(archive, f"{prefix}/dataset.json")
            if (
                manifest["logical_data_fingerprint"] != FINGERPRINT
                or manifest["schema_version"] != frozen["schema_version"]
                or manifest["seed"] != frozen["seed"]
            ):
                raise ValueError("archive_manifest_binding_mismatch")
            datasets[side] = dataset
        left, right = datasets["a"], datasets["b"]
        if (
            left["listings"] != right["listings"]
            or left["image_plan"] != right["image_plan"]
        ):
            raise ValueError("archive_a_b_data_mismatch")

    rows = left["listings"]
    images = {item["listing_id"]: item["image_id"] for item in left["image_plan"]}
    if len(rows) != frozen["distribution_counts"]["listings"] or len(images) != len(
        rows
    ):
        raise ValueError("archive_count_mismatch")
    available = [
        row
        for row in rows
        if row["availability"] == "available"
        and row["available_from"] <= REFERENCE_TIME
        and row["available_until"] > REFERENCE_TIME
    ]
    if (
        len(available)
        != frozen["distribution_counts"]["availability_scenarios"]["available"]
    ):
        raise ValueError("available_count_mismatch")

    labels_by_text = _query_label_index(labels)
    search_definitions = [
        ("android smartphone", "direct_word"),
        ("mobile phone", "related_word"),
        ("student computer", "meaning_based"),
    ]
    cases: list[dict[str, Any]] = []
    browse_queries = [
        ("browse_all_first", {"sort": "created_desc", "page": 1, "page_size": 20}),
        ("browse_all_later", {"sort": "created_desc", "page": 2, "page_size": 20}),
        (
            "browse_bicycles_first",
            {
                "sort": "created_desc",
                "page": 1,
                "page_size": 20,
                "category_code": ["bicycles"],
            },
        ),
        (
            "browse_bicycles_later",
            {
                "sort": "created_desc",
                "page": 2,
                "page_size": 20,
                "category_code": ["bicycles"],
            },
        ),
        (
            "browse_books_first",
            {
                "sort": "created_desc",
                "page": 1,
                "page_size": 20,
                "category_code": ["books"],
            },
        ),
    ]
    for case_id, query in browse_queries:
        cases.append(
            {
                "case_id": case_id,
                "request": {"kind": "browse", "query": query},
                "expected": _case_page(rows, images, query),
                "reference_state": "dataset_derived_ordered_expected_pending_search_owner_review",
            }
        )

    for case_id, (query_text, query_class) in zip(
        ("hybrid_direct", "hybrid_related", "hybrid_meaning"), search_definitions
    ):
        label = labels_by_text[query_text]
        cases.append(
            {
                "case_id": case_id,
                "request": {
                    "kind": "search",
                    "query": {
                        "q": query_text,
                        "search_mode": "hybrid",
                        "sort": "relevance",
                        "page": 1,
                        "page_size": 20,
                    },
                },
                "expected": None,
                "relevance_reference": {
                    "query_id": label["query_id"],
                    "relevant_listing_ids": label["relevant_listing_ids"],
                    "query_class": query_class,
                    "ordered_response_state": "pending_final_data_ready_search_reference_and_review",
                },
            }
        )

    detail_rows = sorted(available, key=lambda row: (row["created_at"], row["id"]))
    for case_id, row in zip(
        ("detail_available_a", "detail_available_b"), (detail_rows[0], detail_rows[-1])
    ):
        expected = _summary(row, images[row["id"]])
        expected["proof_available"] = row["proof_available"]
        cases.append(
            {
                "case_id": case_id,
                "request": {"kind": "detail", "listing_id": row["id"]},
                "expected": expected,
                "reference_state": "dataset_derived_expected_pending_search_owner_review",
            }
        )

    return {
        "format_version": 1,
        "status": "draft_search_order_pending",
        "purpose": "EXP-02 dataset-bound comparison case preparation; not executable",
        "dataset": {
            "logical_data_fingerprint": FINGERPRINT,
            "archive_sha256": archive_sha,
            "schema_version": frozen["schema_version"],
            "seed": frozen["seed"],
            "reference_time": REFERENCE_TIME,
            "availability_window_ends": frozen["measurement_window"]["before"],
            "data_ready": frozen["data_ready"],
        },
        "review": {
            "browse_and_detail": "expected from frozen records and current public listing contract; review pending",
            "hybrid": "requests and reviewed relevance-ID sets bound; ordered response must be separately reviewed",
            "measurement_enabled": False,
        },
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    corpus = build_corpus()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(corpus, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "cases": len(corpus["cases"]),
                "status": corpus["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
