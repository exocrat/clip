# EXP-03 is opt-in; writing this file does not authorize a plan or apply.
# Use the existing shared VPC, service and database; never recreate their data.
variable "exp03_enabled" {
  description = "Enable the separately reviewed temporary ECS/Lambda comparison resources."
  type        = bool
  default     = false
}

variable "exp03_run_id" {
  description = "Short lowercase ownership identifier for all EXP-03 resources."
  type        = string
  default     = null
  validation {
    condition     = var.exp03_run_id == null ? true : can(regex("^[a-z0-9]{3,10}$", var.exp03_run_id))
    error_message = "Use 3-10 lowercase letters or digits."
  }
}

variable "exp03_expiry" {
  description = "Required cleanup/review date for temporary EXP-03 resources."
  type        = string
  default     = null
  validation {
    condition     = var.exp03_expiry == null ? true : can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.exp03_expiry)) && can(formatdate("YYYY-MM-DD", "${var.exp03_expiry}T00:00:00Z"))
    error_message = "Use YYYY-MM-DD."
  }
}

variable "exp03_second_public_subnet_cidr" {
  description = "Reviewed unused VPC subnet CIDR in the second AZ, dedicated to the temporary ALB."
  type        = string
  default     = null
  validation {
    condition     = var.exp03_second_public_subnet_cidr == null ? true : can(cidrhost(var.exp03_second_public_subnet_cidr, 0))
    error_message = "Use an IPv4 CIDR after verifying the current VPC allocations."
  }
}

variable "exp03_certificate_arn" {
  description = "Exact existing issued ACM certificate ARN for the approved HTTPS origin."
  type        = string
  default     = null
  validation {
    condition     = var.exp03_certificate_arn == null ? true : can(regex("^arn:aws:acm:ap-south-1:335523638354:certificate/[0-9a-f-]+$", var.exp03_certificate_arn))
    error_message = "Use an exact ACM certificate ARN in the project account and region."
  }
}

variable "exp03_lambda_image_uri" {
  description = "Reviewed immutable project-account ECR image digest for the Lambda app."
  type        = string
  default     = null
  validation {
    condition     = var.exp03_lambda_image_uri == null ? true : can(regex("^335523638354\\.dkr\\.ecr\\.ap-south-1\\.amazonaws\\.com/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$", var.exp03_lambda_image_uri))
    error_message = "Use an immutable ECR digest in the project account and region."
  }
}

variable "exp03_lambda_memory_mb" {
  description = "Reviewed Lambda memory setting, no more than the experiment design limit."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_lambda_memory_mb == null ? true : var.exp03_lambda_memory_mb >= 128 && var.exp03_lambda_memory_mb <= 2048 && floor(var.exp03_lambda_memory_mb) == var.exp03_lambda_memory_mb
    error_message = "Choose an integer from 128 through 2048 MiB."
  }
}

variable "exp03_lambda_reserved_concurrency" {
  description = "Explicit DB-budget-reviewed Lambda concurrency; the maximum is not a sizing recommendation."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_lambda_reserved_concurrency == null ? true : var.exp03_lambda_reserved_concurrency >= 1 && var.exp03_lambda_reserved_concurrency <= 20 && floor(var.exp03_lambda_reserved_concurrency) == var.exp03_lambda_reserved_concurrency
    error_message = "Choose a reviewed integer from 1 through 20."
  }
}

variable "exp03_budget_cap_usd" {
  description = "Declared maximum additional spend for the owned temporary window; external monitoring and stop controls are still required."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_budget_cap_usd == null ? true : var.exp03_budget_cap_usd > 0 && var.exp03_budget_cap_usd <= 10
    error_message = "Set a positive cap no greater than the user's USD 10 limit."
  }
}

variable "exp03_max_runtime_minutes" {
  description = "Declared maximum window in minutes; does not automatically stop resources."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_max_runtime_minutes == null ? true : var.exp03_max_runtime_minutes >= 1 && var.exp03_max_runtime_minutes <= 1440 && floor(var.exp03_max_runtime_minutes) == var.exp03_max_runtime_minutes
    error_message = "Choose a bounded integer window from 1 to 1440 minutes."
  }
}

variable "exp03_route_reads_to_lambda" {
  description = "Enable ECS-hosted Lambda-first routing for the two GET read patterns; false keeps all routes on ECS."
  type        = bool
  default     = false
}

