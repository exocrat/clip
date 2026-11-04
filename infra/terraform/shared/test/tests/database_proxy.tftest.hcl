# Mock-only proxy lifecycle and rollback checks. No AWS calls.
mock_provider "aws" {
  mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::335523638354:role/synthetic" } }
  mock_resource "aws_cloudwatch_log_group" { defaults = { arn = "arn:aws:logs:ap-south-1:335523638354:log-group:synthetic" } }
  mock_resource "aws_secretsmanager_secret" { defaults = { arn = "arn:aws:secretsmanager:ap-south-1:335523638354:secret:/clip/test/rds-proxy/synthetic-Abc123" } }
  mock_resource "aws_db_proxy" { defaults = { endpoint = "clip-shared-test-pool.proxy-example.ap-south-1.rds.amazonaws.com", arn = "arn:aws:rds:ap-south-1:335523638354:db-proxy:prx-example" } }
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


run "disabled_preserves_direct_connections" {
  command = plan
  assert {
    condition     = length(aws_db_proxy.shared) == 0 && length(aws_security_group.database_proxy) == 0 && length(local.database_proxy_environment) == 0
    error_message = "Default must add neither proxy resources nor endpoint overrides."
  }
}
run "provision_does_not_switch_existing_app" {
  command = plan
  variables {
    identity_runtime_enabled = true
    identity_test_recipients = ["synthetic@example.invalid"]
    database_proxy_enabled   = true
    database_proxy_passwords = { identity = "synthetic-only", marketplace = "synthetic-only", conversations = "synthetic-only" }
  }
  assert {
    condition     = length(local.database_proxy_environment) == 0 && aws_db_proxy.shared[0].require_tls && !aws_db_proxy.shared[0].debug_logging && length(aws_secretsmanager_secret.database_proxy) == 3
    error_message = "Provisioning must preserve direct routing and private role-separated TLS authentication."
  }
  assert {
    condition     = aws_db_proxy_default_target_group.shared[0].connection_pool_config[0].max_connections_percent == 75 && aws_db_proxy_default_target_group.shared[0].connection_pool_config[0].connection_borrow_timeout == 1
    error_message = "Backend use and queue time must remain bounded."
  }
  assert {
    condition     = length(aws_secretsmanager_secret.database_proxy) == 3 && length(aws_secretsmanager_secret_version.database_proxy) == 3
    error_message = "Proxy IAM must read only the exact three secrets."
  }
}
run "explicit_routing_adds_only_nonsecret_override" {
  command = plan
  variables {
    identity_runtime_enabled       = true
    identity_test_recipients       = ["synthetic@example.invalid"]
    database_proxy_enabled         = true
    database_proxy_routing_enabled = true
    database_proxy_passwords       = { identity = "synthetic-only", marketplace = "synthetic-only", conversations = "synthetic-only" }
  }
  assert {
    condition     = length(local.database_proxy_environment) == 1 && local.database_proxy_environment[0].name == "CLIP_DATABASE_PROXY_ENDPOINT"
    error_message = "Routing must be an explicit removable endpoint override."
  }
}
run "missing_identity_runtime_refused" {
  command = plan
  variables {
    database_proxy_enabled   = true
    database_proxy_passwords = { identity = "synthetic-only", marketplace = "synthetic-only", conversations = "synthetic-only" }
  }
  expect_failures = [terraform_data.database_proxy_inputs]
}
