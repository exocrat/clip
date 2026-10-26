# Identity-exclusive temporary builder. Consumes existing shared networking;
# no application role, DB secret, service or shared-root resource is changed.
resource "aws_iam_role" "builder" {
  count = var.builder_enabled ? 1 : 0
  name  = "clip-test-id01-amd64-builder"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}
resource "aws_iam_role_policy" "builder" {
  count = var.builder_enabled ? 1 : 0
  name  = "clip-test-id01-amd64-builder"
  role  = aws_iam_role.builder[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SsmAgentChannelsOnly"
        Effect = "Allow"
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel",
          "ec2messages:AcknowledgeMessage", "ec2messages:DeleteMessage",
          "ec2messages:FailMessage", "ec2messages:GetEndpoint",
          "ec2messages:GetMessages", "ec2messages:SendReply",
        ]
        Resource = "*"
      },
      {
        Sid      = "ExistingImageRepositoryOnly"
        Effect   = "Allow"
        Action   = ["ecr:CompleteLayerUpload", "ecr:UploadLayerPart", "ecr:InitiateLayerUpload", "ecr:BatchCheckLayerAvailability", "ecr:PutImage", "ecr:BatchGetImage"]
        Resource = "arn:aws:ecr:ap-south-1:335523638354:repository/clip-shared-test-api"
      },
      {
        Sid      = "RegistryAuthentication"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
    ]
  })
}
resource "aws_iam_instance_profile" "builder" {
  count = var.builder_enabled ? 1 : 0
  name  = "clip-test-id01-amd64-builder"
  role  = aws_iam_role.builder[0].name
}
resource "aws_security_group" "builder" {
  count       = var.builder_enabled ? 1 : 0
  name        = "clip-test-id01-amd64-builder"
  description = "Temporary private image builder; no inbound access"
  vpc_id      = "vpc-04b0cc01cbf93cd17"
  # HTTPS package/image/SSM traffic uses the existing private-subnet NAT.
  # VPC-resolver DNS does not require an internet-wide DNS egress rule.
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_instance" "builder" {
  count                                = var.builder_enabled ? 1 : 0
  ami                                  = "ami-088fb12f8e8397f06"
  instance_type                        = "t3.small"
  subnet_id                            = "subnet-0c9df7ababd0154bc"
  associate_public_ip_address          = false
  vpc_security_group_ids               = [aws_security_group.builder[0].id]
  iam_instance_profile                 = aws_iam_instance_profile.builder[0].name
  instance_initiated_shutdown_behavior = "terminate"
  user_data_replace_on_change          = true
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  credit_specification {
    cpu_credits = "standard"
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true
  }
  user_data  = <<-SCRIPT
    #!/bin/bash
    set -eu
    # Arm expiry before package setup; shutdown terminates this instance only.
    systemd-run --unit=clip-id01-builder-expiry --on-active=60m /usr/sbin/shutdown -h now
    dnf install -y docker
    systemctl enable --now docker
    systemctl enable --now amazon-ssm-agent
  SCRIPT
  tags       = { Name = "clip-test-id01-amd64-builder", MaxRuntimeMinutes = "60" }
  depends_on = [aws_iam_role_policy.builder]
}
output "builder_instance_id" {
  value = var.builder_enabled ? aws_instance.builder[0].id : null
}
