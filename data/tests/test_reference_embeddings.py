"""Reject invalid local search evidence; actual inference is checked by the opt-in run."""

import asyncio
from types import SimpleNamespace

import pytest

from scripts.evaluation import reference_local  # establish the actual API import root
from scripts.evaluation.reference_embeddings import ReferenceHelper, search_smoke
from app.domains.listings.embedding_client import HelperUnavailable


class SearchResponses:
    """Script boundary failures only; never stand in for real relevance/model evidence."""

    def __init__(self, failure):
        self.failure = failure

    async def get(self, path, *, params):
        ids = ["available"]
        status = 200
        if params["search_mode"] == "hybrid":
            if self.failure == "hidden":
                ids += ["hidden"]
            elif self.failure == "duplicate":
                ids += ["available"]
            elif self.failure == "missing_keyword":
                ids = []
            elif self.failure == "unavailable":
                status = 503
        return SimpleNamespace(
            status_code=status,
            json=lambda: {"items": [{"listing_id": identifier} for identifier in ids]},
        )


@pytest.mark.parametrize(
    "failure", ["hidden", "duplicate", "missing_keyword", "unavailable"]
)
def test_search_evidence_refuses_visibility_union_and_dependency_failures(failure):
    bundle = {
        "listings": [
            {"id": "available", "availability_scenario": "available"},
            {"id": "hidden", "availability_scenario": "unavailable"},
        ]
    }
    with pytest.raises(ValueError):
        asyncio.run(search_smoke(SearchResponses(failure), bundle))


def test_work_budget_refuses_before_launching_any_helper(tmp_path):
    helper = ReferenceHelper(tmp_path / "python", tmp_path / "model")
    helper.windows_started = 2401
    with pytest.raises(HelperUnavailable, match="reference_window_budget"):
        asyncio.run(helper.encode_query("cycle"))
    assert helper.pid is None and helper.starts == 0
