"""Synthetic evaluator checks; no fixture represents actual human review."""

from copy import deepcopy
import json
from uuid import UUID

import pytest

from scripts.evaluation import search as evaluator
from data.generators.preview import stable_id


def identifier(index):
    """Produce stable canonical IDs without borrowing real listing identities."""
    return UUID(stable_id(92001, "listing_placeholder", index))


@pytest.fixture
def reviewed(tmp_path, monkeypatch):
    """Build an explicitly synthetic trusted-adapter output for validation tests."""
    monkeypatch.setattr(evaluator, "ROOT", tmp_path)
    manifest = tmp_path / "data/runs/unit/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")
    listing = identifier(100)
    queries = [identifier(index) for index in range(1, 21)]
    binding = evaluator.DatasetBinding(
        "sha256:" + "a" * 64,
        "data/runs/unit/manifest.json",
        "unit-schema",
        "b" * 40,
        "c" * 40,
        frozenset({listing}),
        {query: frozenset({listing}) for query in queries},
        preview_only=False,
    )
    document = {
        "format_version": "1",
        "status": "reviewed",
        "dataset": {
            name: getattr(binding, name)
            for name in (
                "logical_data_fingerprint",
                "manifest_path",
                "schema_version",
                "source_revision",
            )
        },
        "search_contract_revision": binding.search_contract_revision,
        "review": {
            "reviewer": "Synthetic unit fixture, no actual human review",
            "reviewed_at": "2026-10-24T00:00:00.000000Z",
            "inclusion_policy": "Synthetic validator cases only",
        },
        "queries": [
            {
                "query_id": str(query),
                "query_text": "bicycle",
                "context": {},
                "relevant_listing_ids": [str(listing)],
                "include_in_nfr04": True,
                "exclusion_reason": None,
            }
            for query in queries
        ],
    }
    return document, binding


def test_reviewed_binding_and_draft():
    """The real empty template validates without becoming a scoring input."""
    document = json.loads(
        (evaluator.ROOT / "data/evaluation/query-labels.template.json").read_text()
    )
    assert evaluator.validate_labels(document) == ()
    assert not (evaluator.ROOT / "data/evaluation/query-labels.json").exists()


def test_synthetic_review_requires_trusted_binding(reviewed):
    document, binding = reviewed
    assert len(evaluator.validate_labels(document, binding)) == 20
    with pytest.raises(evaluator.EvaluationError, match="binding_required"):
        evaluator.validate_labels(document)
    document["queries"].pop()
    with pytest.raises(evaluator.EvaluationError, match="twenty_included"):
        evaluator.validate_labels(document, binding)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(extra=True),
        lambda d: d["dataset"].update(logical_data_fingerprint="sha256:wrong"),
        lambda d: d["dataset"].update(source_revision="d" * 40),
        lambda d: d["review"].update(reviewed_at="2026-10-24T00:00:00Z"),
        lambda d: d["dataset"].update(manifest_path="data/runs/../private.json"),
        lambda d: d["queries"].append(deepcopy(d["queries"][0])),
        lambda d: d["queries"][0].update(relevant_listing_ids=None),
        lambda d: d["queries"][0].update(relevant_listing_ids=[str(identifier(999))]),
        lambda d: d["queries"][0]["relevant_listing_ids"].append(
            d["queries"][0]["relevant_listing_ids"][0]
        ),
        lambda d: d["queries"][0].update(include_in_nfr04=False),
        lambda d: d["queries"][0].update(include_in_nfr04=1),
        lambda d: d["queries"][0].update(query_id="invalid"),
        lambda d: d["queries"][0].update(context={"actor_id": "private"}),
        lambda d: d["queries"][0].update(context={"page": 2}),
        lambda d: d["queries"][0].update(context={"min_price_paise": 1.2}),
        lambda d: d["queries"][0].update(context={"negotiable": 1}),
        lambda d: d["queries"][0].update(
            context={"min_price_paise": 2, "max_price_paise": 1}
        ),
        lambda d: d["queries"][0].update(context={"q": "desk"}),
    ],
)
def test_malformed_review_cannot_score(reviewed, mutation):
    """Reject schema, provenance, inclusion and context corruption before scoring."""
    document, binding = reviewed
    mutation(document)
    with pytest.raises(evaluator.EvaluationError):
        evaluator.validate_labels(document, binding)


def test_missing_manifest_and_ineligible_reference(reviewed):
    document, binding = reviewed
    (evaluator.ROOT / binding.manifest_path).unlink()
    with pytest.raises(evaluator.EvaluationError, match="referenced_file_missing"):
        evaluator.validate_labels(document, binding)


