"""Synthetic cross-binding tests; no session or network transport exists here."""

from copy import deepcopy
import hashlib
import json
import subprocess
import sys

import pytest

from scripts.evaluation.k6.comparison_binding_preflight import validate_bindings
from scripts.evaluation.k6.comparison_ordered_results import bind_ordered_results
from scripts.evaluation.k6.prepare_comparison_corpus import FROZEN, LABELS, build_corpus


@pytest.fixture(scope="module")
def prepared():
    draft = build_corpus()
    frozen = json.loads(FROZEN.read_text())
    labels = json.loads(LABELS.read_text())
    ids = [row["listing_id"] for row in draft["cases"][0]["expected"]["items"]]
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
            for case in draft["cases"]
            if case["request"]["kind"] == "search"
        ],
    }
    corpus = bind_ordered_results(reference, "a" * 40)
    content = json.dumps(corpus, sort_keys=True).encode()
    plan = {
        "format_version": 1,
        "purpose": "offline-binding-check-not-authorization",
        "application_revision": "a" * 40,
        "dataset_fingerprint": draft["dataset"]["logical_data_fingerprint"],
        "case_corpus_sha256": hashlib.sha256(content).hexdigest(),
    }
    return plan, content, reference


def test_exact_bindings_pass_without_authorizing_or_attesting_review(prepared):
    plan, content, reference = prepared
    result = validate_bindings(plan, content, reference)
    assert result["bindings_match"] is True
    assert result["measurement_authorized"] is False
    assert result["reference_review_verified"] is False
    assert result["deployment_verified"] is False
    assert result["captured_manifest_checked"] is False


@pytest.mark.parametrize(
    ("key", "bad", "error"),
    [
        ("application_revision", None, "invalid_application_revision"),
        ("application_revision", "short", "invalid_application_revision"),
        ("dataset_fingerprint", "sha256:" + "0" * 64, "dataset_fingerprint_mismatch"),
        ("case_corpus_sha256", "0" * 64, "case_corpus_hash_mismatch"),
    ],
)
def test_missing_and_mismatched_plan_fails_before_reference_rebuild(
    prepared, monkeypatch, key, bad, error
):
    plan, content, reference = prepared
    plan = deepcopy(plan)
    plan[key] = bad
    monkeypatch.setattr(
        "scripts.evaluation.k6.comparison_binding_preflight.bind_ordered_results",
        lambda *_: pytest.fail("must refuse before rebuilding the corpus"),
    )
    with pytest.raises(ValueError, match=error):
        validate_bindings(plan, content, reference)


def test_different_source_revision_and_modified_corpus_fail(prepared):
    plan, content, reference = prepared
    changed = deepcopy(plan)
    changed["application_revision"] = "b" * 40
    with pytest.raises(ValueError, match="reference_binding_mismatch"):
        validate_bindings(changed, content, reference)
    corpus = json.loads(content)
    corpus["cases"][0]["expected"]["items"][0]["title"] = "altered synthetic field"
    altered = json.dumps(corpus, sort_keys=True).encode()
    changed = deepcopy(plan)
    changed["case_corpus_sha256"] = hashlib.sha256(altered).hexdigest()
    with pytest.raises(ValueError, match="case_corpus_does_not_match_reference"):
        validate_bindings(changed, altered, reference)


def test_optional_captured_manifest_checks_the_same_three_bindings(
    prepared, monkeypatch
):
    plan, content, reference = prepared
    calls = []

    def check_manifest(value, template):
        calls.append((value, template))
        return {"state": "captured"}

    monkeypatch.setattr(
        "scripts.evaluation.k6.comparison_binding_preflight.validate_manifest",
        check_manifest,
    )
    captured = {
        "revisions": {"application_revision": plan["application_revision"]},
        "dataset": {"logical_fingerprint": plan["dataset_fingerprint"]},
        "workload": {"case_corpus_sha256": "sha256:" + plan["case_corpus_sha256"]},
    }
    result = validate_bindings(plan, content, reference, captured)
    assert result["captured_manifest_checked"] is True
    assert len(calls) == 1
    for section, key, wrong in [
        ("revisions", "application_revision", "b" * 40),
        ("dataset", "logical_fingerprint", "sha256:" + "0" * 64),
        ("workload", "case_corpus_sha256", "0" * 64),
    ]:
        changed = deepcopy(captured)
        changed[section][key] = wrong
        with pytest.raises(ValueError, match="captured_manifest_binding_mismatch"):
            validate_bindings(plan, content, reference, changed)


def test_blank_captured_manifest_is_refused(prepared):
    from scripts.evaluation.k6.comparison_manifest import TEMPLATE

    plan, content, reference = prepared
    template = json.loads(TEMPLATE.read_text())
    with pytest.raises(ValueError, match="captured_manifest_required"):
        validate_bindings(plan, content, reference, template)


def test_cli_rejects_incomplete_plan_without_printing_reference(prepared, tmp_path):
    plan, content, reference = prepared
    plan = deepcopy(plan)
    plan["application_revision"] = None
    paths = [
        tmp_path / "plan.json",
        tmp_path / "corpus.json",
        tmp_path / "reference.json",
    ]
    paths[0].write_text(json.dumps(plan))
    paths[1].write_bytes(content)
    paths[2].write_text(json.dumps(reference))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.k6.comparison_binding_preflight",
            *map(str, paths),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert reference["queries"][0]["query_text"] not in result.stdout + result.stderr


def test_cli_rejects_explicit_null_captured_manifest(prepared, tmp_path):
    plan, content, reference = prepared
    plan_path, corpus_path, reference_path, capture_path = [
        tmp_path / name
        for name in ("plan.json", "corpus.json", "reference.json", "capture.json")
    ]
    plan_path.write_text(json.dumps(plan))
    corpus_path.write_bytes(content)
    reference_path.write_text(json.dumps(reference))
    capture_path.write_text("null")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.k6.comparison_binding_preflight",
            str(plan_path),
            str(corpus_path),
            str(reference_path),
            "--captured-manifest",
            str(capture_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
