"""Verify proposed parity inputs offline; no rankings or requests are generated."""

from copy import deepcopy
import hashlib
import json
import subprocess

import pytest

from scripts.evaluation.k6.comparison_parity_corpus import build_parity_corpus
from scripts.evaluation.k6.comparison_binding_preflight import validate_bindings
from scripts.evaluation.k6.prepare_comparison_corpus import FINGERPRINT, FROZEN, LABELS


@pytest.fixture(scope="module")
def binding():
    return {
        "format_version": 2,
        "dataset_fingerprint": FINGERPRINT,
        "schema_version": json.loads(FROZEN.read_text())["schema_version"],
        "search_contract_revision": json.loads(LABELS.read_text())[
            "search_contract_revision"
        ],
        "search_implementation_revision": "a" * 40,
        "model_revision": json.loads(FROZEN.read_text())["model"]["revision"],
    }


def test_deterministic_bound_cases_do_not_invent_search_results(binding):
    corpus = build_parity_corpus(binding, "a" * 40)
    assert corpus == build_parity_corpus(binding, "a" * 40)
    searches = [case for case in corpus["cases"] if case["request"]["kind"] == "search"]
    assert len(corpus["cases"]) == 10 and len(searches) == 3
    assert all(case["expected"] is None for case in searches)
    assert corpus["review"]["measurement_enabled"] is False


@pytest.mark.parametrize(
    "field",
    [
        "dataset_fingerprint",
        "schema_version",
        "search_contract_revision",
        "search_implementation_revision",
        "model_revision",
    ],
)
def test_refuses_mismatched_bindings(binding, field):
    altered = deepcopy(binding)
    altered[field] = "incorrect"
    with pytest.raises(ValueError, match="search_binding_mismatch"):
        build_parity_corpus(altered, "a" * 40)


def test_refuses_missing_extra_or_invalid_revision(binding):
    altered = deepcopy(binding)
    altered["ordered_listing_ids"] = []
    with pytest.raises(ValueError, match="invalid_binding_shape"):
        build_parity_corpus(altered, "a" * 40)
    with pytest.raises(ValueError, match="invalid_search_revision"):
        build_parity_corpus(binding, "latest")


def test_checked_draft_and_synthetic_search_parity_connect_without_workload(binding):
    corpus = build_parity_corpus(binding, "a" * 40)
    content = json.dumps(corpus, sort_keys=True).encode()
    plan = {
        "format_version": 1,
        "purpose": "offline-binding-check-not-authorization",
        "application_revision": "a" * 40,
        "dataset_fingerprint": FINGERPRINT,
        "case_corpus_sha256": hashlib.sha256(content).hexdigest(),
    }
    checked = validate_bindings(plan, content, binding, allow_parity_draft=True)
    assert checked["measurement_authorized"] is False
    searches = [case for case in corpus["cases"] if case["request"]["kind"] == "search"]
    page = {"items": [], "page": 1, "page_size": 20, "has_next": False}
    cases = [
        {
            "case_id": case["case_id"],
            "request": case["request"],
            "a": {"status": 200, "body": page},
            "b": {"status": 200, "body": page},
        }
        for case in searches
    ]
    source = (
        "import {readFileSync} from 'node:fs';"
        "import {checkSearchParity} from './scripts/evaluation/k6/comparison_search_parity.js';"
        "const v=JSON.parse(readFileSync(0,'utf8'));"
        "process.stdout.write(JSON.stringify(checkSearchParity(v.cases,v.corpus)));"
    )

    def compare():
        result = subprocess.run(
            ["node", "--input-type=module", "-e", source],
            input=json.dumps({"cases": cases, "corpus": corpus}),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        assert "android smartphone" not in result.stdout
        return json.loads(result.stdout)

    assert compare()["all_equal_and_valid"] is True
    cases[1]["b"]["status"] = 503
    assert compare()["all_equal_and_valid"] is False
    assert checked["deployment_verified"] is False
