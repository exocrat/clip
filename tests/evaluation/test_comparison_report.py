import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.evaluation.k6.comparison_report import summarize_points


def point(metric, value, **tags):
    return {"type": "Point", "metric": metric, "data": {"value": value, "tags": tags}}


class ComparisonReportTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "conditions": [
                {"name": name, "warmup_rate": 1, "measured_rate": 1}
                for name in ("low", "normal", "burst")
            ],
            "warmup_seconds": 1,
            "measured_seconds": 1,
        }

    def test_counts_routes_outcomes_latency_and_client_throughput(self):
        points = []
        kinds = ["browse", "search", "detail", "browse", "search", "browse"]
        outcomes = ["correct", "throttled", "timeout", "correct", "correct", "correct"]
        phases = [
            f"{name}_{cohort}"
            for name in ("low", "normal", "burst")
            for cohort in ("warmup", "measured")
        ]
        for phase, kind, outcome in zip(phases, kinds, outcomes, strict=True):
            tags = {"phase": phase, "kind": kind, "case_index": "0"}
            points.extend(
                [
                    point("clip_comparison_issued", 1, **tags),
                    point("http_reqs", 1, **tags),
                    point("clip_comparison_outcomes", 1, **tags, outcome=outcome),
                    point("clip_comparison_elapsed_ms", 37, **tags, outcome=outcome),
                ]
            )

        report = summarize_points(points, self.profile)
        low_warmup = report["client_metrics"]["low_warmup"]
        normal_warmup = report["client_metrics"]["normal_warmup"]
        burst_warmup = report["client_metrics"]["burst_warmup"]
        self.assertTrue(low_warmup["accounting_complete"])
        self.assertTrue(low_warmup["delivery_complete"])
        self.assertEqual(low_warmup["offered_rps"], 1)
        self.assertEqual(low_warmup["successful_rps"], 1)
        self.assertTrue(report["accounting_complete"])
        self.assertTrue(report["delivery_complete"])
        self.assertFalse(report["latency_timing_verified"])
        self.assertIn("not a verified monotonic", report["latency_limitation"])
        low_measured = report["client_metrics"]["low_measured"]
        self.assertEqual(low_measured["throttled"], 1)
        self.assertEqual(low_measured["failed"], 1)
        self.assertEqual(low_measured["routes"]["search"]["outcomes"], {"throttled": 1})
        self.assertEqual(normal_warmup["timeouts"], 1)
        self.assertEqual(burst_warmup["correct"], 1)
        self.assertEqual(
            report["infrastructure_metrics"]["status"],
            "not_collected_local_preparation",
        )
        self.assertFalse(report["nfr_accepted"])

    def test_dropped_iterations_are_offered_but_never_delivered(self):
        phase = "burst_measured"
        report = summarize_points(
            [point("dropped_iterations", 1, scenario=phase)], self.profile
        )
        cohort = report["client_metrics"][phase]
        self.assertEqual(cohort["offered_requests"], 1)
        self.assertEqual(cohort["offered_rps"], 1)
        self.assertEqual(cohort["actual_http_requests"], 0)
        self.assertEqual(cohort["schedule_shortfall"], 0)
        self.assertFalse(cohort["delivery_complete"])
        self.assertTrue(cohort["accounting_complete"])
        self.assertFalse(report["delivery_complete"])

    def test_missing_completion_and_inconsistent_outcomes_are_visible(self):
        report = summarize_points(
            [
                point("clip_comparison_issued", 1, phase="low_measured", kind="detail"),
                point("http_reqs", 1, phase="low_measured", kind="detail"),
                point(
                    "clip_comparison_outcomes",
                    1,
                    phase="low_measured",
                    kind="detail",
                    outcome="correct",
                ),
            ],
            self.profile,
        )
        cohort = report["client_metrics"]["low_measured"]
        self.assertEqual(cohort["uncompleted"], 1)
        self.assertFalse(cohort["accounting_complete"])
        self.assertFalse(cohort["outcome_latency_counts_match"])

    def test_clock_anomalies_and_noninteger_counter_values_invalidate_accounting(self):
        report = summarize_points(
            [point("clip_comparison_clock_invalid", 1, phase="low_measured")],
            self.profile,
        )
        self.assertEqual(report["client_metrics"]["low_measured"]["clock_invalid"], 1)
        self.assertFalse(
            report["client_metrics"]["low_measured"]["accounting_complete"]
        )
        with self.assertRaisesRegex(ValueError, "Counter metric must be an integer"):
            summarize_points(
                [point("clip_comparison_issued", 0.5, phase="low_measured")],
                self.profile,
            )

    def test_cli_keeps_raw_immutable_and_refuses_to_replace_derived_report(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.ndjson"
            report_path = Path(directory) / "analysis-v1.json"
            raw_path.write_text(
                json.dumps(point("dropped_iterations", 1, scenario="low_measured"))
                + "\n"
            )
            original_raw = raw_path.read_bytes()
            original_hash = hashlib.sha256(original_raw).hexdigest()
            command = [
                sys.executable,
                "-m",
                "scripts.evaluation.k6.comparison_report",
                str(raw_path),
                "--output",
                str(report_path),
            ]

            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 1)
            self.assertTrue(report_path.exists())
            self.assertEqual(
                hashlib.sha256(raw_path.read_bytes()).hexdigest(), original_hash
            )
            original_report = report_path.read_bytes()

            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(raw_path.read_bytes(), original_raw)
            self.assertEqual(report_path.read_bytes(), original_report)


if __name__ == "__main__":
    unittest.main()
