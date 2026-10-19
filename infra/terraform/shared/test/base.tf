# The base phase creates reusable private infrastructure but no ECS task
# definition or service. The exact plan remains a separately approved action.
data "aws_ssm_parameter" "ecs_optimized_ami" {
  count = local.base_enabled ? 1 : 0

  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended/image_id"
}

resource "aws_ecr_repository" "api" {
  count = local.base_enabled ? 1 : 0

  name                 = "${local.prefix}-api"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = { Name = "${local.prefix}-api" }
}

resource "aws_cloudwatch_log_group" "api" {
  count = local.base_enabled ? 1 : 0

  name              = "/ecs/${local.prefix}"
  retention_in_days = var.log_retention_days

  tags = { Name = "${local.prefix}-logs" }
}

resource "aws_ecs_cluster" "shared" {
  count = local.base_enabled ? 1 : 0

  name = local.prefix
  tags = { Name = "${local.prefix}" }
}

# The EC2 role lets the ECS and SSM agents register and maintain managed-node
# connectivity. SSM port forwarding still requires a separately authorized
# operator session; Terraform does not grant access to an individual user.
resource "aws_iam_role" "ecs_instance" {
  count = local.base_enabled ? 1 : 0

  name = "${local.prefix}-ecs-instance"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = { Name = "${local.prefix}-ecs-instance" }
}

resource "aws_iam_role_policy_attachment" "ecs_instance_agent" {
  count = local.base_enabled ? 1 : 0

  role       = aws_iam_role.ecs_instance[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_role_policy_attachment" "ecs_instance_ssm" {
  count = local.base_enabled ? 1 : 0

  role       = aws_iam_role.ecs_instance[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ecs_instance" {
  count = local.base_enabled ? 1 : 0

  name = "${local.prefix}-ecs-instance"
  role = aws_iam_role.ecs_instance[0].name
}

# The API execution role is limited to pulling from this repository and writing
# to this log group. The API task role itself receives no AWS permissions.
resource "aws_iam_role" "api_execution" {
  count = local.base_enabled ? 1 : 0

  name = "${local.prefix}-api-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = { Name = "${local.prefix}-api-execution" }
}

resource "aws_iam_role_policy" "api_execution" {
  count = local.base_enabled ? 1 : 0

  name = "${local.prefix}-api-execution"
  role = aws_iam_role.api_execution[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
        ]
        Resource = aws_ecr_repository.api[0].arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.api[0].arn}:*"
      },
    ]
  })
}

resource "aws_iam_role" "api_task" {
  count = local.base_enabled ? 1 : 0

  name = "${local.prefix}-api-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = { Name = "${local.prefix}-api-task" }
}

# One fixed EC2 host registers into ECS, runs in the active private subnet,
# keeps a 30-GiB encrypted gp3 root volume, and has no SSH key or public IP.
resource "aws_launch_template" "ecs_host" {
  count = local.base_enabled ? 1 : 0

  name_prefix   = "${local.prefix}-"
  image_id      = data.aws_ssm_parameter.ecs_optimized_ami[0].value
  instance_type = var.ecs_instance_type
  user_data = base64encode(<<-EOT
    #!/bin/bash
    set -eu
    mkdir -p /etc/ecs
    cat >> /etc/ecs/ecs.config <<'EOF'
    ECS_CLUSTER=${aws_ecs_cluster.shared[0].name}
    ECS_ENABLE_TASK_IAM_ROLE=true
    EOF
    systemctl enable --now amazon-ssm-agent
  EOT
  )

  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_instance[0].name
  }

  vpc_security_group_ids = [aws_security_group.ecs_host[0].id]

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 30
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  tag_specifications {
    resource_type = "instance"
    tags          = merge(local.common_tags, { Name = "${local.prefix}-ecs-host" })
  }

  tag_specifications {
    resource_type = "volume"
    tags          = merge(local.common_tags, { Name = "${local.prefix}-ecs-root" })
  }
}

resource "aws_autoscaling_group" "ecs_host" {
  count = local.base_enabled ? 1 : 0

  name                = "${local.prefix}-ecs-host"
  min_size            = 1
  max_size            = 1
  desired_capacity    = 1
  vpc_zone_identifier = [aws_subnet.workload_private[0].id]

  launch_template {
    id      = aws_launch_template.ecs_host[0].id
    version = aws_launch_template.ecs_host[0].latest_version
  }

  tag {
    key                 = "Name"
    value               = "${local.prefix}-ecs-host"
    propagate_at_launch = true
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = "true"
    propagate_at_launch = true
  }

}

resource "aws_ecs_capacity_provider" "shared" {
  count = local.base_enabled ? 1 : 0

  name = "${local.prefix}-capacity"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.ecs_host[0].arn
    managed_termination_protection = "DISABLED"
  }

  tags = { Name = "${local.prefix}-capacity" }
}

resource "aws_ecs_cluster_capacity_providers" "shared" {
  count = local.base_enabled ? 1 : 0

  cluster_name       = aws_ecs_cluster.shared[0].name
  capacity_providers = [aws_ecs_capacity_provider.shared[0].name]

  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.shared[0].name
    weight            = 1
    base              = 1
  }
}
