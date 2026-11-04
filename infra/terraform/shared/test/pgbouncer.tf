# Separate service on an existing, explicitly selected ECS host. This is a
# bounded experiment pool, not host-loss HA. API task-loss leaves it running.
variable "pgbouncer_enabled" {
  type    = bool
  default = false
}
variable "pgbouncer_routing_enabled" {
  type    = bool
  default = false
}
variable "pgbouncer_image_uri" {
  type    = string
  default = null
  validation {
    condition     = var.pgbouncer_image_uri == null ? true : can(regex("^335523638354\\.dkr\\.ecr\\.ap-south-1\\.amazonaws\\.com/clip-shared-test-api@sha256:[0-9a-f]{64}$", var.pgbouncer_image_uri))
    error_message = "Use an immutable digest in the existing project repository."
  }
}
variable "pgbouncer_host_instance_id" {
  type    = string
  default = null
  validation {
    condition     = var.pgbouncer_host_instance_id == null ? true : can(regex("^i-[0-9a-f]{17}$", var.pgbouncer_host_instance_id))
    error_message = "Identify the exact existing host."
  }
}
variable "pgbouncer_private_ip" {
  type    = string
  default = null
  validation {
    condition     = var.pgbouncer_private_ip == null ? true : (can(cidrhost("${var.pgbouncer_private_ip}/32", 0)) && can(regex("^10\\.64\\.1\\.", var.pgbouncer_private_ip)))
    error_message = "Use the selected host's existing workload-subnet IPv4 address."
  }
}
variable "pgbouncer_tls_bundle" {
  type        = string
  default     = null
  sensitive   = true
  ephemeral   = true
  description = "Private JSON certificate/private_key injected into write-only SSM; never saved in a plan or state."
  validation {
    condition     = var.pgbouncer_tls_bundle == null ? !var.pgbouncer_enabled : length(var.pgbouncer_tls_bundle) > 0
    error_message = "An enabled pool requires the privately injected TLS bundle."
  }
}
variable "pgbouncer_tls_version" {
  type    = number
  default = 1
}

locals {
  pgbouncer_active = local.service_enabled && var.pgbouncer_enabled
  pgbouncer_environment = var.pgbouncer_routing_enabled ? [
    { name = "CLIP_DATABASE_PROXY_ENDPOINT", value = var.pgbouncer_private_ip }
  ] : []
  pgbouncer_sources = {
    POOL_IDENTITY_DSN      = "/clip/test/identity/database-url"
    POOL_MARKETPLACE_DSN   = "/clip/test/listings-database-url"
    POOL_CONVERSATIONS_DSN = "/clip/test/conversations/database-url"
  }
}

resource "terraform_data" "pgbouncer_inputs" {
  count = var.pgbouncer_enabled || var.pgbouncer_routing_enabled ? 1 : 0
  lifecycle {
    precondition {
      condition     = local.pgbouncer_active && var.identity_runtime_enabled && !var.database_proxy_enabled && !var.database_proxy_routing_enabled && var.pgbouncer_private_ip != null && var.pgbouncer_host_instance_id != null && var.pgbouncer_image_uri != null
      error_message = "Choose one pool only, on a reviewed existing host, with exact image and endpoint; routing cannot precede provisioning."
    }
  }
}

resource "aws_ssm_parameter" "pgbouncer_tls" {
  count            = local.pgbouncer_active ? 1 : 0
  name             = "/clip/test/pgbouncer/tls"
  type             = "SecureString"
  tier             = "Standard"
  value_wo         = var.pgbouncer_tls_bundle
  value_wo_version = var.pgbouncer_tls_version
  tags             = local.common_tags
}

resource "aws_cloudwatch_log_group" "pgbouncer" {
  count             = local.pgbouncer_active ? 1 : 0
  name              = "/clip/test/pgbouncer"
  retention_in_days = 7
  tags              = local.common_tags
}

resource "aws_iam_role" "pgbouncer_execution" {
  count              = local.pgbouncer_active ? 1 : 0
  name               = "${local.prefix}-pgbouncer-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "pgbouncer_execution" {
  count = local.pgbouncer_active ? 1 : 0
  name  = "exact-image-logs-and-pool-secrets"
  role  = aws_iam_role.pgbouncer_execution[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"], Resource = aws_ecr_repository.api[0].arn },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.pgbouncer[0].arn}:*" },
    { Effect = "Allow", Action = ["ssm:GetParameters"], Resource = concat([for path in values(local.pgbouncer_sources) : "arn:aws:ssm:${local.region}:${local.account_id}:parameter${path}"], [aws_ssm_parameter.pgbouncer_tls[0].arn]) }
  ] })
}

