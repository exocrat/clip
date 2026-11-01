"""Synthetic tests only; no result or human review is fabricated as evidence."""

from copy import deepcopy
import json
import subprocess
import sys

import pytest

from scripts.evaluation.k6.prepare_nfr_cases import build_nfr_drafts
from scripts.evaluation.k6.prepare_comparison_corpus import FROZEN, LABELS


def test_draft_is_deterministic_and_preserves_incomplete_hybrid():
    draft = build_nfr_drafts()
    assert draft == build_nfr_drafts()
    assert draft["execution_permitted"] is False
    assert draft["nfr_accepted"] is False
    assert len(draft["nfr_01"]) == 5
    assert all(
        c["expected"] is not None and c["expected_status"] == 200
        for c in draft["nfr_01"]
    )
    assert len(draft["nfr_02"]) == 3
    assert all(c["expected"] is None for c in draft["nfr_02"])
    assert all(
        c["request"]["query"]["search_mode"] == "hybrid" for c in draft["nfr_02"]
    )


def test_reference_and_revision_are_both_required():
    with pytest.raises(ValueError, match="supplied_together"):
        build_nfr_drafts({}, None)
    with pytest.raises(ValueError, match="supplied_together"):
        build_nfr_drafts(None, "a" * 40)


def test_reference_passes_to_existing_binder_without_claiming_approval(monkeypatch):
    draft = build_nfr_drafts()
    cases = deepcopy(draft["nfr_01"] + draft["nfr_02"])
    for item in cases:
        item.pop("expected_status")
    corpus = {
        "dataset": draft["dataset"],
        "review": draft["reference_review"],
        "cases": cases,
    }
    called = []

    def binder(reference, revision):
        called.append((reference, revision))
        return corpus

    monkeypatch.setattr(
        "scripts.evaluation.k6.prepare_nfr_cases.bind_ordered_results", binder
    )
    result = build_nfr_drafts({"synthetic": True}, "a" * 40)
    assert called == [({"synthetic": True}, "a" * 40)]
    assert result["execution_permitted"] is False


def test_supplied_synthetic_order_uses_real_binder_and_refuses_mismatch():
    draft = build_nfr_drafts()
    frozen = json.loads(FROZEN.read_text())
    labels = json.loads(LABELS.read_text())
    ids = [item["listing_id"] for item in draft["nfr_01"][0]["expected"]["items"]]
    reference = {
        "format_version": 1,
        "dataset_fingerprint": draft["dataset"]["logical_data_fingerprint"],
        "schema_version": draft["dataset"]["schema_version"],
        "search_contract_revision": labels["search_contract_revision"],
        "search_implementation_revision": "a" * 40,
        "model_revision": frozen["model"]["revision"],
        "review_record_reference": "synthetic-test-only/review",
        "queries": [
            {
                "query_id": case["relevance_reference"]["query_id"],
                "query_text": case["request"]["query"]["q"],
                "ordered_listing_ids": list(reversed(ids)),
                "has_next": True,
            }
            for case in draft["nfr_02"]
        ],
    }
    result = build_nfr_drafts(reference, "a" * 40)
    assert result["nfr_02"][0]["expected"]["items"][0]["listing_id"] == ids[-1]
    assert result["execution_permitted"] is False
    with pytest.raises(ValueError, match="reference_binding_mismatch"):
        build_nfr_drafts(reference, "b" * 40)


def test_cli_refuses_existing_output_and_incomplete_revision(tmp_path):
    output = tmp_path / "draft.json"
    output.write_text("preserve")
    cmd = [
        sys.executable,
        "-m",
        "scripts.evaluation.k6.prepare_nfr_cases",
        "--output",
        str(output),
    ]
    assert subprocess.run(cmd, capture_output=True, check=False).returncode == 2
    assert output.read_text() == "preserve"
    missing = tmp_path / "new.json"
    cmd[-1] = str(missing)
    cmd.extend(["--search-revision", "a" * 40])
    assert subprocess.run(cmd, capture_output=True, check=False).returncode == 2
    assert not missing.exists()
