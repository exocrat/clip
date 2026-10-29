# ID-01 Step14 local preparation only. No role/password/parameter is provisioned
# here: owner-reviewed SQL and exact secret creation precede any enabled apply.
variable "conversations_runtime_enabled" {
  description = "Inject the separately reviewed Conversations DSN; disabled by default."
  type        = bool
  default     = false
}

variable "notification_worker_enabled" {
  description = "Enable the bounded notification poller in the controlled Identity and Conversations test runtime."
  type        = bool
  default     = false
}

variable "hybrid_runtime_enabled" {
  description = "Explicitly enable the reviewed AMD64 Hybrid image helper/worker; pipeline activation stays separate."
  type        = bool
  default     = false
}

variable "api_task_cpu" {
  description = "Reviewed single API task CPU units; sizing is not performance acceptance."
  type        = number
  default     = 256
  validation {
    condition     = contains([256, 512, 1024], var.api_task_cpu)
    error_message = "Use a reviewed bounded CPU choice:256,512,1024."
  }
}

variable "api_task_memory_mib" {
  description = "Reviewed API task/container memory cap; combined Hybrid requires at least2048MiB."
  type        = number
  default     = 512
  validation {
    condition     = contains([512, 1024, 2048, 4096], var.api_task_memory_mib)
    error_message = "Use a reviewed bounded memory choice:512,1024,2048,4096MiB."
  }
}

# ECS injects this one exact SecureString through its execution role, not the
# application task role. Neither wildcard reads nor secret values enter HCL.
resource "aws_iam_role_policy" "api_conversations_secret" {
  count = local.service_enabled && var.conversations_runtime_enabled ? 1 : 0
  name  = "${local.prefix}-api-conversations-secret"
  role  = aws_iam_role.api_execution[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameters"]
      Resource = "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/conversations/database-url"
    }]
  })
}
