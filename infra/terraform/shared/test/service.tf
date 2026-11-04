# This phase adds the API service and two separately invoked database tasks
# after the base infrastructure exists. All use private EC2 bridge networking;
# no public listener or inbound security-group rule is created. Real Identity
# configuration is opt-in and remains at zero tasks outside an approved window.
# New service names follow DEC-03; existing base names remain untouched. Owner=shared-team
# is the explicit PD-16 exception, with the human operator accountable.
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

  name = "clip-test-db-setup-secrets-${local.region}-pd16"
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

  name = "clip-test-db-probe-secret-${local.region}-pd16"
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

  family                   = "clip-test-api-${local.region}-pd16"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = tostring(var.api_task_cpu)
  memory                   = tostring(var.api_task_memory_mib)
  execution_role_arn       = aws_iam_role.api_execution[0].arn
  task_role_arn            = aws_iam_role.api_task[0].arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([merge({
    name      = "api"
    image     = var.api_image_uri
    essential = true
    cpu       = var.api_task_cpu
    memory    = var.api_task_memory_mib
    portMappings = [{
      containerPort = 8000
      hostPort      = 18000
      protocol      = "tcp"
    }]
    # Preserve the disabled foundation profile until complete controlled runtime
    # inputs are reviewed. Recipients are private Terraform inputs, never literals.
    environment = concat([
      { name = "CLIP_ENVIRONMENT", value = var.identity_runtime_enabled ? "test" : "production" },
      { name = "CLIP_DEBUG", value = "false" },
      ], var.identity_runtime_enabled ? [
      { name = "CLIP_IDENTITY_PROVIDER", value = "microsoft" },
      { name = "CLIP_EMAIL_PROVIDER", value = "dual" },
      { name = "CLIP_IDENTITY_RUNTIME_ENABLED", value = "true" },
      { name = "CLIP_IDENTITY_BROWSER_ORIGINS", value = jsonencode(["https://clip-iisc.site"]) },
      { name = "CLIP_SES_TEST_RECIPIENTS", value = jsonencode(var.identity_test_recipients) },
      { name = "CLIP_DEVELOPMENT_AUTH", value = "false" },
      { name = "CLIP_ISOLATED_LISTINGS_TEST_CALLER", value = "false" },
      { name = "CLIP_SERVE_WEB_APP", value = "true" },
      { name = "CLIP_STORAGE_PROVIDER", value = "s3" },
      { name = "CLIP_IMAGE_BUCKET", value = aws_s3_bucket.listings_images[0].bucket },
      { name = "CLIP_IMAGE_REGION", value = local.region },
      { name = "CLIP_IMAGE_KEY_PREFIX", value = "id01" },
      { name = "CLIP_HYBRID_SEARCH_ENABLED", value = tostring(var.hybrid_runtime_enabled) },
      { name = "CLIP_HYBRID_WORKER_ENABLED", value = tostring(var.hybrid_runtime_enabled) },
      ] : [], var.identity_runtime_enabled ? [
      { name = "CLIP_NOTIFICATION_WORKER_ENABLED", value = tostring(var.notification_worker_enabled) },
      { name = "CLIP_NOTIFICATION_ALLOW_UNLISTED_RECIPIENTS", value = tostring(var.notification_allow_unlisted_recipients) },
    ] : [], local.database_proxy_environment)
    secrets = concat(var.identity_runtime_enabled ? [{
      name      = "CLIP_DATABASE_URL"
      valueFrom = "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/listings-database-url"
      }] : [], var.conversations_runtime_enabled ? [{
      name      = "CLIP_DATABASE_DSN"
      valueFrom = "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/conversations/database-url"
    }] : [])
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
    }, var.identity_runtime_enabled ? {
    # Disable raw URI access logs; trust only the reviewed proxy's exact source IP.
    command = concat([
      "uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0",
      "--port", "8000", "--no-access-log",
      ], local.exp03_active ? [
      "--proxy-headers", "--forwarded-allow-ips", join(",", compact([var.public_subnet_cidr, var.exp03_second_public_subnet_cidr])),
      ] : var.identity_https_proxy_enabled ? [
      "--proxy-headers", "--forwarded-allow-ips", local.identity_proxy_private_ip,
    ] : ["--no-proxy-headers"])
  } : {})])

  lifecycle {
    precondition {
      condition     = (!var.conversations_runtime_enabled && !var.hybrid_runtime_enabled) || var.identity_runtime_enabled
      error_message = "Consumer runtime options require the real Identity profile; fake auth is not an integration path."
    }
    precondition {
      condition     = !var.notification_worker_enabled || (var.identity_runtime_enabled && var.conversations_runtime_enabled)
      error_message = "The notification worker requires the real Identity profile and dedicated Conversations connection."
    }
    precondition {
      condition     = !var.notification_allow_unlisted_recipients || var.notification_worker_enabled
      error_message = "Unlisted notification recipients require the explicitly enabled worker."
    }
    precondition {
      condition     = !var.hybrid_runtime_enabled || (var.api_task_memory_mib >= 2048 && var.api_task_cpu >= 512)
      error_message = "Hybrid requires an explicitly reviewed task cap of at least2048MiB and512CPUunits; defaults are not combined sizing evidence."
    }
    precondition {
      condition     = !var.identity_runtime_enabled || length(var.identity_test_recipients) > 0
      error_message = "Explicit Identity runtime requires a reviewed nonempty controlled-recipient input; never deploy the incomplete demo configuration."
    }
    precondition {
      condition     = var.api_image_uri != null
      error_message = "Set api_image_uri to the reviewed immutable ECR digest before enabling the service phase."
    }
  }

  depends_on = [aws_iam_role_policy.api_execution, aws_iam_role_policy.api_conversations_secret]
}

resource "aws_ecs_service" "api" {
  count = local.service_enabled ? 1 : 0

  name            = "clip-test-api-${local.region}-pd16"
  cluster         = aws_ecs_cluster.shared[0].id
  task_definition = aws_ecs_task_definition.api[0].arn
  desired_count   = var.api_service_enabled ? var.api_service_desired_count : 0

  lifecycle {
    precondition {
      condition     = !var.api_service_enabled || var.api_service_desired_count <= var.ecs_host_max_size
      error_message = "The enabled API service cannot request more tasks than the approved ECS host maximum."
    }
  }

  dynamic "load_balancer" {
    for_each = local.exp03_active ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.exp03_ecs[0].arn
      container_name   = "api"
      container_port   = 8000
    }
  }

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

  depends_on = [
    aws_ecs_cluster_capacity_providers.shared,
    aws_iam_role_policy.api_identity_email,
    aws_iam_role_policy.api_execution,
    aws_lb_listener.exp03_https,
  ]
  tags = { Name = "clip-test-api-${local.region}-pd16" }
}

# This one-shot task creates the dedicated database login. Its psql script
# hashes the password client-side and emits only safe status lines.
resource "aws_ecs_task_definition" "db_role_setup" {
  count = local.service_enabled ? 1 : 0

  family                   = "clip-test-db-role-setup-${local.region}-pd16"
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
  tags = merge(local.common_tags, { Name = "clip-test-db-role-setup-${local.region}-pd16" })
}

# This separate one-shot task sees only the probe credential and checks both
# database connectivity and the low-privilege boundary before reporting pass.
resource "aws_ecs_task_definition" "db_probe" {
  count = local.service_enabled ? 1 : 0

  family                   = "clip-test-db-probe-${local.region}-pd16"
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
  tags = merge(local.common_tags, { Name = "clip-test-db-probe-${local.region}-pd16" })
}
