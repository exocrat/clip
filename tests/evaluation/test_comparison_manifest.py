import copy
import json
import unittest

from scripts.evaluation.k6.comparison_manifest import TEMPLATE, validate_manifest


class ComparisonManifestTests(unittest.TestCase):
    def setUp(self):
        self.template = json.loads(TEMPLATE.read_text())

    def test_template_is_valid_but_never_authorizes_measurement(self):
        report = validate_manifest(copy.deepcopy(self.template), self.template)
        self.assertEqual(
            report,
            {"valid": True, "state": "template", "measurement_authorized": False},
        )

    def test_template_rejects_run_values_and_extra_fields(self):
        for version in (1, 2):
            value = copy.deepcopy(self.template)
            value["schema_version"] = version
            with self.assertRaisesRegex(ValueError, "Unsupported manifest schema"):
                validate_manifest(value, self.template)
        value = copy.deepcopy(self.template)
        value["run"]["run_id"] = "A-low-r1"
        with self.assertRaisesRegex(
            ValueError, "Template must not contain run-specific"
        ):
            validate_manifest(value, self.template)
        value = copy.deepcopy(self.template)
        value["credential"] = "never"
        with self.assertRaisesRegex(ValueError, "Unexpected object shape"):
            validate_manifest(value, self.template)

    def test_template_rejects_sensitive_values_and_changes_to_approved_protocol(self):
        value = copy.deepcopy(self.template)
        value["target"]["entrypoint_reference"] = "Bearer abc123"
        with self.assertRaisesRegex(ValueError, "Sensitive value pattern"):
            validate_manifest(value, self.template)
        value = copy.deepcopy(self.template)
        value["target"][
            "entrypoint_reference"
        ] = "https://example.test/path?X-Amz-Signature=abc"
        with self.assertRaisesRegex(ValueError, "Sensitive value pattern"):
            validate_manifest(value, self.template)
        value = copy.deepcopy(self.template)
        value["workload"]["request_mix_per_ten"]["search"] = 4
        with self.assertRaisesRegex(ValueError, "Workload mix differs"):
            validate_manifest(value, self.template)
        value = copy.deepcopy(self.template)
        value["workload"]["rotation_rule"] = "different"
        with self.assertRaisesRegex(ValueError, "rotation rule differs"):
            validate_manifest(value, self.template)
        value = copy.deepcopy(self.template)
        value["workload"]["rotation_seed"] = 1
        with self.assertRaisesRegex(ValueError, "run-specific workload"):
            validate_manifest(value, self.template)

    def test_captured_record_checks_revision_data_telemetry_cost_and_run_evidence(self):
        value = copy.deepcopy(self.template)
        value["manifest_state"] = "captured"
        value["run"] = {
            "run_id": "A-low-r1",
            "configuration": "A",
            "condition": "low",
            "repetition": 1,
            "owner_role": "experiment operator D",
            "planned_start_utc": "2026-11-01T10:00:00Z",
            "actual_start_utc": "2026-11-01T10:00:01Z",
            "actual_end_utc": "2026-11-01T10:06:00Z",
        }
        value["target"] = {
            "account_id": "123456789012",
            "role_arn": "arn:aws:iam::123456789012:role/read-only",
            "region": "ap-south-1",
            "environment_id": "test-evaluation",
            "entrypoint_reference": "approved-target-record",
            "resource_ids": ["ecs-service-1", "db-instance-1"],
            "resource_configuration_sha256": "a" * 64,
        }
        value["revisions"] = {
            "application_revision": "a" * 40,
            "image_digest": "sha256:" + "b" * 64,
            "frontend_revision": "c" * 40,
            "migration_head": "20261101010000",
            "api_contract_sha256": "d" * 64,
        }
        value["dataset"] = {
            "seed": 42,
            "user_count": 5000,
            "listing_count": 1000,
            "logical_fingerprint": "sha256:" + "e" * 64,
            "index_fingerprint": "index-fingerprint-v1",
            "database_settings_sha256": "f" * 64,
        }
        value["workload"].update(
            {
                "profile_sha256": "1" * 64,
                "execution_profile_reference": "profiles/cycle-1.json",
                "execution_profile_sha256": "f" * 64,
                "case_corpus_path": "data/evaluation/workloads/cases.json",
                "case_corpus_sha256": "2" * 64,
                "generator_version": "k6 v2.3.0",
                "load_script_sha256": "3" * 64,
                "run_command_reference": "docs/evaluation/experiment/A-low-r1/command.md",
                "rotation_seed": 2,
                "sequence_start": 2,
            }
        )
        value["resource_telemetry"] = {
            "ecs_artifact_reference": "telemetry/ecs.json",
            "ecs_artifact_sha256": "6" * 64,
            "lambda_artifact_reference": "telemetry/lambda.json",
            "lambda_artifact_sha256": "7" * 64,
            "postgres_artifact_reference": "telemetry/postgres.json",
            "postgres_artifact_sha256": "8" * 64,
            "generator_artifact_reference": "telemetry/generator.json",
            "generator_artifact_sha256": "9" * 64,
        }
        value["cost_inputs"].update(
            {
                "source_reference": "cost/actual-cost.json",
                "source_sha256": "a" * 64,
                "interval_start_utc": "2026-11-01T10:00:00Z",
                "interval_end_utc": "2026-11-01T11:00:00Z",
                "amount_before_credits": 1.25,
                "billing_delay_note": "Provider billing data may be delayed.",
            }
        )
        value["evidence"] = {
            "raw_output_reference": "raw/run.ndjson",
            "raw_output_sha256": "4" * 64,
            "derived_report_reference": "reports/run.json",
            "derived_report_sha256": "5" * 64,
            "approval_record_reference": "approval/record.md",
            "cleanup_record_reference": "cleanup/record.md",
        }
        report = validate_manifest(value, self.template)
        self.assertEqual(
            report,
            {"valid": True, "state": "captured", "measurement_authorized": False},
        )
        value["workload"]["execution_profile_reference"] = None
        with self.assertRaisesRegex(ValueError, "empty value"):
            validate_manifest(value, self.template)
        value["workload"]["execution_profile_reference"] = "profiles/cycle-1.json"
        value["workload"]["execution_profile_sha256"] = "invalid"
        with self.assertRaisesRegex(ValueError, "Invalid SHA-256"):
            validate_manifest(value, self.template)
        value["workload"]["execution_profile_sha256"] = "f" * 64
        value["workload"]["rotation_seed"] = 3
        with self.assertRaisesRegex(ValueError, "does not match the rotation seed"):
            validate_manifest(value, self.template)
        value["workload"]["rotation_seed"] = 2
        value["evidence"]["derived_report_reference"] = value["evidence"][
            "raw_output_reference"
        ]
        with self.assertRaisesRegex(ValueError, "separate references"):
            validate_manifest(value, self.template)
        value["evidence"]["derived_report_reference"] = "reports/run.json"
        value["dataset"]["listing_count"] = 999
        with self.assertRaisesRegex(ValueError, "reference workload size"):
            validate_manifest(value, self.template)


if __name__ == "__main__":
    unittest.main()
