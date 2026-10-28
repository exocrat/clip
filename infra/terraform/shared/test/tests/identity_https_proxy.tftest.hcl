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

run "disabled_defaults_preserve_no_proxy_or_runtime_command" {
  command = plan
  assert {
    condition     = length(aws_instance.identity_https_proxy) == 0 && length(aws_eip.identity_https_proxy) == 0 && length(aws_security_group.identity_https_proxy) == 0
    error_message = "Default settings must create no proxy ingress resources."
  }
  assert {
    condition     = try(jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].command, null) == null
    error_message = "Disabled Identity must retain the image's default command."
  }
}

run "enabled_proxy_pins_private_peer_and_safe_api_command" {
  command = plan
  variables {
    identity_https_proxy_enabled       = true
    identity_https_proxy_upstream_ipv4 = "10.64.1.130"
    identity_https_proxy_review_date   = "2026-10-28"
    identity_runtime_enabled           = true
    identity_test_recipients           = ["synthetic@example.invalid"]
  }
  assert {
    condition     = !strcontains(aws_iam_role_policy.identity_https_proxy_ssm[0].policy, "ssm:GetParameter") && !strcontains(aws_iam_role_policy.identity_https_proxy_ssm[0].policy, "secretsmanager:") && alltrue([for action in flatten([for statement in jsondecode(aws_iam_role_policy.identity_https_proxy_ssm[0].policy).Statement : statement.Action]) : !strcontains(action, "*")])
    error_message = "The proxy node role must not read application secrets."
  }
  assert {
    condition     = aws_instance.identity_https_proxy[0].private_ip == "10.64.0.10" && aws_instance.identity_https_proxy[0].instance_type == "t3.micro"
    error_message = "Proxy must use the exact private peer and bounded test instance."
  }
  assert {
    condition     = contains(jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].command, "--no-access-log") && contains(jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].command, "10.64.0.10") && !contains(jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].command, "*")
    error_message = "API command must suppress raw access logs and restrict forwarded headers to the exact proxy."
  }
}

run "missing_upstream_and_review_refused" {
  command = plan
  variables {
    identity_https_proxy_enabled = true
  }
  expect_failures = [aws_instance.identity_https_proxy]
}
