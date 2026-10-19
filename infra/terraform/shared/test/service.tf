# This phase adds the API service and two separately invoked database tasks
# after the base infrastructure exists. All use private EC2 bridge networking;
# no public listener or inbound security-group rule is created.
resource "aws_ssm_parameter" "db_probe_password" {
  count = local.service_enabled ? 1 : 0

  name             = local.db_probe_password_parameter_name
  description      = "PD-16 dedicated PostgreSQL probe-login credential."
  type             = "SecureString"
  tier             = "Standard"
  value_wo         = var.db_probe_password
  value_wo_version = var.db_probe_password_version

  tags = local.common_tags
}

# The setup task alone can retrieve the RDS master credential and probe
# credential. The default AWS-managed SSM key is used, so no custom KMS grant
# is needed; parameter-level access is restricted to these two exact ARNs.
resource "aws_iam_role_policy" "db_role_setup_secrets" {
  count = local.service_enabled ? 1 : 0

  name = "${local.prefix}-db-setup-secrets"
  role = aws_iam_role.db_role_setup_execution[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["ssm:GetParameters"]
      Resource = [
        aws_ssm_parameter.db_master_password[0].arn,
        aws_ssm_parameter.db_probe_password[0].arn,
      ]
    }]
  })
}

# The probe execution role can retrieve only the low-privilege login secret.
resource "aws_iam_role_policy" "db_probe_secret" {
  count = local.service_enabled ? 1 : 0

  name = "${local.prefix}-db-probe-secret"
  role = aws_iam_role.db_probe_execution[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameters"]
      Resource = aws_ssm_parameter.db_probe_password[0].arn
    }]
  })
}

resource "aws_ecs_task_definition" "api" {
  count = local.service_enabled ? 1 : 0

  family                   = "${local.prefix}-api"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.api_execution[0].arn
  task_role_arn            = aws_iam_role.api_task[0].arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name      = "api"
    image     = var.api_image_uri
    essential = true
    cpu       = 256
    memory    = 512
    portMappings = [{
      containerPort = 8000
      hostPort      = 18000
      protocol      = "tcp"
    }]
    environment = [
      { name = "CLIP_ENVIRONMENT", value = "production" },
      { name = "CLIP_DEBUG", value = "false" },
    ]
    healthCheck = {
      command = [
        "CMD",
        "python",
        "-c",
        "import json, urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)) == {'status': 'ok'}",
      ]
      interval    = 30
      timeout     = 3
      retries     = 3
      startPeriod = 10
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api[0].name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.api_image_uri != null
      error_message = "Set api_image_uri to the reviewed immutable ECR digest before enabling the service phase."
    }
  }

  depends_on = [aws_iam_role_policy.api_execution]
}

resource "aws_ecs_service" "api" {
  count = local.service_enabled ? 1 : 0

  name            = "${local.prefix}-api"
  cluster         = aws_ecs_cluster.shared[0].id
  task_definition = aws_ecs_task_definition.api[0].arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.shared[0].name
    weight            = 1
    base              = 1
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  enable_ecs_managed_tags            = true
  enable_execute_command             = false
  propagate_tags                     = "SERVICE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_ecs_cluster_capacity_providers.shared]
  tags       = { Name = "${local.prefix}-api" }
}

# This one-shot task creates the dedicated database login. Its psql script
# hashes the password client-side and emits only safe status lines.
resource "aws_ecs_task_definition" "db_role_setup" {
  count = local.service_enabled ? 1 : 0

  family                   = "${local.prefix}-db-role-setup"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.db_role_setup_execution[0].arn
  task_role_arn            = aws_iam_role.db_role_setup_task[0].arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name       = "db-role-setup"
    image      = var.postgres_probe_image_uri
    essential  = true
    cpu        = 256
    memory     = 512
    entryPoint = ["/bin/sh", "-c"]
    command    = [file("${path.module}/scripts/setup-db-role.sh")]
    environment = [
      { name = "PGHOST", value = aws_db_instance.shared[0].address },
      { name = "PGPORT", value = tostring(aws_db_instance.shared[0].port) },
      { name = "PGDATABASE", value = var.db_name },
      { name = "PGUSER", value = var.db_master_username },
    ]
    secrets = [
      { name = "PGPASSWORD", valueFrom = aws_ssm_parameter.db_master_password[0].arn },
      { name = "PROBE_PASSWORD", valueFrom = aws_ssm_parameter.db_probe_password[0].arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api[0].name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "db-role-setup"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.postgres_probe_image_uri != null
      error_message = "Set postgres_probe_image_uri to a reviewed immutable client-image digest before enabling the service phase."
    }
  }

  depends_on = [
    aws_iam_role_policy.db_role_setup_execution_logs,
    aws_iam_role_policy.db_role_setup_secrets,
  ]
  tags = merge(local.common_tags, { Name = "${local.prefix}-db-role-setup" })
}

# This separate one-shot task sees only the probe credential and checks both
# database connectivity and the low-privilege boundary before reporting pass.
resource "aws_ecs_task_definition" "db_probe" {
  count = local.service_enabled ? 1 : 0

  family                   = "${local.prefix}-db-probe"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.db_probe_execution[0].arn
  task_role_arn            = aws_iam_role.db_probe_task[0].arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name       = "db-probe"
    image      = var.postgres_probe_image_uri
    essential  = true
    cpu        = 256
    memory     = 512
    entryPoint = ["/bin/sh", "-c"]
    command    = [file("${path.module}/scripts/probe-db.sh")]
    environment = [
      { name = "PGHOST", value = aws_db_instance.shared[0].address },
      { name = "PGPORT", value = tostring(aws_db_instance.shared[0].port) },
      { name = "PGDATABASE", value = var.db_name },
      { name = "PGUSER", value = local.db_probe_username },
    ]
    secrets = [
      { name = "PGPASSWORD", valueFrom = aws_ssm_parameter.db_probe_password[0].arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api[0].name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "db-probe"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.postgres_probe_image_uri != null
      error_message = "Set postgres_probe_image_uri to a reviewed immutable client-image digest before enabling the service phase."
    }
  }

  depends_on = [
    aws_iam_role_policy.db_probe_execution_logs,
    aws_iam_role_policy.db_probe_secret,
  ]
  tags = merge(local.common_tags, { Name = "${local.prefix}-db-probe" })
}
