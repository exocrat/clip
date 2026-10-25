locals {
  ecs_cluster_name        = "clip-test-listings-ap-south-1-li02"
  ecs_capacity_provider   = "clip-test-listings-capacity-ap-south-1-li02"
  ecs_auto_scaling_group  = "clip-test-listings-ecs-host-ap-south-1-li02"
  ecs_instance_role       = "clip-test-listings-ecs-instance-ap-south-1-li02"
  ecs_instance_profile    = "clip-test-listings-ecs-instance-ap-south-1-li02"
  ecs_host_security_group = "clip-test-listings-ecs-host-ap-south-1-li02"
  ecs_root_volume_name    = "clip-test-listings-ecs-root-ap-south-1-li02"
}

resource "aws_ecs_cluster" "demo" {
  name = local.ecs_cluster_name

  tags = { Name = local.ecs_cluster_name }
}

resource "aws_security_group" "demo_ecs_host" {
  name        = local.ecs_host_security_group
  description = "Private EC2 host security group for the isolated LI-02 ECS cluster."
  vpc_id      = data.aws_vpc.shared.id

  egress {
    description = "Private ECS host outbound access through the existing shared NAT."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = local.ecs_host_security_group }
}

resource "aws_iam_role" "demo_ecs_instance" {
  name = local.ecs_instance_role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = { Name = local.ecs_instance_role }
}

resource "aws_iam_role_policy_attachment" "demo_ecs_instance_agent" {
  role       = aws_iam_role.demo_ecs_instance.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "demo_ecs_instance" {
  name = local.ecs_instance_profile
  role = aws_iam_role.demo_ecs_instance.name
}

resource "aws_launch_template" "demo_ecs_host" {
  name_prefix   = "clip-test-listings-ecs-host-li02-"
  image_id      = data.aws_ssm_parameter.ecs_optimized_ami.value
  instance_type = "c7i-flex.large"

  user_data = base64encode(<<-EOT
    #!/bin/bash
    set -eu
    mkdir -p /etc/ecs
    cat >> /etc/ecs/ecs.config <<'EOF'
    ECS_CLUSTER=${aws_ecs_cluster.demo.name}
    ECS_ENABLE_TASK_IAM_ROLE=true
    EOF

    cat > /usr/local/sbin/clip-li02-block-task-imds <<'EOF'
    #!/bin/bash
    set -eu
    if ! /usr/sbin/iptables -C FORWARD -i docker+ -d 169.254.169.254/32 -j DROP 2>/dev/null; then
      /usr/sbin/iptables -I FORWARD 1 -i docker+ -d 169.254.169.254/32 -j DROP
    fi
    EOF
    chmod 0755 /usr/local/sbin/clip-li02-block-task-imds

    cat > /etc/systemd/system/clip-li02-block-task-imds.service <<'EOF'
    [Unit]
    Description=Block ECS bridge tasks from EC2 instance metadata
    After=network-pre.target
    Before=ecs.service

    [Service]
    Type=oneshot
    ExecStart=/usr/local/sbin/clip-li02-block-task-imds
    RemainAfterExit=yes

    [Install]
    WantedBy=multi-user.target
    EOF
    systemctl daemon-reload
    systemctl enable --now clip-li02-block-task-imds.service
    systemctl restart ecs.service
  EOT
  )

  iam_instance_profile {
    name = aws_iam_instance_profile.demo_ecs_instance.name
  }

  vpc_security_group_ids = [aws_security_group.demo_ecs_host.id]

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
    tags = {
      Name = local.ecs_auto_scaling_group
      Task = "LI-02"
    }
  }

  tag_specifications {
    resource_type = "volume"
    tags = {
      Name = local.ecs_root_volume_name
      Task = "LI-02"
    }
  }
}

resource "aws_autoscaling_group" "demo_ecs_host" {
  name                = local.ecs_auto_scaling_group
  min_size            = 0
  max_size            = 1
  desired_capacity    = 0
  vpc_zone_identifier = [data.aws_subnet.shared_workload_private.id]

  launch_template {
    id      = aws_launch_template.demo_ecs_host.id
    version = aws_launch_template.demo_ecs_host.latest_version
  }

  tag {
    key                 = "Name"
    value               = local.ecs_auto_scaling_group
    propagate_at_launch = true
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = "true"
    propagate_at_launch = true
  }

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}

resource "aws_ecs_capacity_provider" "demo" {
  name = local.ecs_capacity_provider

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.demo_ecs_host.arn
    managed_termination_protection = "DISABLED"
    managed_draining               = "ENABLED"

    managed_scaling {
      maximum_scaling_step_size = 1
      minimum_scaling_step_size = 1
      status                    = "ENABLED"
      target_capacity           = 100
    }
  }

  tags = { Name = local.ecs_capacity_provider }
}

resource "aws_ecs_cluster_capacity_providers" "demo" {
  cluster_name       = aws_ecs_cluster.demo.name
  capacity_providers = [aws_ecs_capacity_provider.demo.name]

  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.demo.name
    weight            = 1
    base              = 1
  }
}
