# Mock-provider plan checks only; never initialize the remote backend or call AWS.
mock_provider "aws" {
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:ap-south-1:335523638354:log-group:synthetic" }
  }
}

variables {
  deployment_phase                  = "service"
  cleanup_review_date               = "2026-11-05"
  vpc_cidr                          = "10.64.0.0/20"
  public_subnet_cidr                = "10.64.0.0/24"
  active_private_subnet_cidr        = "10.64.1.0/24"
  secondary_private_subnet_cidr     = "10.64.2.0/24"
  active_availability_zone          = "ap-south-1a"
  secondary_availability_zone       = "ap-south-1b"
  db_instance_class                 = "db.t4g.micro"
  db_engine_version                 = "18.6"
  db_allocated_storage_gib          = 20
  db_skip_final_snapshot_on_delete  = true
  db_backup_retention_days          = 1
  db_master_password                = "synthetic-test-only-not-a-real-password"
  db_probe_password                 = "synthetic-test-only-not-a-real-password"
  log_retention_days                = 7
  api_image_uri                     = "335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  postgres_probe_image_uri          = "docker.io/library/postgres@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  exp03_run_id                      = "test001"
  exp03_expiry                      = "2026-11-05"
  exp03_second_public_subnet_cidr   = "10.64.3.0/24"
  exp03_certificate_arn             = "arn:aws:acm:ap-south-1:335523638354:certificate/00000000-0000-0000-0000-000000000000"
  exp03_lambda_image_uri            = "335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-lambda@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  exp03_lambda_memory_mb            = 2048
  exp03_lambda_reserved_concurrency = 2
  exp03_budget_cap_usd              = 10
  exp03_max_runtime_minutes         = 120
}

run "disabled_preserves_shared_service" {
  command = plan
  assert {
    condition     = length(aws_lb.exp03) == 0 && length(aws_lambda_function.exp03) == 0 && length(aws_subnet.exp03_public_secondary) == 0 && length(aws_ecs_service.api[0].load_balancer) == 0
    error_message = "Disabled EXP-03 must add no ingress or Lambda and leave ECS unattached."
  }
}

run "enabled_a_defaults_to_ecs_and_bounds_lambda" {
  command = plan
  variables {
    exp03_enabled            = true
    api_service_enabled      = true
    identity_runtime_enabled = true
    identity_test_recipients = ["synthetic@example.invalid"]
    hybrid_runtime_enabled   = true
    api_task_cpu             = 512
    api_task_memory_mib      = 2048
  }
  assert {
    condition     = length(aws_lb.exp03) == 1 && length(aws_ecs_service.api[0].load_balancer) == 1 && contains([for item in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : item.name], "CLIP_EXP03_OVERFLOW_ENABLED") && [for item in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : item.value if item.name == "CLIP_EXP03_OVERFLOW_ENABLED"][0] == "false"
    error_message = "A must use the ECS default and attach the existing API service."
  }
  assert {
    condition     = length(aws_security_group.exp03_ecs) == 1 && aws_vpc_security_group_ingress_rule.exp03_alb_https[0].from_port == 443 && aws_vpc_security_group_ingress_rule.exp03_alb_https[0].to_port == 443
    error_message = "Create the separate ECS ingress group and expose only HTTPS."
  }
  assert {
    condition     = aws_lambda_function.exp03[0].timeout == 5 && aws_lambda_function.exp03[0].memory_size == 2048 && aws_lambda_function.exp03[0].reserved_concurrent_executions == 2
    error_message = "Lambda limits must use the explicit inputs."
  }
  assert {
    condition     = length(aws_iam_role_policy.exp03_ecs_invoke_lambda) == 0 && length(aws_vpc_security_group_egress_rule.exp03_lambda_to_database) == 1 && length(aws_vpc_security_group_egress_rule.exp03_lambda_to_ssm) == 1 && aws_vpc_security_group_egress_rule.exp03_lambda_to_ssm[0].to_port == 443
    error_message = "A leaves Lambda uninvoked while Lambda egress stays scoped."
  }
  assert {
    condition     = aws_lambda_function.exp03[0].environment[0].variables.CLIP_EMAIL_PROVIDER == "disabled" && aws_lambda_function.exp03[0].environment[0].variables.CLIP_LAMBDA_DATABASE_PARAMETER_ENABLED == "true" && !contains(keys(aws_lambda_function.exp03[0].environment[0].variables), "CLIP_DATABASE_URL")
    error_message = "Lambda must use fixed secret references without email or DB secret environment values."
  }
  assert {
    condition     = contains(jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].command, "10.64.0.0/24,10.64.3.0/24") && aws_vpc_security_group_ingress_rule.exp03_ecs_from_alb[0].from_port == 18000 && aws_vpc_security_group_ingress_rule.exp03_ecs_from_alb[0].to_port == 18000
    error_message = "ECS must trust only the ALB subnets and permit only the ALB API host port."
  }
}

