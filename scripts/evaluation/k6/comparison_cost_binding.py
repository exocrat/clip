"""Cross-check a declared cost input against a captured run and report offline."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_cost_preview import calculate_cost
from scripts.evaluation.k6.comparison_manifest import TEMPLATE, validate_manifest

MAX_BYTES = 2_000_000


def check_cost_binding(cost: Any, manifest: Any, report_bytes: bytes) -> dict[str, Any]:
    """Match declared run, condition, report digest and measured correct count."""
    calculate_cost(cost)
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    if validate_manifest(manifest, template)["state"] != "captured":
        raise ValueError("captured_manifest_required")
    if cost["run_id"] != manifest["run"]["run_id"]:
        raise ValueError("run_id_mismatch")
    if cost["condition"] != manifest["run"]["condition"]:
        raise ValueError("condition_mismatch")
    if not isinstance(report_bytes, bytes) or len(report_bytes) > MAX_BYTES:
        raise ValueError("invalid_report_bytes")
    digest = hashlib.sha256(report_bytes).hexdigest()
    if digest != manifest["evidence"]["derived_report_sha256"].removeprefix("sha256:"):
        raise ValueError("report_hash_mismatch")
    report = json.loads(report_bytes)
    count = report["client_metrics"][f'{cost["condition"]}_measured']["correct"]
    if type(count) is not int or count < 0 or count != cost["correct_operations"]:
        raise ValueError("correct_count_mismatch")
    return {
        "run_and_condition_match": True,
        "report_hash_matches_manifest": True,
        "measured_correct_count_matches": True,
        "cost_allocation_verified": False,
        "report_content_independently_verified": False,
        "run_validity_verified": False,
        "measurement_authorized": False,
    }


def _read(path: Path) -> bytes:
    """Read a bounded local input without resolving any remote reference."""
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("input_too_large")
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("input_too_large")
    return data


def main() -> None:
    """Print a sanitized consistency result; never start a workload."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("cost_input", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("derived_report", type=Path)
    args = parser.parse_args()
    try:
        result = check_cost_binding(
            json.loads(_read(args.cost_input)),
            json.loads(_read(args.manifest)),
            _read(args.derived_report),
        )
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(2, "Cost input binding failed; no workload was started\n")


if __name__ == "__main__":
    main()
