# Mock-only proxy lifecycle and rollback checks. No AWS calls.
mock_provider "aws" {
  mock_resource "aws_launch_template" {
    defaults = { id = "lt-0123456789abcdef0" }
  }
  mock_resource "aws_autoscaling_group" {
    defaults = { arn = "arn:aws:autoscaling:ap-south-1:335523638354:autoScalingGroup:00000000-0000-0000-0000-000000000000:autoScalingGroupName/synthetic" }
  }
  mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::335523638354:role/synthetic" } }
  mock_resource "aws_cloudwatch_log_group" { defaults = { arn = "arn:aws:logs:ap-south-1:335523638354:log-group:synthetic" } }
  mock_resource "aws_secretsmanager_secret" { defaults = { arn = "arn:aws:secretsmanager:ap-south-1:335523638354:secret:/clip/test/rds-proxy/synthetic-Abc123" } }
  mock_resource "aws_db_proxy" { defaults = { endpoint = "clip-shared-test-pool.proxy-example.ap-south-1.rds.amazonaws.com", arn = "arn:aws:rds:ap-south-1:335523638354:db-proxy:prx-example" } }
}
variables {
  database_proxy_passwords                  = { identity = "synthetic-only", marketplace = "synthetic-only", conversations = "synthetic-only" }
  nfr07_restored_database_url               = "synthetic-only"
  nfr07_restored_identity_database_url      = "synthetic-only"
  nfr07_restored_conversations_database_url = "synthetic-only"
  pgbouncer_tls_bundle                      = "synthetic-tls-only"
  deployment_phase                          = "service"
  cleanup_review_date                       = "2026-10-28"
  vpc_cidr                                  = "10.64.0.0/20"
  public_subnet_cidr                        = "10.64.0.0/24"
  active_private_subnet_cidr                = "10.64.1.0/24"
  secondary_private_subnet_cidr             = "10.64.2.0/24"
  active_availability_zone                  = "ap-south-1a"
  secondary_availability_zone               = "ap-south-1b"
  db_instance_class                         = "db.t4g.micro"
  db_engine_version                         = "18.6"
  db_allocated_storage_gib                  = 20
  db_skip_final_snapshot_on_delete          = true
  db_backup_retention_days                  = 1
  db_master_password                        = "synthetic-test-only-not-a-real-password"
  db_probe_password                         = "synthetic-test-only-not-a-real-password"
  log_retention_days                        = 7
  api_image_uri                             = "335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  postgres_probe_image_uri                  = "docker.io/library/postgres@sha256:0000000000000000000000000000000000000000000000000000000000000000"
}


run "disabled_pool_does_not_change_runtime" {
  command = plan
  assert {
    condition     = length(aws_ecs_service.pgbouncer) == 0 && length(local.pgbouncer_environment) == 0
    error_message = "Default must preserve direct connections."
  }
}
run "separate_pool_without_app_activation" {
  command = apply
  variables {
    identity_runtime_enabled   = true
    identity_test_recipients   = ["synthetic@example.invalid"]
    pgbouncer_enabled          = true
    pgbouncer_private_ip       = "10.64.1.83"
    pgbouncer_host_instance_id = "i-0123456789abcdef0"
    pgbouncer_image_uri        = "335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:1111111111111111111111111111111111111111111111111111111111111111"
    pgbouncer_tls_bundle       = "synthetic-private-tls-fixture"
  }
  assert {
    condition     = aws_ecs_service.pgbouncer[0].desired_count == 1 && length(local.pgbouncer_environment) == 0 && length(aws_db_proxy.shared) == 0
    error_message = "Pool must be separate, and provisioning must not activate routing or RDS Proxy."
  }
  assert {
    condition     = aws_ecs_task_definition.pgbouncer[0].cpu == "1024" && aws_ecs_task_definition.pgbouncer[0].memory == "256" && length(jsondecode(aws_ecs_task_definition.pgbouncer[0].container_definitions)[0].secrets) == 4
    error_message = "Pool resource and secret access bounds changed."
  }
  assert {
    condition     = one(aws_ecs_service.pgbouncer[0].placement_constraints).expression == "ec2InstanceId == i-0123456789abcdef0" && aws_vpc_security_group_ingress_rule.pgbouncer_ecs[0].from_port == 6432
    error_message = "Endpoint must stay on the exact host with private pool port only."
  }
}
run "routing_requires_the_pool" {
  command = plan
  variables { pgbouncer_routing_enabled = true }
  expect_failures = [terraform_data.pgbouncer_inputs]
}