variable "exp03_router_max_inflight" {
  description = "Reviewed per-ECS-process cap for outstanding Lambda SDK calls; required only in configuration B."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_router_max_inflight == null ? true : var.exp03_router_max_inflight >= 1 && var.exp03_router_max_inflight <= 1000 && floor(var.exp03_router_max_inflight) == var.exp03_router_max_inflight
    error_message = "Choose a reviewed positive integer per-process cap no greater than 1000."
  }
}

variable "exp03_router_deadline_seconds" {
  description = "Reviewed per-request router deadline, at most the approved five-second request timeout."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_router_deadline_seconds == null ? true : var.exp03_router_deadline_seconds > 0 && var.exp03_router_deadline_seconds <= 5
    error_message = "Choose a positive router deadline no greater than five seconds."
  }
}

variable "exp03_invoke_connect_timeout_seconds" {
  description = "Reviewed Lambda SDK connection timeout, at most five seconds."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_invoke_connect_timeout_seconds == null ? true : var.exp03_invoke_connect_timeout_seconds > 0 && var.exp03_invoke_connect_timeout_seconds <= 5
    error_message = "Choose a positive connection timeout no greater than five seconds."
  }
}

variable "exp03_invoke_read_timeout_seconds" {
  description = "Reviewed Lambda SDK response-read timeout, at most five seconds."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_invoke_read_timeout_seconds == null ? true : var.exp03_invoke_read_timeout_seconds > 0 && var.exp03_invoke_read_timeout_seconds <= 5
    error_message = "Choose a positive read timeout no greater than five seconds."
  }
}

variable "exp03_invoke_pool_connections" {
  description = "Reviewed botocore connection-pool size per ECS process."
  type        = number
  default     = null
  validation {
    condition     = var.exp03_invoke_pool_connections == null ? true : var.exp03_invoke_pool_connections >= 1 && var.exp03_invoke_pool_connections <= 1000 && floor(var.exp03_invoke_pool_connections) == var.exp03_invoke_pool_connections
    error_message = "Choose a positive integer SDK pool size no greater than 1000."
  }
}

locals {
  exp03_active = var.exp03_enabled && local.service_enabled
  exp03_name   = "clip-exp03-${coalesce(var.exp03_run_id, "unset")}"
  exp03_tags = merge(local.common_tags, {
    Owner      = "Rahul"
    Task       = "EXP-03"
    RunId      = coalesce(var.exp03_run_id, "unset")
    ExpiresOn  = coalesce(var.exp03_expiry, "unset")
    BudgetUSD  = coalesce(tostring(var.exp03_budget_cap_usd), "unset")
    MaxMinutes = coalesce(tostring(var.exp03_max_runtime_minutes), "unset")
  })
}

resource "terraform_data" "exp03_inputs" {
  count = var.exp03_enabled || var.exp03_route_reads_to_lambda ? 1 : 0
  lifecycle {
    precondition {
      condition = local.exp03_active && var.api_service_enabled && var.identity_runtime_enabled && var.hybrid_runtime_enabled && var.vpc_cidr == "10.64.0.0/20" && var.public_subnet_cidr == "10.64.0.0/24" && var.active_private_subnet_cidr == "10.64.1.0/24" && var.secondary_private_subnet_cidr == "10.64.2.0/24" && alltrue([
        var.exp03_run_id != null,
        var.exp03_expiry != null,
        var.exp03_second_public_subnet_cidr != null,
        var.exp03_certificate_arn != null,
        var.exp03_lambda_image_uri != null,
        var.exp03_lambda_memory_mb != null,
        var.exp03_lambda_reserved_concurrency != null,
        var.exp03_budget_cap_usd != null,
        var.exp03_max_runtime_minutes != null,
        !var.exp03_route_reads_to_lambda || var.exp03_router_max_inflight != null,
        !var.exp03_route_reads_to_lambda || (var.exp03_router_max_inflight != null && var.exp03_router_max_inflight >= var.exp03_lambda_reserved_concurrency),
        !var.exp03_route_reads_to_lambda || var.exp03_router_deadline_seconds != null,
        !var.exp03_route_reads_to_lambda || var.exp03_invoke_connect_timeout_seconds != null,
        !var.exp03_route_reads_to_lambda || var.exp03_invoke_read_timeout_seconds != null,
        !var.exp03_route_reads_to_lambda || var.exp03_invoke_pool_connections != null,
        var.exp03_second_public_subnet_cidr == null ? false : contains([for n in range(16) : cidrsubnet(var.vpc_cidr, 4, n)], var.exp03_second_public_subnet_cidr),
        !contains([var.public_subnet_cidr, var.active_private_subnet_cidr, var.secondary_private_subnet_cidr], var.exp03_second_public_subnet_cidr),
      ])
      error_message = "EXP-03 requires the real Identity/Hybrid ECS service and explicit run, budget, runtime, cleanup, subnet, certificate, image, memory and concurrency inputs."
    }
  }
}

