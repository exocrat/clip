# Local mock plans only: no AWS provider operations, secrets or remote state.
mock_provider "aws" {}

# Give the intended execution role a distinct known plan-time identity so the
# permission assertion detects accidentally targeting the task/proxy role.
override_resource {
  target          = aws_iam_role.api_execution[0]
  override_during = plan
  values = {
    id  = "synthetic-api-execution-role"
    arn = "arn:aws:iam::335523638354:role/synthetic-api-execution-role"
  }
}

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

run "disabled_adds_no_keys_or_permissions" {
  command = plan
  assert {
    condition     = length(aws_iam_role_policy.api_turnstile_secret) == 0 && !contains([for item in jsondecode(aws_ecs_task_definition.api_release[0].container_definitions)[0].environment : item.name], "CLIP_TURNSTILE_SITE_KEY") && !contains([for item in jsondecode(aws_ecs_task_definition.api_release[0].container_definitions)[0].secrets : item.name], "CLIP_TURNSTILE_SECRET_KEY")
    error_message = "Disabled defaults must inject neither key nor new permission."
  }
}

run "enabled_uses_runtime_reference_only" {
  command = plan
  variables {
    identity_runtime_enabled = true
    identity_test_recipients = ["synthetic@example.invalid"]
    turnstile_site_key       = "synthetic-public-widget-key"
  }
  assert {
    condition     = [for item in jsondecode(aws_ecs_task_definition.api_release[0].container_definitions)[0].environment : item.value if item.name == "CLIP_TURNSTILE_SITE_KEY"] == ["synthetic-public-widget-key"]
    error_message = "Public key must be an ECS runtime environment value."
  }
  assert {
    condition     = [for item in jsondecode(aws_ecs_task_definition.api_release[0].container_definitions)[0].secrets : item.valueFrom if item.name == "CLIP_TURNSTILE_SECRET_KEY"] == ["arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/turnstile/secret-key"] && !contains([for item in jsondecode(aws_ecs_task_definition.api_release[0].container_definitions)[0].environment : item.name], "CLIP_TURNSTILE_SECRET_KEY")
    error_message = "Private key must use the exact SSM reference, never plaintext environment."
  }
  assert {
    condition     = jsondecode(aws_iam_role_policy.api_turnstile_secret[0].policy).Statement[0].Action == ["ssm:GetParameters"] && jsondecode(aws_iam_role_policy.api_turnstile_secret[0].policy).Statement[0].Resource == "arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/turnstile/secret-key" && aws_iam_role_policy.api_turnstile_secret[0].role == aws_iam_role.api_execution[0].id
    error_message = "Only the API execution role may read this exact parameter."
  }
}

run "rejects_missing_identity" {
  command = plan
  variables {
    turnstile_site_key = "synthetic-public-widget-key"
  }
  expect_failures = [aws_ecs_task_definition.api_release]
}

run "rejects_empty_key" {
  command = plan
  variables { turnstile_site_key = "" }
  expect_failures = [var.turnstile_site_key]
}
