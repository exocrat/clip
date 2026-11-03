"""Keep the draft bound to the frozen corpus and never invent Hybrid rank."""

from scripts.evaluation.k6.prepare_comparison_corpus import build_corpus


def test_comparison_corpus_is_dataset_bound_and_preserves_unordered_labels():
    corpus = build_corpus()
    cases = corpus["cases"]
    counts = {
        kind: sum(case["request"]["kind"] == kind for case in cases)
        for kind in ("browse", "search", "detail")
    }

    assert corpus["dataset"]["logical_data_fingerprint"].startswith("sha256:")
    assert corpus["dataset"]["data_ready"] is False
    assert corpus["status"] == "draft_search_order_pending"
    assert counts == {"browse": 5, "search": 3, "detail": 2}
    assert all(
        case["expected"] is not None
        for case in cases
        if case["request"]["kind"] in ("browse", "detail")
    )

    search_cases = [case for case in cases if case["request"]["kind"] == "search"]
    assert all(case["expected"] is None for case in search_cases)
    assert {case["relevance_reference"]["query_class"] for case in search_cases} == {
        "direct_word",
        "related_word",
        "meaning_based",
    }
    assert all(
        case["request"]["query"]["search_mode"] == "hybrid" for case in search_cases
    )
    assert all(
        case["relevance_reference"]["relevant_listing_ids"] for case in search_cases
    )