@pytest.mark.parametrize("hits", [15, 16, 20])
def test_threshold_and_permanent_preview_status(hits):
    """The 80% boundary never grants NFR acceptance, even with perfect fixtures."""
    listing = identifier(100)
    cases = tuple(
        evaluator.EvaluationCase(identifier(i), frozenset({listing}), True)
        for i in range(1, 21)
    )
    results = {
        case.query_id: evaluator.Retrieval((listing,) if i < hits else ())
        for i, case in enumerate(cases)
    }
    report = evaluator.score_preview(cases, results, frozenset({listing}))
    assert report["success_at_5"] == hits / 20
    assert report["fixture_target_met"] == (hits >= 16)
    assert report["preview_only"] and not report["nfr04_accepted"]
    assert not report["human_review_verified"]


@pytest.mark.parametrize("status", ["timeout", "error", "unauthorized"])
def test_failed_and_missing_queries_stay_in_denominator(status):
    listing = identifier(100)
    cases = tuple(
        evaluator.EvaluationCase(identifier(i), frozenset({listing}), True)
        for i in range(1, 4)
    )
    report = evaluator.score_preview(
        cases,
        {
            cases[0].query_id: evaluator.Retrieval((listing,)),
            cases[1].query_id: evaluator.Retrieval(status=status),
        },
        frozenset({listing}),
    )
    assert report["included_queries"] == 3 and report["hits_at_5"] == 1
    assert report["retrieval_failures"] == 2


def test_rank_six_empty_labels_and_explicit_exclusion():
    assert evaluator.self_check()["success_at_5"] == 0.25
    ids = tuple(identifier(i) for i in range(100, 106))
    case = evaluator.EvaluationCase(identifier(1), frozenset({ids[4]}), True)
    assert (
        evaluator.score_preview(
            (case,), {case.query_id: evaluator.Retrieval(ids)}, frozenset(ids)
        )["hits_at_5"]
        == 1
    )


@pytest.mark.parametrize(
    "ids",
    [(identifier(100), identifier(100)), (identifier(999),), (identifier(100),) * 101],
)
def test_invalid_results_are_visible_failures(ids):
    case = evaluator.EvaluationCase(identifier(1), frozenset({identifier(100)}), True)
    report = evaluator.score_preview(
        (case,), {case.query_id: evaluator.Retrieval(ids)}, frozenset({identifier(100)})
    )
    assert report["retrieval_failures"] == 1 and report["hits_at_5"] == 0
    assert report["queries"][0]["outcome"] == "invalid"


def test_cli_reports_no_acceptance(capsys):
    assert evaluator.main(["validate-labels"]) == 0
    assert json.loads(capsys.readouterr().out)["scoring_allowed"] is False
    assert evaluator.main(["self-check"]) == 0
    assert json.loads(capsys.readouterr().out)["nfr04_accepted"] is False
    assert evaluator.main(["validate-labels", "--labels", "../private.json"]) == 2
    assert "private.json" not in capsys.readouterr().out


def test_binding_preview_and_context_eligibility(reviewed):
    """A trusted shape alone cannot override preview status or eligible IDs."""
    from dataclasses import replace

    document, binding = reviewed
    with pytest.raises(evaluator.EvaluationError, match="binding_required"):
        evaluator.validate_labels(document, replace(binding, preview_only=True))
    with pytest.raises(evaluator.EvaluationError, match="not_eligible"):
        evaluator.validate_labels(document, replace(binding, eligible_ids={}))


def test_symlink_reference_refused(reviewed, tmp_path):
    document, binding = reviewed
    target = tmp_path / binding.manifest_path
    target.unlink()
    other = tmp_path / "other.json"
    other.write_text("{}")
    target.symlink_to(other)
    with pytest.raises(evaluator.EvaluationError, match="unsafe_reference"):
        evaluator.validate_labels(document, binding)


def test_draft_cannot_contain_judgments(reviewed):
    document, _ = reviewed
    document["status"] = "draft"
    document["dataset"] = dict.fromkeys(document["dataset"])
    document["review"] = dict.fromkeys(document["review"])
    document["search_contract_revision"] = None
    with pytest.raises(evaluator.EvaluationError, match="draft_judgments"):
        evaluator.validate_labels(document)


@pytest.mark.parametrize("length", [1, 120, 121])
def test_context_query_trim_matches_public_http_limit(length):
    """Padding is ignored before the bound; genuine excess text stays invalid."""
    from app.domains.listings.browse_validation import BrowseQuery
    from pydantic import ValidationError

    text = "x" * length
    context = {"q": " \t" + text + " \n"}
    original = dict(context)
    if length <= 120:
        assert BrowseQuery.model_validate(context).q == text
        evaluator._context(context, text)
    else:
        with pytest.raises(ValidationError):
            BrowseQuery.model_validate(context)
        with pytest.raises(evaluator.EvaluationError, match="invalid_context"):
            evaluator._context(context, text)
    assert context == original
