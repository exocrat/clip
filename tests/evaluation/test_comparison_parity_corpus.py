"""Verify proposed parity inputs offline; no rankings or requests are generated."""

from copy import deepcopy
import json

import pytest

from scripts.evaluation.k6.comparison_parity_corpus import build_parity_corpus
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
