data "aws_vpc" "shared" {
  filter {
    name   = "tag:Name"
    values = ["clip-shared-test-vpc"]
  }
}

data "aws_internet_gateway" "shared" {
  filter {
    name   = "attachment.vpc-id"
    values = [data.aws_vpc.shared.id]
  }
}

data "aws_subnet" "shared_public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.shared.id]
  }

  filter {
    name   = "tag:Name"
    values = ["clip-shared-test-nat-public"]
  }
}

data "aws_ssm_parameter" "ecs_optimized_ami" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended/image_id"
}

resource "aws_subnet" "demo_public" {
  count = var.demo_enabled ? 1 : 0

  vpc_id                  = data.aws_vpc.shared.id
  cidr_block              = var.demo_public_subnet_cidr
  availability_zone       = var.demo_public_availability_zone
  map_public_ip_on_launch = false

  tags = { Name = "clip-test-listings-public-ap-south-1-li02" }
}

resource "aws_route_table" "demo_public" {
  count = var.demo_enabled ? 1 : 0

  vpc_id = data.aws_vpc.shared.id
  tags   = { Name = "clip-test-listings-public-ap-south-1-li02" }
}

resource "aws_route" "demo_public_default" {
  count = var.demo_enabled ? 1 : 0

  route_table_id         = aws_route_table.demo_public[0].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = data.aws_internet_gateway.shared.id
}

resource "aws_route_table_association" "demo_public" {
  count = var.demo_enabled ? 1 : 0

  subnet_id      = aws_subnet.demo_public[0].id
  route_table_id = aws_route_table.demo_public[0].id
}

resource "aws_security_group" "demo_alb" {
  count = var.demo_enabled ? 1 : 0

  name        = "clip-test-listings-alb-ap-south-1-li02"
  description = "Temporary public HTTP ingress for synthetic Listings demo."
  vpc_id      = data.aws_vpc.shared.id

  ingress {
    description = "Public HTTP demo route; removed by LI-02 stop."
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "Forward app traffic only to the LI-02 ECS host demo port."
    from_port       = 18001
    to_port         = 18001
    protocol        = "tcp"
    security_groups = [aws_security_group.demo_ecs_host.id]
  }

  tags = { Name = "clip-test-listings-alb-ap-south-1-li02" }
}

resource "aws_vpc_security_group_ingress_rule" "demo_from_alb" {
  count = var.demo_enabled ? 1 : 0

  security_group_id            = aws_security_group.demo_ecs_host.id
  referenced_security_group_id = aws_security_group.demo_alb[0].id
  description                  = "Temporary ALB access to the LI-02 app host port."
  ip_protocol                  = "tcp"
  from_port                    = 18001
  to_port                      = 18001
}

resource "aws_lb" "demo" {
  count = var.demo_enabled ? 1 : 0

  name               = "clip-li02-demo"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.demo_alb[0].id]
  subnets            = [data.aws_subnet.shared_public.id, aws_subnet.demo_public[0].id]

  enable_deletion_protection = false
  drop_invalid_header_fields = true

  depends_on = [aws_route.demo_public_default, aws_route_table_association.demo_public]

  tags = { Name = "clip-test-listings-alb-ap-south-1-li02" }
}

resource "aws_lb_target_group" "demo" {
  count = var.demo_enabled ? 1 : 0

  name        = "clip-li02-demo"
  port        = 18001
  protocol    = "HTTP"
  target_type = "instance"
  vpc_id      = data.aws_vpc.shared.id

  health_check {
    enabled             = true
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 20
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = { Name = "clip-test-listings-target-ap-south-1-li02" }
}

resource "aws_lb_listener" "demo_http" {
  count = var.demo_enabled ? 1 : 0

  load_balancer_arn = aws_lb.demo[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.demo[0].arn
  }
}

resource "aws_ecs_task_definition" "demo_api" {
  count = var.demo_enabled ? 1 : 0

  family                   = "clip-test-listings-demo-ap-south-1-li02"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "listings-demo"
    image     = var.api_image_uri
    essential = true
    cpu       = 256
    memory    = 512
    portMappings = [{
      containerPort = 8000
      hostPort      = 18001
      protocol      = "tcp"
    }]
    environment = [
      { name = "CLIP_ENVIRONMENT", value = "test" },
      { name = "CLIP_DEBUG", value = "false" },
      { name = "CLIP_DEVELOPMENT_AUTH", value = "true" },
      { name = "CLIP_ISOLATED_LISTINGS_TEST_CALLER", value = "true" },
      { name = "CLIP_ISOLATED_LISTINGS_MAX_COUNT", value = "10" },
      { name = "CLIP_SERVE_WEB_APP", value = "true" },
      { name = "CLIP_STORAGE_PROVIDER", value = "s3" },
      { name = "CLIP_IMAGE_BUCKET", value = aws_s3_bucket.images.bucket },
      { name = "CLIP_IMAGE_REGION", value = local.region },
      { name = "CLIP_IMAGE_KEY_PREFIX", value = local.image_prefix },
    ]
    secrets = [{
      name      = "CLIP_DATABASE_URL"
      valueFrom = local.db_url_parameter_arn
    }]
    healthCheck = {
      command     = ["CMD", "python", "-c", "import json, urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)) == {'status': 'ok'}"]
      interval    = 30
      timeout     = 3
      retries     = 3
      startPeriod = 20
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "demo-api"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.api_image_uri != null
      error_message = "Set api_image_uri to the reviewed immutable web/API image digest before starting the demo."
    }
  }

  depends_on = [aws_iam_role_policy.execution, aws_iam_role_policy.task_images]
}

resource "aws_ecs_service" "demo_api" {
  count = var.demo_enabled ? 1 : 0

  name            = "clip-test-listings-demo-ap-south-1-li02"
  cluster         = aws_ecs_cluster.demo.arn
  task_definition = aws_ecs_task_definition.demo_api[0].arn
  desired_count   = var.demo_app_enabled ? 1 : 0

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.demo.name
    weight            = 1
    base              = 1
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.demo[0].arn
    container_name   = "listings-demo"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  enable_execute_command             = false
  propagate_tags                     = "SERVICE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    precondition {
      condition     = !var.demo_app_enabled || var.demo_enabled
      error_message = "demo_app_enabled requires demo_enabled so the reviewed ALB and database tasks exist."
    }
  }

  depends_on = [
    aws_ecs_cluster_capacity_providers.demo,
    aws_lb_listener.demo_http,
    aws_vpc_security_group_ingress_rule.demo_from_alb,
  ]
  tags = { Name = "clip-test-listings-demo-ap-south-1-li02" }
}

output "demo_url" {
  description = "Temporary public HTTP URL for the isolated Listings demo; changes when its ALB is recreated."
  value       = var.demo_enabled ? "http://${aws_lb.demo[0].dns_name}" : null
}
