# Mock-provider plan checks only; never initialize the remote backend or call AWS.
mock_provider "aws" {
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:ap-south-1:335523638354:log-group:synthetic" }
  }
  mock_resource "aws_launch_template" {
    defaults = { id = "lt-0123456789abcdef0" }
  }
  mock_resource "aws_autoscaling_group" {
    defaults = { arn = "arn:aws:autoscaling:ap-south-1:335523638354:autoScalingGroup:00000000-0000-0000-0000-000000000000:autoScalingGroupName/synthetic" }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::335523638354:role/synthetic" }
  }
  mock_resource "aws_lb" {
    defaults = { arn = "arn:aws:elasticloadbalancing:ap-south-1:335523638354:loadbalancer/app/synthetic/50dc6c495c0c9188" }
  }
  mock_resource "aws_lb_listener" {
    defaults = { arn = "arn:aws:elasticloadbalancing:ap-south-1:335523638354:listener/app/synthetic/50dc6c495c0c9188/73e2d6bc24d8a067" }
  }
  mock_resource "aws_lb_target_group" {
    defaults = { arn = "arn:aws:elasticloadbalancing:ap-south-1:335523638354:targetgroup/synthetic/73e2d6bc24d8a067" }
  }
  mock_resource "aws_lambda_function" {
    defaults = { arn = "arn:aws:lambda:ap-south-1:335523638354:function:synthetic" }
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
  # The ECS service's load_balancer collection is provider-computed, so use the
  # mock provider's in-memory apply phase to assert its attached target group.
  command = apply
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
    condition     = length(aws_lb.exp03) == 1 && length(aws_ecs_service.api[0].load_balancer) == 1 && aws_lb_listener.exp03_https[0].default_action[0].target_group_arn == aws_lb_target_group.exp03_ecs[0].arn && length(aws_lb_listener_rule.exp03_selected_reads) == 0
    error_message = "A must send all requests to ECS without a weighted selected-read rule."
  }
  assert {
    condition     = length(aws_security_group.exp03_ecs) == 1 && aws_vpc_security_group_ingress_rule.exp03_alb_https[0].from_port == 443 && aws_vpc_security_group_ingress_rule.exp03_alb_https[0].to_port == 443
    error_message = "Create the separate ECS ingress group and expose only HTTPS."
  }
  assert {
    condition     = length(aws_lambda_function.exp03) == 0 && length(aws_lb_target_group.exp03_lambda) == 0 && length(aws_lambda_permission.exp03_alb) == 0
    error_message = "A must not provision or route to Lambda."
  }
  assert {
    condition     = length(aws_vpc_security_group_egress_rule.exp03_lambda_to_database) == 0 && length(aws_vpc_security_group_egress_rule.exp03_lambda_to_ssm) == 0
    error_message = "A must not create Lambda network access rules."
  }
  assert {
    condition     = contains(jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].command, "10.64.0.0/24,10.64.3.0/24") && aws_vpc_security_group_ingress_rule.exp03_ecs_from_alb[0].from_port == 18000 && aws_vpc_security_group_ingress_rule.exp03_ecs_from_alb[0].to_port == 18000
    error_message = "ECS must trust only the ALB subnets and permit only the ALB API host port."
  }
}

