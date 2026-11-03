# Isolated application checks for a restored database. Opt-in, initially stopped;
# provisioning and later activation each require an exact reviewed Terraform plan.
variable "nfr07_smoke_enabled" {
  type        = bool
  default     = false
  description = "Provision the separately approved isolated restore smoke service at zero tasks."
}
variable "nfr07_smoke_running" {
  type        = bool
  default     = false
  description = "Start one smoke task only after its parameter points to the restored database."
}
variable "nfr07_smoke_hostname" {
  type        = string
  default     = null
  description = "Separately approved DNS host on the experiment ALB, different from the source app."
  validation {
    condition     = var.nfr07_smoke_hostname == null ? true : var.nfr07_smoke_hostname == "restore.clip-iisc.site"
    error_message = "Use the fixed isolated restore.clip-iisc.site hostname."
  }
}
variable "nfr07_smoke_certificate_arn" {
  type        = string
  default     = null
  description = "Existing issued project-account certificate covering the isolated hostname."
  validation {
    condition     = var.nfr07_smoke_certificate_arn == null ? true : can(regex("^arn:aws:acm:ap-south-1:335523638354:certificate/[a-f0-9-]+$", var.nfr07_smoke_certificate_arn))
    error_message = "Use a reviewed certificate in the project account and region."
  }
}
variable "nfr07_restored_database_url" {
  type        = string
  default     = "postgresql://restore-pending.invalid/restore_pending"
  sensitive   = true
  ephemeral   = true
  description = "Securely supplied restored-database URL; write-only in SSM, never saved in Terraform state."
}
variable "nfr07_database_url_version" {
  type        = number
  default     = 1
  description = "Increment when publishing the restored endpoint into the write-only parameter."
}
locals {
  nfr07_active = var.nfr07_smoke_enabled && local.exp03_active
  # Reuse the reviewed application image/configuration, replace every database
  # secret and disable Hybrid/notification writers. The 1-GiB basic smoke task
  # can share a 4-GiB host with a 2-GiB source task, preserving two source tasks.
  # Port 18001 cannot collide with API.
  nfr07_source_container = local.nfr07_active ? jsondecode(aws_ecs_task_definition.api[0].container_definitions)[0] : null
}
resource "aws_ssm_parameter" "nfr07_database" {
  count            = local.nfr07_active ? 1 : 0
  name             = "/clip/test/nfr07/database-url"
  type             = "SecureString"
  value_wo         = var.nfr07_restored_database_url
  value_wo_version = var.nfr07_database_url_version
  tags             = local.exp03_tags
  lifecycle {
    precondition {
      condition     = !var.nfr07_smoke_running || var.nfr07_database_url_version >= 2
      error_message = "Publish the isolated restored-database URL before starting smoke compute."
    }
  }
}
resource "aws_iam_role_policy" "nfr07_execution" {
  count = local.nfr07_active ? 1 : 0
  name  = "clip-test-nfr07-secret"
  role  = aws_iam_role.api_execution[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["ssm:GetParameters"], Resource = [aws_ssm_parameter.nfr07_database[0].arn, aws_ssm_parameter.nfr07_conversations_database[0].arn]
  }] })
}
resource "aws_ecs_task_definition" "nfr07_smoke" {
  count                    = local.nfr07_active ? 1 : 0
  family                   = "clip-test-nfr07-smoke"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.api_execution[0].arn
  task_role_arn            = aws_iam_role.api_task[0].arn
  container_definitions = jsonencode([merge(local.nfr07_source_container, {
    cpu          = 256
    memory       = 1024
    portMappings = [{ containerPort = 8000, hostPort = 18001, protocol = "tcp" }]
    environment = concat([
      for item in local.nfr07_source_container.environment : item
      if !contains(["CLIP_NOTIFICATION_WORKER_ENABLED", "CLIP_HYBRID_WORKER_ENABLED", "CLIP_IDENTITY_BROWSER_ORIGINS", "CLIP_NFR07_RESTORE_SMOKE_ENABLED", "CLIP_HYBRID_SEARCH_ENABLED"], item.name)
      ], [
      { name = "CLIP_NFR07_RESTORE_SMOKE_ENABLED", value = "true" },
      { name = "CLIP_HYBRID_SEARCH_ENABLED", value = "false" },
      { name = "CLIP_NOTIFICATION_WORKER_ENABLED", value = "false" },
      { name = "CLIP_HYBRID_WORKER_ENABLED", value = "false" },
      { name = "CLIP_IDENTITY_BROWSER_ORIGINS", value = jsonencode(["https://${var.nfr07_smoke_hostname}"]) }
    ])
    secrets = [for item in local.nfr07_source_container.secrets : item.name == "CLIP_DATABASE_URL" ? merge(item, { valueFrom = aws_ssm_parameter.nfr07_database[0].arn }) : item.name == "CLIP_DATABASE_DSN" ? merge(item, { valueFrom = aws_ssm_parameter.nfr07_conversations_database[0].arn }) : item]
  })])
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  lifecycle {
    precondition {
      condition     = var.identity_runtime_enabled && var.conversations_runtime_enabled && var.nfr07_smoke_hostname != null && var.nfr07_smoke_certificate_arn != null
      error_message = "Smoke requires the real authenticated app, isolated hostname and reviewed certificate."
    }
  }
  depends_on = [aws_iam_role_policy.nfr07_execution, aws_iam_role_policy.nfr07_identity_secret]
}
resource "aws_lb_target_group" "nfr07_smoke" {
  count       = local.nfr07_active ? 1 : 0
  name        = "${local.exp03_name}-restore"
  port        = 18001
  protocol    = "HTTP"
  target_type = "instance"
  vpc_id      = aws_vpc.shared[0].id
  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
  tags = local.exp03_tags
}
resource "aws_lb_listener_certificate" "nfr07_smoke" {
  count           = local.nfr07_active ? 1 : 0
  listener_arn    = aws_lb_listener.exp03_https[0].arn
  certificate_arn = var.nfr07_smoke_certificate_arn
}
resource "aws_lb_listener_rule" "nfr07_smoke" {
  count        = local.nfr07_active ? 1 : 0
  listener_arn = aws_lb_listener.exp03_https[0].arn
  priority     = 5
  condition {
    host_header { values = [var.nfr07_smoke_hostname] }
  }
  condition {
    path_pattern { values = ["/api/*", "/*"] }
  }
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nfr07_smoke[0].arn
  }
  tags = local.exp03_tags
}
resource "aws_vpc_security_group_egress_rule" "nfr07_alb_to_ecs" {
  count                        = local.nfr07_active ? 1 : 0
  security_group_id            = aws_security_group.exp03_alb[0].id
  referenced_security_group_id = aws_security_group.exp03_ecs[0].id
  ip_protocol                  = "tcp"
  from_port                    = 18001
  to_port                      = 18001
}
resource "aws_vpc_security_group_ingress_rule" "nfr07_ecs_from_alb" {
  count                        = local.nfr07_active ? 1 : 0
  security_group_id            = aws_security_group.exp03_ecs[0].id
  referenced_security_group_id = aws_security_group.exp03_alb[0].id
  ip_protocol                  = "tcp"
  from_port                    = 18001
  to_port                      = 18001
}
resource "aws_ecs_service" "nfr07_smoke" {
  count           = local.nfr07_active ? 1 : 0
  name            = "clip-test-nfr07-smoke"
  cluster         = aws_ecs_cluster.shared[0].id
  task_definition = aws_ecs_task_definition.nfr07_smoke[0].arn
  desired_count   = var.nfr07_smoke_running ? 1 : 0
  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.shared[0].name
    weight            = 1
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.nfr07_smoke[0].arn
    container_name   = "api"
    container_port   = 8000
  }
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  depends_on                         = [aws_lb_listener_rule.nfr07_smoke]
  tags                               = local.exp03_tags
}
output "nfr07_smoke_bindings" {
  description = "Non-secret bindings to freeze in the restore observer manifest before the timed run."
  value = local.nfr07_active ? {
    https_origin                         = "https://${var.nfr07_smoke_hostname}"
    cluster_arn                          = aws_ecs_cluster.shared[0].arn
    service_arn                          = aws_ecs_service.nfr07_smoke[0].id
    task_definition_arn                  = aws_ecs_task_definition.nfr07_smoke[0].arn
    load_balancer_arn                    = aws_lb.exp03[0].arn
    listener_arn                         = aws_lb_listener.exp03_https[0].arn
    listener_rule_arn                    = aws_lb_listener_rule.nfr07_smoke[0].arn
    certificate_arn                      = var.nfr07_smoke_certificate_arn
    target_group_arn                     = aws_lb_target_group.nfr07_smoke[0].arn
    database_parameter_arn               = aws_ssm_parameter.nfr07_database[0].arn
    identity_database_parameter_arn      = aws_ssm_parameter.nfr07_identity_database[0].arn
    conversations_database_parameter_arn = aws_ssm_parameter.nfr07_conversations_database[0].arn
    container_image                      = var.api_image_uri
  } : null
}