run "b_routes_to_ecs_router_with_lambda_invoke_role" {
  command = plan
  variables {
    exp03_enabled                        = true
    exp03_route_reads_to_lambda          = true
    exp03_router_max_inflight            = 4
    exp03_router_deadline_seconds        = 4
    exp03_invoke_connect_timeout_seconds = 1
    exp03_invoke_read_timeout_seconds    = 3
    exp03_invoke_pool_connections        = 4
    api_service_enabled                  = true
    identity_runtime_enabled             = true
    identity_test_recipients             = ["synthetic@example.invalid"]
    hybrid_runtime_enabled               = true
    api_task_cpu                         = 512
    api_task_memory_mib                  = 2048
  }
  assert {
    condition     = length(aws_ecs_service.api[0].load_balancer) == 1 && aws_ecs_service.api[0].load_balancer[0].target_group_arn == aws_lb_target_group.exp03_ecs[0].arn && [for item in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : item.value if item.name == "CLIP_EXP03_OVERFLOW_ENABLED"][0] == "true" && contains([for item in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : item.name], "CLIP_EXP03_LAMBDA_FUNCTION_ARN") && [for item in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : item.value if item.name == "CLIP_EXP03_ROUTER_MAX_INFLIGHT"][0] == "4" && [for item in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : item.value if item.name == "CLIP_EXP03_LAMBDA_RESERVED_CONCURRENCY"][0] == "2" && jsondecode(aws_iam_role_policy.exp03_ecs_invoke_lambda[0].policy).Statement[0].Action == ["lambda:InvokeFunction"] && jsondecode(aws_iam_role_policy.exp03_ecs_invoke_lambda[0].policy).Statement[0].Resource == aws_lambda_function.exp03[0].arn
    error_message = "ALB routes all traffic to ECS; its task role invokes Lambda for selected reads."
  }
}

run "b_without_resources_is_rejected" {
  command = plan
  variables { exp03_route_reads_to_lambda = true }
  expect_failures = [terraform_data.exp03_inputs]
}

run "b_requires_explicit_router_limits" {
  command = plan
  variables {
    exp03_enabled                        = true
    exp03_route_reads_to_lambda          = true
    exp03_router_max_inflight            = 4
    exp03_router_deadline_seconds        = 4
    exp03_invoke_connect_timeout_seconds = 1
    exp03_invoke_read_timeout_seconds    = null
    exp03_invoke_pool_connections        = 4
    api_service_enabled                  = true
    identity_runtime_enabled             = true
    identity_test_recipients             = ["synthetic@example.invalid"]
    hybrid_runtime_enabled               = true
    api_task_cpu                         = 512
    api_task_memory_mib                  = 2048
  }
  expect_failures = [terraform_data.exp03_inputs]
}

run "stopped_service_is_rejected" {
  command = plan
  variables { exp03_enabled = true }
  expect_failures = [terraform_data.exp03_inputs]
}

run "existing_subnet_is_rejected" {
  command = plan
  variables {
    exp03_enabled                   = true
    exp03_second_public_subnet_cidr = "10.64.2.0/24"
    api_service_enabled             = true
    identity_runtime_enabled        = true
    identity_test_recipients        = ["synthetic@example.invalid"]
    hybrid_runtime_enabled          = true
    api_task_cpu                    = 512
    api_task_memory_mib             = 2048
  }
  expect_failures = [terraform_data.exp03_inputs]
}

run "larger_overlapping_shared_subnet_is_rejected" {
  command = plan
  variables {
    exp03_enabled            = true
    public_subnet_cidr       = "10.64.0.0/23"
    api_service_enabled      = true
    identity_runtime_enabled = true
    identity_test_recipients = ["synthetic@example.invalid"]
    hybrid_runtime_enabled   = true
    api_task_cpu             = 512
    api_task_memory_mib      = 2048
  }
  expect_failures = [terraform_data.exp03_inputs]
}

run "budget_above_user_cap_is_rejected" {
  command = plan
  variables { exp03_budget_cap_usd = 10.01 }
  expect_failures = [var.exp03_budget_cap_usd]
}

run "missing_window_is_rejected" {
  command = plan
  variables {
    exp03_enabled             = true
    exp03_max_runtime_minutes = null
    api_service_enabled       = true
    identity_runtime_enabled  = true
    identity_test_recipients  = ["synthetic@example.invalid"]
    hybrid_runtime_enabled    = true
    api_task_cpu              = 512
    api_task_memory_mib       = 2048
  }
  expect_failures = [terraform_data.exp03_inputs]
}
