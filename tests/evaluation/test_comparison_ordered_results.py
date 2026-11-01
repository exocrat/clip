"""Exercise ordered-reference binding with invented test-only result orders."""

from copy import deepcopy
import json
import subprocess
import sys

import pytest

from scripts.evaluation.k6.comparison_ordered_results import bind_ordered_results
from scripts.evaluation.k6.prepare_comparison_corpus import FROZEN, LABELS, build_corpus

REVISION = "a" * 40  # Explicitly synthetic; not an actual deployed revision.


@pytest.fixture(scope="module")
def reference():
    """Create a synthetic reference envelope; it is not reviewed search output."""
    corpus = build_corpus()
    frozen = json.loads(FROZEN.read_text())
    labels = json.loads(LABELS.read_text())
    ids = [item["listing_id"] for item in corpus["cases"][0]["expected"]["items"]]
    return {
        "format_version": 1,
        "dataset_fingerprint": corpus["dataset"]["logical_data_fingerprint"],
        "schema_version": corpus["dataset"]["schema_version"],
        "search_contract_revision": labels["search_contract_revision"],
        "search_implementation_revision": REVISION,
        "model_revision": frozen["model"]["revision"],
        "review_record_reference": "synthetic-test-only/review",
        "queries": [
            {
                "query_id": case["relevance_reference"]["query_id"],
                "query_text": case["request"]["query"]["q"],
                "ordered_listing_ids": list(reversed(ids)),
                "has_next": True,
            }
            for case in corpus["cases"]
            if case["request"]["kind"] == "search"
        ],
    }


def test_binds_order_and_fields_without_claiming_review_or_run_authorization(reference):
    corpus = bind_ordered_results(deepcopy(reference), REVISION)
    search_cases = [c for c in corpus["cases"] if c["request"]["kind"] == "search"]
    assert len(search_cases) == 3
    for case, query in zip(search_cases, reference["queries"], strict=True):
        assert [row["listing_id"] for row in case["expected"]["items"]] == query[
            "ordered_listing_ids"
        ]
        assert case["expected"]["has_next"] is True
        assert all(row["title"] for row in case["expected"]["items"])
    assert corpus["review"]["measurement_enabled"] is False
    assert corpus["dataset"]["data_ready"] is False
    assert "not_verified" in corpus["status"]
    assert (
        corpus["review"]["ordered_reference_binding"]["search_implementation_revision"]
        == REVISION
    )
    assert (
        len(corpus["review"]["ordered_reference_binding"]["canonical_json_sha256"])
        == 64
    )


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (
            lambda ref: ref.update(dataset_fingerprint="sha256:" + "0" * 64),
            "reference_binding_mismatch",
        ),
        (lambda ref: ref.update(model_revision="wrong"), "reference_binding_mismatch"),
        (
            lambda ref: ref.update(search_implementation_revision="b" * 40),
            "reference_binding_mismatch",
        ),
        (
            lambda ref: ref.update(search_implementation_revision=None),
            "reference_binding_mismatch",
        ),
        (
            lambda ref: ref.update(review_record_reference=""),
            "review_record_reference_required",
        ),
        (
            lambda ref: ref.update(review_record_reference="Bearer private-value"),
            "review_record_reference_required",
        ),
        (
            lambda ref: ref["queries"][0].update(query_text="different"),
            "query_text_mismatch",
        ),
        (
            lambda ref: ref["queries"][0]["ordered_listing_ids"].append(
                ref["queries"][0]["ordered_listing_ids"][0]
            ),
            "invalid_ordered_page",
        ),
        (
            lambda ref: ref["queries"][0].update(
                ordered_listing_ids=["unknown"], has_next=False
            ),
            "unknown_or_unavailable_listing",
        ),
        (
            lambda ref: ref["queries"][0].update(ordered_listing_ids=[], has_next=True),
            "invalid_ordered_page",
        ),
        (
            lambda ref: ref["queries"].append(ref["queries"][0]),
            "three_reference_queries_required",
        ),
    ],
)
def test_rejects_unbound_or_malformed_references(reference, mutate, error):
    candidate = deepcopy(reference)
    mutate(candidate)
    with pytest.raises(ValueError, match=error):
        bind_ordered_results(candidate, REVISION)


@pytest.mark.parametrize("expected", ["", "a" * 39, "A" * 40, "not-a-revision"])
def test_refuses_invalid_intended_revision_before_corpus(
    reference, expected, monkeypatch
):
    monkeypatch.setattr(
        "scripts.evaluation.k6.comparison_ordered_results.build_corpus",
        lambda: pytest.fail("must reject before loading the corpus"),
    )
    with pytest.raises(ValueError, match="invalid_expected_search_revision"):
        bind_ordered_results(reference, expected)


def test_refuses_revision_mismatch_before_corpus(reference, monkeypatch):
    monkeypatch.setattr(
        "scripts.evaluation.k6.comparison_ordered_results.build_corpus",
        lambda: pytest.fail("must reject mismatch before loading the corpus"),
    )
    with pytest.raises(ValueError, match="reference_binding_mismatch"):
        bind_ordered_results(reference, "b" * 40)


def test_cli_never_overwrites_or_creates_output_for_bad_input(reference, tmp_path):
    reference_path = tmp_path / "synthetic-reference.json"
    output = tmp_path / "prepared.json"
    reference_path.write_text(json.dumps(reference))
    command = [
        sys.executable,
        "-m",
        "scripts.evaluation.k6.comparison_ordered_results",
        str(reference_path),
        "--search-revision",
        REVISION,
        "--output",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert reference["queries"][0]["ordered_listing_ids"][0] not in completed.stdout
    original = output.read_bytes()
    repeated = subprocess.run(command, capture_output=True, text=True, check=False)
    assert repeated.returncode == 2
    assert output.read_bytes() == original
    mismatched_output = tmp_path / "mismatch.json"
    mismatch = command.copy()
    mismatch[5] = "b" * 40
    mismatch[7] = str(mismatched_output)
    assert subprocess.run(mismatch, capture_output=True, check=False).returncode == 2
    assert not mismatched_output.exists()
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}")
    invalid_output = tmp_path / "invalid-output.json"
    command[3] = str(invalid_path)
    command[7] = str(invalid_output)
    rejected = subprocess.run(command, capture_output=True, text=True, check=False)
    assert rejected.returncode == 2
    assert not invalid_output.exists()
