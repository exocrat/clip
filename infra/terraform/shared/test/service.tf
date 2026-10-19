# This phase adds the API service after the base infrastructure exists. It uses
# private EC2 bridge networking and a digest-pinned image; no public listener or
# inbound security-group rule is created.
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