# The RDS-only secondary subnet remains private. The ALB receives its own
# second-AZ subnet and associates it with the existing public route table.
resource "aws_subnet" "exp03_public_secondary" {
  count                   = local.exp03_active ? 1 : 0
  vpc_id                  = aws_vpc.shared[0].id
  cidr_block              = var.exp03_second_public_subnet_cidr
  availability_zone       = var.secondary_availability_zone
  map_public_ip_on_launch = false
  tags                    = merge(local.exp03_tags, { Name = "${local.exp03_name}-public" })
  depends_on              = [terraform_data.exp03_inputs]
}

resource "aws_route_table_association" "exp03_public_secondary" {
  count          = local.exp03_active ? 1 : 0
  subnet_id      = aws_subnet.exp03_public_secondary[0].id
  route_table_id = aws_route_table.nat_public[0].id
}

resource "aws_security_group" "exp03_alb" {
  count       = local.exp03_active ? 1 : 0
  name        = "${local.exp03_name}-alb"
  description = "Temporary public HTTPS ingress for the reviewed comparison."
  vpc_id      = aws_vpc.shared[0].id
  tags        = merge(local.exp03_tags, { Name = "${local.exp03_name}-alb" })
}

resource "aws_vpc_security_group_ingress_rule" "exp03_alb_https" {
  count             = local.exp03_active ? 1 : 0
  security_group_id = aws_security_group.exp03_alb[0].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "Public HTTPS; application session controls remain active."
  tags              = local.exp03_tags
}

resource "aws_security_group" "exp03_ecs" {
  count       = local.exp03_active ? 1 : 0
  name        = "${local.exp03_name}-ecs-ingress"
  description = "Additional temporary ingress group for the ECS host."
  vpc_id      = aws_vpc.shared[0].id
  tags        = merge(local.exp03_tags, { Name = "${local.exp03_name}-ecs-ingress" })
}

resource "aws_vpc_security_group_egress_rule" "exp03_alb_to_ecs" {
  count                        = local.exp03_active ? 1 : 0
  security_group_id            = aws_security_group.exp03_alb[0].id
  referenced_security_group_id = aws_security_group.exp03_ecs[0].id
  ip_protocol                  = "tcp"
  from_port                    = 18000
  to_port                      = 18000
  description                  = "Only the existing ECS API host port."
  tags                         = local.exp03_tags
}

resource "aws_vpc_security_group_ingress_rule" "exp03_ecs_from_alb" {
  count                        = local.exp03_active ? 1 : 0
  security_group_id            = aws_security_group.exp03_ecs[0].id
  referenced_security_group_id = aws_security_group.exp03_alb[0].id
  ip_protocol                  = "tcp"
  from_port                    = 18000
  to_port                      = 18000
  description                  = "Only the temporary ALB may reach the API host port."
  tags                         = local.exp03_tags
}

resource "aws_security_group" "exp03_lambda" {
  count       = local.exp03_active ? 1 : 0
  name        = "${local.exp03_name}-lambda"
  description = "Temporary Lambda read path without inbound access."
  vpc_id      = aws_vpc.shared[0].id
  tags        = merge(local.exp03_tags, { Name = "${local.exp03_name}-lambda" })
}

resource "aws_vpc_security_group_egress_rule" "exp03_lambda_to_database" {
  count                        = local.exp03_active ? 1 : 0
  security_group_id            = aws_security_group.exp03_lambda[0].id
  referenced_security_group_id = aws_security_group.database[0].id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "Only the existing private PostgreSQL security group."
  tags                         = local.exp03_tags
}

resource "aws_vpc_security_group_egress_rule" "exp03_lambda_to_ssm" {
  count             = local.exp03_active ? 1 : 0
  security_group_id = aws_security_group.exp03_lambda[0].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "HTTPS through existing NAT for the fixed SSM runtime references."
  tags              = local.exp03_tags
}

resource "aws_lb" "exp03" {
  count              = local.exp03_active ? 1 : 0
  name               = local.exp03_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.exp03_alb[0].id]
  subnets            = [aws_subnet.nat_public[0].id, aws_subnet.exp03_public_secondary[0].id]
  tags               = merge(local.exp03_tags, { Name = local.exp03_name })
  depends_on         = [aws_route_table_association.exp03_public_secondary]
}