run "b_routes_selected_reads_with_weighted_alb_targets" {
  # The target attachment ID is provider-computed, so keep this entirely in
  # the mock provider's in-memory apply phase for the identity assertion.
  command = apply
  variables {
    exp03_enabled                              = true
    exp03_selected_reads_lambda_weight_percent = 75
    api_service_enabled                        = true
    identity_runtime_enabled                   = true
    identity_test_recipients                   = ["synthetic@example.invalid"]
    hybrid_runtime_enabled                     = true
    api_task_cpu                               = 512
    api_task_memory_mib                        = 2048
  }
  assert {
    condition     = length(aws_lb_listener_rule.exp03_selected_reads) == 1 && length(aws_lb_listener_rule.exp03_selected_reads[0].action[0].forward[0].target_group) == 2
    error_message = "B must have one rule with exactly two weighted targets."
  }
  assert {
    condition = length([
      for target in aws_lb_listener_rule.exp03_selected_reads[0].action[0].forward[0].target_group : target
      if target.arn == aws_lb_target_group.exp03_lambda[0].arn && target.weight == 75
      ]) == 1 && length([
      for target in aws_lb_listener_rule.exp03_selected_reads[0].action[0].forward[0].target_group : target
      if target.arn == aws_lb_target_group.exp03_ecs[0].arn && target.weight == 25
    ]) == 1
    error_message = "B must assign 75 percent to Lambda and 25 percent to ECS."
  }
  assert {
    condition = length([
      for condition in aws_lb_listener_rule.exp03_selected_reads[0].condition : condition
      if length(condition.http_request_method) == 1 && length(condition.http_request_method[0].values) == 1 && contains(condition.http_request_method[0].values, "GET")
    ]) == 1
    error_message = "B's selected route must permit GET only."
  }
  assert {
    condition = length([
      for condition in aws_lb_listener_rule.exp03_selected_reads[0].condition : condition
      if length(condition.path_pattern) == 1 && toset(condition.path_pattern[0].regex_values) == toset(["^/api/listings$", "^/api/listings/[0-9A-Fa-f-]{36}$"])
    ]) == 1
    error_message = "B's selected route must match only Listing collection and detail paths."
  }
  assert {
    condition     = aws_lb_target_group.exp03_lambda[0].target_type == "lambda" && aws_lb_target_group.exp03_lambda[0].lambda_multi_value_headers_enabled && aws_lb_target_group_attachment.exp03_lambda[0].target_id == aws_lambda_function.exp03[0].arn && aws_lambda_permission.exp03_alb[0].principal == "elasticloadbalancing.amazonaws.com" && aws_lambda_permission.exp03_alb[0].source_arn == aws_lb_target_group.exp03_lambda[0].arn
    error_message = "ALB must invoke the registered Lambda target with narrowly scoped permission and multi-value headers."
  }
  assert {
    condition     = length(aws_vpc_security_group_egress_rule.exp03_lambda_to_database) == 1 && length(aws_vpc_security_group_egress_rule.exp03_lambda_to_ssm) == 1 && aws_vpc_security_group_egress_rule.exp03_lambda_to_ssm[0].to_port == 443 && aws_lambda_function.exp03[0].environment[0].variables.CLIP_EMAIL_PROVIDER == "disabled" && aws_lambda_function.exp03[0].environment[0].variables.CLIP_LAMBDA_DATABASE_PARAMETER_ENABLED == "true" && !contains(keys(aws_lambda_function.exp03[0].environment[0].variables), "CLIP_DATABASE_URL")
    error_message = "Lambda must use restricted network access and fixed secret references without email or DB secret environment values."
  }
  assert {
    condition     = !anytrue([for item in jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0].environment : startswith(item.name, "CLIP_EXP03_")])
    error_message = "ECS must not contain configuration for the retired Lambda router."
  }
}

run "b_without_resources_is_rejected" {
  command = plan
  variables { exp03_selected_reads_lambda_weight_percent = 25 }
  expect_failures = [terraform_data.exp03_inputs]
}

run "nfr06_can_plan_two_hybrid_tasks_and_hosts" {
  command = plan
  variables {
    api_service_enabled       = true
    api_service_desired_count = 2
    ecs_host_max_size         = 2
    identity_runtime_enabled  = true
    identity_test_recipients  = ["synthetic@example.invalid"]
    hybrid_runtime_enabled    = true
    api_task_cpu              = 512
    api_task_memory_mib       = 2048
  }
  assert {
    condition     = aws_ecs_service.api[0].desired_count == 2 && aws_autoscaling_group.ecs_host[0].max_size == 2
    error_message = "NFR-06 must be able to declare two Hybrid-capable ECS tasks on separate hosts."
  }
}

run "two_service_tasks_require_two_hosts" {
  command = plan
  variables {
    api_service_enabled       = true
    api_service_desired_count = 2
    ecs_host_max_size         = 1
  }
  expect_failures = [aws_ecs_service.api]
}

run "invalid_alb_weight_is_rejected" {
  command = plan
  variables { exp03_selected_reads_lambda_weight_percent = 101 }
  expect_failures = [var.exp03_selected_reads_lambda_weight_percent]
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
