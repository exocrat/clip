"""Synthetic tests only; no result or human review is fabricated as evidence."""

import json
import subprocess
import sys

from scripts.evaluation.k6.prepare_nfr_cases import build_nfr_drafts


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
    assert all(
        c["relevance_reference"]["query_class"]
        in {"direct_word", "related_word", "meaning_based"}
        for c in draft["nfr_02"]
    )
    assert "not required for NFR-02 latency" in draft["reference_review"]["hybrid"]


def test_cli_refuses_existing_output_and_writes_latency_cases_without_rankings(
    tmp_path,
):
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
    completed = subprocess.run(cmd, capture_output=True, check=False)
    assert completed.returncode == 0
    result = json.loads(missing.read_text())
    assert result["execution_permitted"] is False
    assert result["nfr_accepted"] is False
    assert all(case["expected"] is None for case in result["nfr_02"])