resource "aws_lb_target_group" "exp03_ecs" {
  count       = local.exp03_active ? 1 : 0
  name        = "${local.exp03_name}-ecs"
  port        = 18000
  protocol    = "HTTP"
  target_type = "instance"
  vpc_id      = aws_vpc.shared[0].id
  health_check {
    path                = "/health"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
  tags = local.exp03_tags
}

resource "aws_lb_listener" "exp03_https" {
  count             = local.exp03_active ? 1 : 0
  load_balancer_arn = aws_lb.exp03[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.exp03_certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.exp03_ecs[0].arn
  }
  tags = local.exp03_tags
}

resource "aws_iam_role" "exp03_lambda" {
  count = local.exp03_active ? 1 : 0
  name  = "${local.exp03_name}-lambda"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "lambda.amazonaws.com" } }]
  })
  tags = local.exp03_tags
}

resource "aws_cloudwatch_log_group" "exp03_lambda" {
  count             = local.exp03_active ? 1 : 0
  name              = "/aws/lambda/${local.exp03_name}"
  retention_in_days = 7
  tags              = local.exp03_tags
}

resource "aws_iam_role_policy" "exp03_lambda" {
  count = local.exp03_active ? 1 : 0
  name  = "${local.exp03_name}-runtime"
  role  = aws_iam_role.exp03_lambda[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ssm:GetParameter"], Resource = [
        "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/listings-database-url",
        "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/identity/database-url",
        "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/identity/authentication-keys",
      ] },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.exp03_lambda[0].arn}:*" },
      # Lambda service needs these EC2 ENI actions for a VPC-attached function.
      { Effect = "Allow", Action = ["ec2:CreateNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DescribeSubnets", "ec2:DeleteNetworkInterface", "ec2:AssignPrivateIpAddresses", "ec2:UnassignPrivateIpAddresses"], Resource = "*" },
      # The Lambda service needs ENI permissions, but function code does not.
      { Effect = "Deny", Action = ["ec2:CreateNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DescribeSubnets", "ec2:DeleteNetworkInterface", "ec2:DetachNetworkInterface", "ec2:AssignPrivateIpAddresses", "ec2:UnassignPrivateIpAddresses"], Resource = "*", Condition = {
        ArnEquals = { "lambda:SourceFunctionArn" = "arn:aws:lambda:${local.region}:${local.account_id}:function:${local.exp03_name}" }
      } },
    ]
  })
}

resource "aws_lambda_function" "exp03" {
  count                          = local.exp03_active ? 1 : 0
  function_name                  = local.exp03_name
  role                           = aws_iam_role.exp03_lambda[0].arn
  package_type                   = "Image"
  image_uri                      = var.exp03_lambda_image_uri
  architectures                  = ["x86_64"]
  memory_size                    = var.exp03_lambda_memory_mb
  timeout                        = 5
  reserved_concurrent_executions = var.exp03_lambda_reserved_concurrency
  vpc_config {
    subnet_ids         = [aws_subnet.workload_private[0].id]
    security_group_ids = [aws_security_group.exp03_lambda[0].id]
  }
  environment {
    variables = {
      CLIP_ENVIRONMENT                       = "test"
      CLIP_IDENTITY_PROVIDER                 = "microsoft"
      CLIP_EMAIL_PROVIDER                    = "disabled"
      CLIP_IDENTITY_RUNTIME_ENABLED          = "true"
      CLIP_IDENTITY_BROWSER_ORIGINS          = jsonencode(["https://clip-iisc.site"])
      CLIP_LAMBDA_DATABASE_PARAMETER_ENABLED = "true"
      CLIP_HYBRID_SEARCH_ENABLED             = "true"
      CLIP_HYBRID_WORKER_ENABLED             = "false"
      CLIP_STORAGE_PROVIDER                  = "disabled"
      CLIP_SERVE_WEB_APP                     = "false"
    }
  }
  depends_on = [aws_iam_role_policy.exp03_lambda, terraform_data.exp03_inputs]
  tags       = local.exp03_tags
}

resource "aws_iam_role_policy" "exp03_ecs_invoke_lambda" {
  count = local.exp03_active && var.exp03_route_reads_to_lambda ? 1 : 0
  name  = "${local.exp03_name}-invoke-lambda"
  role  = aws_iam_role.api_task[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = aws_lambda_function.exp03[0].arn
    }]
  })
}