# Fail closed when opt-in inputs do not select the real experiment infrastructure.
resource "terraform_data" "nfr07_guard" {
  count = var.nfr07_smoke_enabled || var.nfr07_smoke_running ? 1 : 0
  lifecycle {
    precondition {
      condition     = var.nfr07_smoke_enabled && local.exp03_active && var.exp03_selected_reads_lambda_weight_percent == null
      error_message = "NFR-07 smoke requires explicitly enabled ECS-only EXP-03 infrastructure; remove the isolated smoke resources before switching to weighted B."
    }
  }
}

variable "nfr07_restored_identity_database_url" {
  type        = string
  default     = "postgresql://restore-pending.invalid/restore_pending"
  sensitive   = true
  ephemeral   = true
  description = "Restored Identity DB URL using the preserved Identity role; write-only secret input."
}
variable "nfr07_restored_conversations_database_url" {
  type        = string
  default     = "postgresql://restore-pending.invalid/restore_pending"
  sensitive   = true
  ephemeral   = true
  description = "Restored Conversations DB URL using the preserved Conversations role; write-only secret input."
}
resource "aws_ssm_parameter" "nfr07_identity_database" {
  count            = local.nfr07_active ? 1 : 0
  name             = "/clip/test/nfr07/identity-database-url"
  type             = "SecureString"
  value_wo         = var.nfr07_restored_identity_database_url
  value_wo_version = var.nfr07_database_url_version
  tags             = local.exp03_tags
}
resource "aws_ssm_parameter" "nfr07_conversations_database" {
  count            = local.nfr07_active ? 1 : 0
  name             = "/clip/test/nfr07/conversations-database-url"
  type             = "SecureString"
  value_wo         = var.nfr07_restored_conversations_database_url
  value_wo_version = var.nfr07_database_url_version
  tags             = local.exp03_tags
}
resource "aws_iam_role_policy" "nfr07_identity_secret" {
  count = local.nfr07_active ? 1 : 0
  name  = "clip-test-nfr07-identity-secret"
  role  = aws_iam_role.api_task[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["ssm:GetParameter"], Resource = aws_ssm_parameter.nfr07_identity_database[0].arn
  }] })
}
