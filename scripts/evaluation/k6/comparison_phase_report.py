"""Preview paired k6 response phases from an offline synthetic JSON fixture.

This report is not wired to a workload and cannot approve timing or an NFR.
"""

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from scripts.evaluation.k6.comparison_report import OUTCOMES, _quantiles

MAX_BYTES = 2_000_000
FIELDS = ("blocked", "duration", "connecting", "tls_handshaking")


def preview(records: list) -> dict:
    """Summarize same-response phases; never omit suspect correct samples silently."""
    if not isinstance(records, list) or len(records) > 10000:
        raise ValueError("Expected a bounded record array")
    outcomes: Counter = Counter()
    phases: dict[str, list[float]] = {name: [] for name in FIELDS}
    spans: list[float] = []
    anomalies: Counter = Counter()
    for record in records:
        if not isinstance(record, dict) or set(record) != {"outcome", "timings"}:
            raise ValueError("Invalid fixture record")
        outcome = record["outcome"]
        if outcome not in OUTCOMES:
            raise ValueError("Invalid outcome")
        outcomes[outcome] += 1
        if outcome != "correct":
            continue  # failure timing cannot safely be inferred from these phases
        timing = record["timings"]
        if not isinstance(timing, dict) or set(timing) != set(FIELDS):
            anomalies["missing_or_unknown_phase"] += 1
            continue
        if any(
            isinstance(timing[name], bool)
            or not isinstance(timing[name], (int, float))
            or not math.isfinite(timing[name])
            or timing[name] < 0
            for name in FIELDS
        ):
            anomalies["invalid_phase"] += 1
            continue
        total = timing["blocked"] + timing["duration"]
        if not math.isfinite(total) or total > 5000:
            anomalies["over_timeout_warning"] += 1
            continue
        for name in FIELDS:
            phases[name].append(timing[name])
        spans.append(total)

    valid = not anomalies and bool(outcomes["correct"])
    return {
        "preview_only": True,
        "timing_verified": False,
        "nfr_accepted": False,
        "correct_records": outcomes["correct"],
        "failure_outcomes": {
            k: v for k, v in sorted(outcomes.items()) if k != "correct"
        },
        "anomalies": dict(anomalies),
        "percentiles_available": valid,
        "correct_phase_ms": (
            {k: _quantiles(v) for k, v in phases.items()} if valid else None
        ),
        "correct_approximate_span_ms": _quantiles(spans) if valid else None,
        "limitation": "Synthetic preview only; timing and failure boundaries are unverified.",
    }


def main() -> None:
    """Read bounded local JSON and write a new preview without overwriting input."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.fixture.stat().st_size > MAX_BYTES:
            raise ValueError("Fixture too large")
        result = preview(json.loads(args.fixture.read_text()))
        with args.output.open("x") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
    except OSError, ValueError, TypeError, json.JSONDecodeError:
        parser.exit(2, "Could not produce synthetic phase preview\n")


if __name__ == "__main__":
    main()
