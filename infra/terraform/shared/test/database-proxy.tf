# Opt-in shared backend pooling. No source DSN, password or database is changed.
# Existing role passwords arrive as ephemeral inputs and enter only write-only
# secret fields. Plans/state retain references and versions, never passwords.
variable "database_proxy_enabled" {
  type        = bool
  default     = false
  description = "Provision the separately approved private RDS Proxy."
}

variable "database_proxy_routing_enabled" {
  type        = bool
  default     = false
  description = "Route both app architectures through the verified proxy; false preserves direct rollback."
}

variable "database_proxy_passwords" {
  type        = map(string)
  default     = null
  sensitive   = true
  ephemeral   = true
  description = "Existing role passwords injected privately from the bound SSM source versions; write-only, never saved in state or plans."
  validation {
    condition     = var.database_proxy_passwords == null ? !var.database_proxy_enabled : (toset(keys(var.database_proxy_passwords)) == toset(["identity", "marketplace", "conversations"]) && alltrue([for value in values(var.database_proxy_passwords) : length(value) > 0]))
    error_message = "Enabled proxy requires the three existing role credentials supplied through ephemeral inputs."
  }
}

variable "database_proxy_credential_version" {
  type        = number
  default     = 1
  description = "Explicit write-only secret version; change only after reviewing source credential rotation."
  validation {
    condition     = var.database_proxy_credential_version >= 1 && floor(var.database_proxy_credential_version) == var.database_proxy_credential_version
    error_message = "Use a positive integral credential version."
  }
}

locals {
  database_proxy_roles = {
    identity      = "clip_test_identity_app"
    marketplace   = "clip_test_marketplace_app"
    conversations = "clip_test_conversations_app"
  }

  database_proxy_active = local.service_enabled && var.database_proxy_enabled
  database_proxy_environment = var.database_proxy_routing_enabled ? [
    { name = "CLIP_DATABASE_PROXY_ENDPOINT", value = try(aws_db_proxy.shared[0].endpoint, "proxy-disabled-invalid") }
  ] : []
}

resource "terraform_data" "database_proxy_inputs" {
  count = var.database_proxy_enabled || var.database_proxy_routing_enabled ? 1 : 0
  lifecycle {
    precondition {
      condition     = local.database_proxy_active && var.identity_runtime_enabled
      error_message = "Proxy provisioning/routing requires the real service and all three approved credential references."
    }
  }
}

resource "aws_secretsmanager_secret" "database_proxy" {
  for_each                = local.database_proxy_active ? local.database_proxy_roles : {}
  name                    = "/clip/test/rds-proxy/${each.key}"
  description             = "Existing CLIP restricted role credentials for the shared private proxy."
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "database_proxy" {
  for_each                 = local.database_proxy_active ? local.database_proxy_roles : {}
  secret_id                = aws_secretsmanager_secret.database_proxy[each.key].id
  secret_string_wo         = jsonencode({ username = each.value, password = var.database_proxy_passwords[each.key] })
  secret_string_wo_version = var.database_proxy_credential_version
}

resource "aws_security_group" "database_proxy" {
  count       = local.database_proxy_active ? 1 : 0
  name        = "${local.prefix}-database-proxy"
  description = "Private shared proxy; only existing app runtimes may connect."
  vpc_id      = aws_vpc.shared[0].id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "database_proxy_ecs" {
  count                        = local.database_proxy_active ? 1 : 0
  security_group_id            = aws_security_group.database_proxy[0].id
  referenced_security_group_id = aws_security_group.ecs_host[0].id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_ingress_rule" "database_proxy_lambda" {
  count                        = local.database_proxy_active && local.exp03_lambda_active ? 1 : 0
  security_group_id            = aws_security_group.database_proxy[0].id
  referenced_security_group_id = aws_security_group.exp03_lambda[0].id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_egress_rule" "database_proxy_database" {
  count                        = local.database_proxy_active ? 1 : 0
  security_group_id            = aws_security_group.database_proxy[0].id
  referenced_security_group_id = aws_security_group.database[0].id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_egress_rule" "lambda_database_proxy" {
  count                        = local.database_proxy_active && local.exp03_lambda_active ? 1 : 0
  security_group_id            = aws_security_group.exp03_lambda[0].id
  referenced_security_group_id = aws_security_group.database_proxy[0].id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_iam_role" "database_proxy" {
  count = local.database_proxy_active ? 1 : 0
  name  = "${local.prefix}-database-proxy"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "rds.amazonaws.com" } }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "database_proxy" {
  count = local.database_proxy_active ? 1 : 0
  name  = "read-exact-proxy-credentials"
  role  = aws_iam_role.database_proxy[0].id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = [for secret in aws_secretsmanager_secret.database_proxy : secret.arn] }]
  })
}

resource "aws_db_proxy" "shared" {
  count                  = local.database_proxy_active ? 1 : 0
  name                   = "${local.prefix}-pool"
  engine_family          = "POSTGRESQL"
  require_tls            = true
  debug_logging          = false
  idle_client_timeout    = 300
  role_arn               = aws_iam_role.database_proxy[0].arn
  vpc_subnet_ids         = [aws_subnet.workload_private[0].id, aws_subnet.rds_secondary_private[0].id]
  vpc_security_group_ids = [aws_security_group.database_proxy[0].id]
  dynamic "auth" {
    for_each = aws_secretsmanager_secret.database_proxy
    content {
      auth_scheme               = "SECRETS"
      iam_auth                  = "DISABLED"
      secret_arn                = auth.value.arn
      client_password_auth_type = "POSTGRES_SCRAM_SHA_256"
    }
  }
  tags       = local.common_tags
  depends_on = [terraform_data.database_proxy_inputs, aws_iam_role_policy.database_proxy, aws_secretsmanager_secret_version.database_proxy]
}

resource "aws_db_proxy_default_target_group" "shared" {
  count         = local.database_proxy_active ? 1 : 0
  db_proxy_name = aws_db_proxy.shared[0].name
  connection_pool_config {
    connection_borrow_timeout    = 1
    max_connections_percent      = 75
    max_idle_connections_percent = 50
    # Clients verify these exact bounded defaults before using a new connection.
    init_query = "SET statement_timeout='5s'; SET lock_timeout='1s'; SET idle_in_transaction_session_timeout='5s'"
  }
}

resource "aws_db_proxy_target" "shared" {
  count                  = local.database_proxy_active ? 1 : 0
  db_instance_identifier = aws_db_instance.shared[0].identifier
  db_proxy_name          = aws_db_proxy.shared[0].name
  target_group_name      = aws_db_proxy_default_target_group.shared[0].name
}

output "database_proxy_endpoint" {
  value = local.database_proxy_active ? aws_db_proxy.shared[0].endpoint : null
}

output "database_proxy_arn" {
  value = local.database_proxy_active ? aws_db_proxy.shared[0].arn : null
}
