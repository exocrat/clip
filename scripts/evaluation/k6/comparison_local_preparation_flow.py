"""Connect local preparation components using a fixed synthetic metric only.

This is not an experiment runner: it never reads a session, starts a process,
or sends requests. Its output is explicitly synthetic and cannot authorize runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from scripts.evaluation.k6.comparison_evidence_capture import capture_local_evidence
from scripts.evaluation.k6.comparison_report import summarize_points
from scripts.evaluation.k6.comparison_stage_run import stage_run


def prepare_synthetic_evidence(
    paths: Mapping[str, Path],
    cycle: int,
    run_id: str,
    profile_hash: str,
    source_dir: Path,
    schedule_path: Path,
    module_hashes: Any,
    stage_root: Path,
    capture_root: Path,
    *,
    parity_path: Path,
    parity_evidence_root: Path,
) -> dict[str, Any]:
    """Validate and stage inputs, then capture one fabricated dropped arrival."""
    staged = stage_run(
        paths,
        cycle,
        run_id,
        profile_hash,
        source_dir,
        schedule_path,
        module_hashes,
        stage_root,
        parity_path=parity_path,
        parity_evidence_root=parity_evidence_root,
    )
    condition = staged["condition"]
    schedule = json.loads((stage_root / run_id / "schedule.json").read_bytes())
    point = {
        "type": "Point",
        "metric": "dropped_iterations",
        "data": {
            "value": 1,
            "tags": {"scenario": f"{condition}_measured", "synthetic_fixture": "true"},
        },
    }
    report = summarize_points([point], schedule, condition)
    report["synthetic_fixture"] = True
    raw = (json.dumps(point, sort_keys=True) + "\n").encode()
    report_bytes = (json.dumps(report, sort_keys=True) + "\n").encode()
    capture = capture_local_evidence(capture_root, run_id, raw, report_bytes)
    return {
        "synthetic_fixture": True,
        "measurement_authorized": False,
        "requests_sent": False,
        "staged": staged,
        "capture": capture,
    }