# Existing host SG already has outbound DB access. Only this new private host
# port is added; no public listener, public address or ingress CIDR is introduced.
resource "aws_vpc_security_group_ingress_rule" "pgbouncer_ecs" {
  count                        = local.pgbouncer_active ? 1 : 0
  security_group_id            = aws_security_group.ecs_host[0].id
  referenced_security_group_id = aws_security_group.ecs_host[0].id
  ip_protocol                  = "tcp"
  from_port                    = 6432
  to_port                      = 6432
}
resource "aws_vpc_security_group_ingress_rule" "pgbouncer_lambda" {
  count                        = local.pgbouncer_active && local.exp03_lambda_active ? 1 : 0
  security_group_id            = aws_security_group.ecs_host[0].id
  referenced_security_group_id = aws_security_group.exp03_lambda[0].id
  ip_protocol                  = "tcp"
  from_port                    = 6432
  to_port                      = 6432
}
resource "aws_vpc_security_group_egress_rule" "lambda_pgbouncer" {
  count                        = local.pgbouncer_active && local.exp03_lambda_active ? 1 : 0
  security_group_id            = aws_security_group.exp03_lambda[0].id
  referenced_security_group_id = aws_security_group.ecs_host[0].id
  ip_protocol                  = "tcp"
  from_port                    = 6432
  to_port                      = 6432
}

resource "aws_ecs_task_definition" "pgbouncer" {
  count                    = local.pgbouncer_active ? 1 : 0
  family                   = "clip-test-pgbouncer-ap-south-1-exp03"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "1024"
  memory                   = "256"
  execution_role_arn       = aws_iam_role.pgbouncer_execution[0].arn
  container_definitions = jsonencode([{
    name                   = "pgbouncer"
    image                  = var.pgbouncer_image_uri
    essential              = true
    cpu                    = 1024
    memory                 = 256
    user                   = "10001:10001"
    readonlyRootFilesystem = true
    environment            = [{ name = "POOL_ENDPOINT", value = var.pgbouncer_private_ip }]
    portMappings           = [{ containerPort = 6432, hostPort = 6432, protocol = "tcp" }]
    linuxParameters        = { capabilities = { drop = ["ALL"] }, tmpfs = [{ containerPath = "/run/clip-pool", size = 4, mountOptions = ["rw", "noexec", "nosuid", "nodev", "mode=0700", "uid=10001", "gid=10001"] }] }
    ulimits                = [{ name = "nofile", softLimit = 1024, hardLimit = 1024 }]
    secrets                = concat([for name, path in local.pgbouncer_sources : { name = name, valueFrom = "arn:aws:ssm:${local.region}:${local.account_id}:parameter${path}" }], [{ name = "POOL_TLS_BUNDLE", valueFrom = aws_ssm_parameter.pgbouncer_tls[0].arn }])
    healthCheck            = { command = ["CMD", "python", "-c", "import socket; socket.create_connection(('127.0.0.1',6432),2).close()"], interval = 15, timeout = 3, retries = 3, startPeriod = 10 }
    logConfiguration       = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.pgbouncer[0].name, awslogs-region = local.region, awslogs-stream-prefix = "pool" } }
  }])
  depends_on = [terraform_data.pgbouncer_inputs, aws_iam_role_policy.pgbouncer_execution]
  tags       = local.common_tags
}

resource "aws_ecs_service" "pgbouncer" {
  count                              = local.pgbouncer_active ? 1 : 0
  name                               = "clip-test-pgbouncer-ap-south-1-exp03"
  cluster                            = aws_ecs_cluster.shared[0].id
  task_definition                    = aws_ecs_task_definition.pgbouncer[0].arn
  desired_count                      = 1
  launch_type                        = "EC2"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  placement_constraints {
    type       = "memberOf"
    expression = "ec2InstanceId == ${var.pgbouncer_host_instance_id}"
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  depends_on = [aws_vpc_security_group_ingress_rule.pgbouncer_ecs]
  tags       = local.common_tags
}

output "pgbouncer_endpoint" {
  value = local.pgbouncer_active ? var.pgbouncer_private_ip : null
}
