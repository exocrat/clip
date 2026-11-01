"""Local k6 accounting/caps/installer metadata tests; no binary download or network."""

import json
from pathlib import Path
import struct
from unittest.mock import patch

import pytest

from scripts.evaluation.k6.install import minimum_macos, ROOT
from scripts.evaluation.k6.runner import cohort, summarize, quantile, execute


def point(metric, value, *, phase="measured", outcome=None):
    tags = {"scenario": phase}
    if metric.startswith("clip_"):
        tags.update(phase=phase, case_id="controlled")
    if outcome is not None:
        tags["outcome"] = outcome
    return {"type": "Point", "metric": metric, "data": {"value": value, "tags": tags}}


def samples(*outcomes):
    result = []
    for index, outcome in enumerate(outcomes):
        result.extend(
            [
                point("clip_issued", 1),
                point("http_reqs", 1),
                point("clip_elapsed_ms", 100 + index * 100, outcome=outcome),
            ]
        )
    return result


def test_r7_quantiles_use_actual_samples_and_empty_is_not_zero_latency():
    assert quantile([], 0.95) is None
    assert quantile([1, 2, 3, 4], 0.5) == 2.5
    assert quantile([1, 2, 3, 4], 0.95) == pytest.approx(3.85)


def test_correct_200_shape_is_not_inferred_from_status_and_denominators_remain_visible():
    result = cohort(
        samples("ok", "invalid", "unauthorized", "timeout"), "measured", 4, 2
    )
    assert result["issued"] == result["actual_http_requests"] == 4
    assert result["outcomes"] == {
        "ok": 1,
        "invalid": 1,
        "unauthorized": 1,
        "timeout": 1,
    }
    assert result["successful_latency"]["samples"] == 1
    assert result["all_completed_latency"]["samples"] == 4
    assert result["within_1s_fraction_of_issued"] == 0.25
    assert result["within_1s_fraction_of_correct"] == 1.0
    assert not result["valid"]


def test_browse_and_search_denominators_differ_and_boundary_is_inclusive():
    points = samples("ok", "ok", "timeout")
    elapsed = [p for p in points if p["metric"] == "clip_elapsed_ms"]
    elapsed[0]["data"]["value"] = 1000
    elapsed[1]["data"]["value"] = 1001
    result = cohort(points, "measured", 3, 1)
    assert result["expected_result_within_1s"] == 1
    assert result["within_1s_fraction_of_correct"] == 0.5
    assert result["within_1s_fraction_of_issued"] == pytest.approx(1 / 3)
    assert result["outcomes"]["timeout"] == 1
    assert not result["valid"]


def test_empty_success_and_missing_outcome_do_not_appear_as_a_pass():
    result = cohort(samples("timeout"), "measured", 1, 1)
    assert result["within_1s_fraction_of_correct"] is None
    assert result["within_1s_fraction_of_issued"] == 0
    missing = cohort([point("clip_issued", 1), point("http_reqs", 1)], "measured", 1, 1)
    assert missing["uncompleted"] == 1
    assert not missing["valid"]


def test_generator_shortfall_cannot_be_hidden_by_perfect_returned_requests():
    result = cohort(
        samples("ok", "ok") + [point("dropped_iterations", 2)], "measured", 4, 2
    )
    assert result["generator_drops"] == result["generator_shortfall"] == 2
    assert result["issued_rps"] == result["successful_rps"] == 1
    assert result["offered_rps"] == 2
    assert not result["valid"]


def test_interrupted_requests_and_boundary_iterations_are_not_extra_successes():
    result = cohort(
        samples("ok") + [point("clip_issued", 1), point("clip_outside_cohort", 1)],
        "measured",
        2,
        1,
    )
    assert result["uncompleted"] == 1
    assert result["boundary_iterations_without_http"] == 1
    assert not result["valid"]
    valid = cohort(
        samples("ok", "ok") + [point("clip_outside_cohort", 1)], "measured", 2, 1
    )
    assert valid["valid"] and valid["actual_http_requests"] == 2


def test_warmup_is_not_mixed_with_measured_latency_and_completion_required(tmp_path):
    profile = {
        "id": "controlled",
        "rate": 2,
        "warmup_seconds": 1,
        "measured_seconds": 1,
    }
    points = samples("ok", "ok") + [
        point("clip_issued", 1, phase="warmup"),
        point("http_reqs", 1, phase="warmup"),
        point("clip_elapsed_ms", 9000, phase="warmup", outcome="timeout"),
    ]
    raw = tmp_path / "raw.ndjson"
    raw.write_text("\n".join(json.dumps(p) for p in points))
    result = summarize(raw, profile, True, 0)
    assert result["measured"]["all_completed_latency"]["p95_ms"] == 195
    assert result["warmup"]["outcomes"]["timeout"] == 1
    assert not result["valid_preparation_run"] and not result["nfr_accepted"]
    assert result["latency_timing_verified"] is False
    assert not summarize(raw, profile, False, 0)["valid_preparation_run"]


def test_missing_metric_file_and_clock_anomaly_are_invalid(tmp_path):
    profile = {
        "id": "controlled",
        "rate": 1,
        "warmup_seconds": 0,
        "measured_seconds": 1,
    }
    assert not summarize(tmp_path / "missing", profile, False, 1)[
        "valid_preparation_run"
    ]
    assert not cohort(
        samples("ok") + [point("clip_clock_invalid", 1)], "measured", 1, 1
    )["valid"]


@pytest.mark.parametrize("value", [float("nan"), -1, float("inf")])
def test_nonfinite_or_negative_metrics_refused(value):
    with pytest.raises(ValueError):
        cohort([point("clip_elapsed_ms", value, outcome="ok")], "measured", 1, 1)


def test_future_full_rate_profiles_cannot_execute_even_on_loopback(tmp_path):
    path = ROOT / "data/evaluation/workloads/browse-nfr-draft-v1.json"
    with pytest.raises(ValueError):
        execute(path, 8000, tmp_path / "unused", target_kind="native")


def test_output_traversal_is_refused_before_binary_or_process(tmp_path):
    profile = ROOT / "data/evaluation/workloads/local-search-pilot-v1.json"
    with patch("subprocess.run") as run:
        with pytest.raises(ValueError):
            execute(
                profile, 8000, ROOT / ".tools/../outside-test-run", target_kind="native"
            )
        run.assert_not_called()


def test_macho_compatibility_checked_without_running_code():
    header = struct.pack("<8I", 0xFEEDFACF, 0x0100000C, 0, 2, 1, 24, 0, 0)
    command = struct.pack("<6I", 0x32, 24, 1, 12 << 16, 0, 0)
    assert minimum_macos(header + command) == (12, 0, 0)
    with pytest.raises(ValueError):
        minimum_macos(struct.pack("<8I", 0xFEEDFACF, 7, 0, 2, 1, 24, 0, 0) + command)


def test_node_workload_and_response_contract_checks():
    """Run pure k6-shared JS tests in the existing pinned Node toolchain (also in CI)."""
    import shutil
    import subprocess

    local = ROOT / ".tools/node/bin/node"
    node = str(local) if local.is_file() else shutil.which("node")
    assert node is not None, "Existing project Node toolchain is required"
    result = subprocess.run(
        [node, "--test", "scripts/evaluation/k6/core.test.mjs"],
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
