"""Actual-label adapter refusal and fixed-window eligibility controls; no AWS."""

from uuid import UUID

import pytest

from scripts.evaluation import reference_labels as subject


def test_missing_human_decision_refuses_before_dataset_or_git(monkeypatch):
    def read(path):
        if path.name == "accepted-judgments.json":
            return {"reviewer": "Synthetic control"}
        if path.name == "step-05-label-binding-decisions.json":
            return {
                "source_binding_accepted": False,
                "use_recorded_acceptance_time": True,
            }
        raise AssertionError("Read dataset before human decision guard")

    monkeypatch.setattr(subject.files, "_read_json", read)
    with pytest.raises(ValueError, match="human_label_binding_decisions_required"):
        subject.materialize()


def test_revision_reader_refuses_non_commit_inputs():
    for value in ("main", "HEAD", "a" * 39, "$(anything)"):
        with pytest.raises(ValueError, match="invalid_source_revision"):
            subject.revision_bytes(value, "contracts/search.md")


def sample():
    """Minimal counts-shaped control; no final data/labels or human assertions."""
    users = [
        {
            "id": str(index),
            "account_class": "regular",
            "status": "active",
            "expires_at": None,
            "handle_ready": True,
            "activated_at": "2026-10-01T00:00:00Z",
            "created_at": "2026-10-01T00:00:00Z",
        }
        for index in range(5000)
    ]
    listings = [
        {
            "id": str(UUID(int=index + 1, version=4)),
            "owner_id": str(index),
            "availability": "available",
            "available_from": "2026-10-01T00:00:00Z",
            "available_until": "2026-12-31T00:00:00Z",
        }
        for index in range(1000)
    ]
    for row in listings[800:]:
        row["available_from"] = "2026-12-02T00:00:00Z"
    return {
        "users": users,
        "listings": listings,
        "manifest": {
            "measurement_window": {
                "from": "2026-10-30T01:00:00Z",
                "before": "2026-12-01T00:00:00Z",
            }
        },
    }


def test_future_items_do_not_enter_eligible_scope():
    value = sample()
    eligible = subject.eligible_reference_ids(value)
    assert len(eligible) == 800
    assert UUID(value["listings"][800]["id"]) not in eligible


def test_regular_owner_does_not_require_temporary_activation():
    value = sample()
    for user in value["users"]:
        user["activated_at"] = None
    assert len(subject.eligible_reference_ids(value)) == 800


@pytest.mark.parametrize("change", ["owner", "end", "availability"])
def test_changed_owner_or_window_refuses_final_binding(change):
    value = sample()
    if change == "owner":
        value["users"][0]["status"] = "inactive"
    if change == "end":
        value["listings"][0]["available_until"] = "2026-11-01T00:00:00Z"
    if change == "availability":
        value["listings"][0]["availability"] = "unavailable"
    with pytest.raises(ValueError, match="counts_or_eligibility_changed"):
        subject.eligible_reference_ids(value)
