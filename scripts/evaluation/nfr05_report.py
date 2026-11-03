"""Calculate a preview of NFR-05 outcomes from sanitized local observations.

This does not observe a browser, validate a clock or establish an NFR pass.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SAMPLE_COUNT = 60
DEADLINE_NS = 5_000_000_000
MAX_INPUT_BYTES = 64_000


def summarize(observations: Any) -> dict[str, Any]:
    """Count all planned messages, including missing, late and failed outcomes."""
    if not isinstance(observations, dict) or set(observations) != {"samples"}:
        raise ValueError("invalid_input")
    samples = observations["samples"]
    if not isinstance(samples, list) or len(samples) > SAMPLE_COUNT:
        raise ValueError("invalid_samples")
    seen: set[int] = set()
    counts = {"visible_on_time": 0, "visible_late": 0, "failed": 0, "undisplayed": 0}
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != {
            "index",
            "outcome",
            "submitted_ns",
            "displayed_ns",
        }:
            raise ValueError("invalid_sample")
        index, outcome = sample["index"], sample["outcome"]
        submitted, displayed = sample["submitted_ns"], sample["displayed_ns"]
        if type(index) is not int or index not in range(SAMPLE_COUNT) or index in seen:
            raise ValueError("invalid_index")
        seen.add(index)
        if not (
            (type(submitted) is int and submitted >= 0)
            or (outcome == "failed" and submitted is None)
        ):
            raise ValueError("invalid_submission_time")
        if outcome == "displayed":
            if (
                type(displayed) is not int
                or type(submitted) is not int
                or displayed < submitted
            ):
                raise ValueError("invalid_display_time")
            key = (
                "visible_on_time"
                if displayed - submitted <= DEADLINE_NS
                else "visible_late"
            )
        elif outcome in ("failed", "undisplayed") and displayed is None:
            key = outcome
        else:
            raise ValueError("invalid_outcome")
        counts[key] += 1
    missing = SAMPLE_COUNT - len(seen)
    return {
        "preview_only": True,
        "nfr_accepted": False,
        "observation_and_clock_verified": False,
        "expected": SAMPLE_COUNT,
        "accounted": len(seen),
        "missing": missing,
        **counts,
        "on_time_fraction": counts["visible_on_time"] / SAMPLE_COUNT,
        "threshold_met_if_valid": missing == 0 and counts["visible_on_time"] >= 57,
    }


def main() -> None:
    """Read a bounded local JSON file and print aggregate counts only."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        with args.input.open("rb") as source:
            content = source.read(MAX_INPUT_BYTES + 1)
        if len(content) > MAX_INPUT_BYTES:
            raise ValueError("input_too_large")
        result = summarize(json.loads(content))
    except OSError, UnicodeError, ValueError, TypeError:
        parser.exit(2, "Invalid NFR-05 observations\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
