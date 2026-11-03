"""Exercise fabricated events only; this never opens a browser or sends chat."""

import pytest

from scripts.evaluation.nfr05_events import collect


def event(index, kind, timestamp):
    return {"index": index, "event": kind, "time_ns": timestamp}


def test_events_feed_preview_without_promoting_missing_or_server_receipt():
    events = [event(0, "submitted", 100), event(0, "displayed", 5_000_000_100)]
    events += [event(1, "submitted", 100), event(1, "undisplayed", 6_000_000_100)]
    events += [event(2, "failed", 100), event(3, "submitted", 100)]
    result = collect(events)
    assert result["preview"]["visible_on_time"] == 1
    assert result["preview"]["undisplayed"] == 1
    assert result["preview"]["failed"] == 1
    assert result["preview"]["missing"] == 57
    assert result["preview"]["nfr_accepted"] is False
    with pytest.raises(ValueError):
        collect([event(0, "server_received", 100)])


@pytest.mark.parametrize(
    "events",
    [
        [event(0, "displayed", 2)],
        [event(0, "submitted", 2), event(0, "displayed", 1)],
        [event(0, "submitted", 2), event(0, "undisplayed", 3)],
        [event(0, "submitted", 1), event(0, "submitted", 2)],
        [event(0, "failed", 1), event(0, "failed", 2)],
        [{**event(0, "submitted", 1), "message": "synthetic"}],
    ],
)
def test_invalid_or_private_events_are_refused(events):
    with pytest.raises(ValueError):
        collect(events)
