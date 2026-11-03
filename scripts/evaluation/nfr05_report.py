"""Calculate a preview of NFR-05 outcomes from sanitized local observations.

This does not observe a browser, validate a clock or establish an NFR pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SAMPLE_COUNT = 60
DEADLINE_NS = 5_000_000_000
MAX_INPUT_BYTES = 64_000
CAPTURE_KEYS = {
    "format_version",
    "nfr_id",
    "run_id",
    "configuration",
    "target_origin",
    "manifest_sha256",
    "action_approval_sha256",
    "target_plan_sha256",
    "application_revision",
    "dataset_fingerprint",
    "live_target_and_participants_preflighted",
    "conversation_id_sha256",
    "background_profile_sha256",
    "background_load",
    "clock",
    "warmup_seconds",
    "measured_seconds",
    "expected_messages",
    "interval_seconds",
    "deadline_seconds",
    "background_load_verified",
    "nfr_accepted",
    "samples",
    "correlation_sha256_by_index",
}


def summarize(observations: Any, background_raw: bytes | None = None) -> dict[str, Any]:
    """Count all planned messages, including missing, late and failed outcomes."""
    if not isinstance(observations, dict):
        raise ValueError("invalid_input")
    capture = None
    background_hash_verified = False
    if set(observations) == CAPTURE_KEYS:
        capture = observations
        if (
            capture["format_version"] != 1
            or capture["nfr_id"] != "nfr-05"
            or not isinstance(capture["run_id"], str)
            or not capture["run_id"]
            or capture["configuration"] not in {"A", "B"}
            or capture["warmup_seconds"] != 60
            or capture["measured_seconds"] != 300
            or capture["expected_messages"] != SAMPLE_COUNT
            or capture["interval_seconds"] != 5
            or capture["deadline_seconds"] != 5
            or type(capture["background_load_verified"]) is not bool
            or capture["nfr_accepted"] is not False
            or not isinstance(capture["target_origin"], str)
            or not isinstance(capture["clock"], str)
            or any(
                not isinstance(capture[key], str)
                or len(capture[key]) != 64
                or any(char not in "0123456789abcdef" for char in capture[key])
                for key in ("conversation_id_sha256", "background_profile_sha256")
            )
            or not isinstance(capture["correlation_sha256_by_index"], list)
            or len(capture["correlation_sha256_by_index"]) != SAMPLE_COUNT
            or capture["live_target_and_participants_preflighted"] is not True
            or any(
                not isinstance(capture[key], str)
                or len(capture[key]) != 64
                or any(char not in "0123456789abcdef" for char in capture[key])
                for key in (
                    "manifest_sha256",
                    "action_approval_sha256",
                    "target_plan_sha256",
                )
            )
            or not isinstance(capture["application_revision"], str)
            or not isinstance(capture["dataset_fingerprint"], str)
        ):
            raise ValueError("invalid_capture_metadata")
        background = capture["background_load"]
        if (
            not isinstance(background, dict)
            or set(background)
            != {
                "run_id",
                "scheduled_requests",
                "issued_requests",
                "http_requests",
                "dropped_iterations",
                "outcomes",
                "accounting_complete",
                "successful_background_load",
                "raw_limit_exceeded",
                "raw_evidence_path",
                "raw_evidence_sha256",
            }
            or not isinstance(background["run_id"], str)
            or not background["run_id"]
            or type(background["scheduled_requests"]) is not int
            or background["scheduled_requests"] != 3000
            or any(
                type(background[key]) is not int or background[key] < 0
                for key in ("issued_requests", "http_requests", "dropped_iterations")
            )
            or not isinstance(background["outcomes"], dict)
            or any(
                not isinstance(key, str) or type(value) is not int or value < 0
                for key, value in background["outcomes"].items()
            )
            or type(background["accounting_complete"]) is not bool
            or type(background["successful_background_load"]) is not bool
            or type(background["raw_limit_exceeded"]) is not bool
            or background["accounting_complete"]
            != (
                not background["raw_limit_exceeded"]
                and background["issued_requests"] == 3000
                and background["issued_requests"]
                == background["http_requests"]
                == sum(background["outcomes"].values())
            )
            or background["successful_background_load"]
            != (
                background["accounting_complete"]
                and background["issued_requests"] == 3000
                and background["dropped_iterations"] == 0
                and not background["raw_limit_exceeded"]
                and background["outcomes"] == {"completed": 3000}
            )
            or background["successful_background_load"]
            != capture["background_load_verified"]
            or not isinstance(background["raw_evidence_path"], str)
            or len(background["raw_evidence_path"]) > 512
            or not isinstance(background["raw_evidence_sha256"], str)
            or len(background["raw_evidence_sha256"]) != 64
            or any(
                char not in "0123456789abcdef"
                for char in background["raw_evidence_sha256"]
            )
        ):
            raise ValueError("invalid_background_load_capture")
        if background_raw is not None:
            if (
                len(background_raw) > 100_000_000
                or hashlib.sha256(background_raw).hexdigest()
                != background["raw_evidence_sha256"]
            ):
                raise ValueError("background_raw_hash_mismatch")
            background_hash_verified = True
        correlations = capture["correlation_sha256_by_index"]
        if any(
            not isinstance(row, dict)
            or set(row) != {"index", "sha256"}
            or type(row["index"]) is not int
            or row["index"] != index
            or not isinstance(row["sha256"], str)
            or len(row["sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in row["sha256"])
            for index, row in enumerate(correlations)
        ):
            raise ValueError("invalid_capture_correlations")
        observations = {"samples": capture["samples"]}
    elif set(observations) != {"samples"}:
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
        "capture_metadata": (
            {
                "run_id": capture["run_id"],
                "configuration": capture["configuration"],
                "target_origin": capture["target_origin"],
                "manifest_sha256": capture["manifest_sha256"],
                "action_approval_sha256": capture["action_approval_sha256"],
                "target_plan_sha256": capture["target_plan_sha256"],
                "application_revision": capture["application_revision"],
                "dataset_fingerprint": capture["dataset_fingerprint"],
                "conversation_id_sha256": capture["conversation_id_sha256"],
                "background_profile_sha256": capture["background_profile_sha256"],
                "background_load_verified": capture["background_load_verified"],
                "background_load_run_id": background["run_id"],
                "background_load_evidence_sha256": background["raw_evidence_sha256"],
                "clock": capture["clock"],
            }
            if capture
            else None
        ),
        "background_evidence_content_hash_verified": background_hash_verified,
        "full_run_validity": bool(
            capture
            and capture["background_load_verified"]
            and background_hash_verified
            and missing == 0
        ),
    }


def main() -> None:
    """Read a bounded local JSON file and print aggregate counts only."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("input", type=Path)
    parser.add_argument("--background-raw", type=Path)
    args = parser.parse_args()
    try:
        with args.input.open("rb") as source:
            content = source.read(MAX_INPUT_BYTES + 1)
        if len(content) > MAX_INPUT_BYTES:
            raise ValueError("input_too_large")
        background_raw = None
        if args.background_raw:
            if args.background_raw.stat().st_size <= 100_000_000:
                background_raw = args.background_raw.read_bytes()
        result = summarize(json.loads(content), background_raw)
    except OSError, UnicodeError, ValueError, TypeError:
        parser.exit(2, "Invalid NFR-05 observations\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
