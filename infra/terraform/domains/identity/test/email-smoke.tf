# Identity-owned one-shot definition, separate from the shared API service.
# Registration never launches a task. The container defaults to provider disabled;
# one-message approval/recipient overrides belong to a separately approved run.
resource "aws_ecs_task_definition" "email_smoke" {
  count                    = var.email_smoke_task_enabled ? 1 : 0
  family                   = "clip-test-identity-email-ap-south-1-id01"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  task_role_arn            = "arn:aws:iam::335523638354:role/clip-shared-test-api-task"
  execution_role_arn       = "arn:aws:iam::335523638354:role/clip-shared-test-api-execution"
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = file("${path.module}/email-smoke-container.json")
}
output "email_smoke_task_definition_arn" {
  value = var.email_smoke_task_enabled ? aws_ecs_task_definition.email_smoke[0].arn : null
}
