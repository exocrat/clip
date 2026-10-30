# Local mock plans only: no AWS provider operations, secrets or remote state.
mock_provider "aws" {}

variables {
  deployment_phase                 = "service"
  cleanup_review_date              = "2026-10-28"
  vpc_cidr                         = "10.64.0.0/20"
  public_subnet_cidr               = "10.64.0.0/24"
  active_private_subnet_cidr       = "10.64.1.0/24"
  secondary_private_subnet_cidr    = "10.64.2.0/24"
  active_availability_zone         = "ap-south-1a"
  secondary_availability_zone      = "ap-south-1b"
  db_instance_class                = "db.t4g.micro"
  db_engine_version                = "18.6"
  db_allocated_storage_gib         = 20
  db_skip_final_snapshot_on_delete = true
  db_backup_retention_days         = 1
  db_master_password               = "synthetic-test-only-not-a-real-password"
  db_probe_password                = "synthetic-test-only-not-a-real-password"
  log_retention_days               = 7
  api_image_uri                    = "335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  postgres_probe_image_uri         = "docker.io/library/postgres@sha256:0000000000000000000000000000000000000000000000000000000000000000"
}

run "defaults_add_no_conversations_secret" {
  command = plan
  assert {
    condition     = length(aws_iam_role_policy.api_conversations_secret) == 0 && aws_ecs_task_definition.api[0].memory == "512" && length(aws_cloudwatch_metric_alarm.notification) == 0
    error_message = "Defaults must preserve512MiB, no new secret grant and no notification monitoring."
  }
}
run "explicit_consumers_use_exact_secret_and_bounded_capacity" {
  command = plan
  variables {
    identity_runtime_enabled      = true
    identity_test_recipients      = ["synthetic@example.invalid"]
    conversations_runtime_enabled = true
    notification_worker_enabled   = true
    notification_allow_unlisted_recipients = true
    notification_monitoring_enabled = true
    hybrid_runtime_enabled        = true
    api_task_cpu                  = 512
    api_task_memory_mib           = 2048
  }
  assert {
    condition     = jsondecode(aws_iam_role_policy.api_conversations_secret[0].policy).Statement[0].Resource == "arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/conversations/database-url" && jsondecode(aws_iam_role_policy.api_conversations_secret[0].policy).Statement[0].Action == ["ssm:GetParameters"]
    error_message = "Execution-role access must be exact and read-only."
  }
  assert {
    condition     = length(aws_cloudwatch_log_metric_filter.notification) == 4 && length(aws_cloudwatch_metric_alarm.notification) == 4 && length(aws_cloudwatch_dashboard.notification) == 1 && alltrue([for alarm in aws_cloudwatch_metric_alarm.notification : !alarm.actions_enabled])
    error_message = "Explicit monitoring must use bounded failure metrics and actionless alarms."
  }
  assert {
    condition     = contains([for setting in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : setting.value if setting.name == "CLIP_NOTIFICATION_WORKER_ENABLED"], "true")
    error_message = "Enable the bounded poller explicitly."
  }
  assert {
    condition     = contains([for secret in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].secrets : secret.name], "CLIP_DATABASE_DSN") && aws_ecs_task_definition.api[0].memory == "2048" && aws_ecs_service.api[0].desired_count == 0
    error_message = "Explicit configuration must bind the separate DSN/cap without starting a service."
  }
  assert {
    condition     = alltrue([for setting in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : setting.value == "true" if contains(["CLIP_HYBRID_SEARCH_ENABLED", "CLIP_HYBRID_WORKER_ENABLED"], setting.name)]) && length(aws_instance.identity_https_proxy) == 0
    error_message = "Hybrid flags must be explicit without creating public proxy resources."
  }

}
run "worker_without_conversations_refused" {
  command = plan
  variables {
    identity_runtime_enabled    = true
    identity_test_recipients    = ["synthetic@example.invalid"]
    notification_worker_enabled = true
  }
  expect_failures = [aws_ecs_task_definition.api]
}
run "unlisted_without_worker_refused" {
  command = plan
  variables {
    identity_runtime_enabled               = true
    identity_test_recipients               = ["synthetic@example.invalid"]
    conversations_runtime_enabled          = true
    notification_allow_unlisted_recipients = true
  }
  expect_failures = [aws_ecs_task_definition.api]
}
run "consumer_without_identity_refused" {
  command = plan
  variables { conversations_runtime_enabled = true }
  expect_failures = [aws_ecs_task_definition.api]
}
run "hybrid_default_capacity_refused" {
  command = plan
  variables {
    identity_runtime_enabled = true
    identity_test_recipients = ["synthetic@example.invalid"]
    hybrid_runtime_enabled   = true
  }
  expect_failures = [aws_ecs_task_definition.api]
}
