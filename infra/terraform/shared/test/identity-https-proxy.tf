# Optional reviewed test ingress. All resources stay absent unless explicitly enabled.
# The exact upstream is supplied only after discovering the one owned ECS host.
variable "identity_https_proxy_enabled" {
  type        = bool
  default     = false
  description = "Create the separately reviewed four-hour Identity HTTPS proxy; defaults off."
}

variable "identity_https_proxy_upstream_ipv4" {
  type        = string
  default     = null
  description = "Observed private ECS host IPv4 under10.64.1.0/24; never a guessed upstream."
  validation {
    condition = var.identity_https_proxy_upstream_ipv4 == null ? true : (
      can(regex("^10\\.64\\.1\\.[0-9]{1,3}$", var.identity_https_proxy_upstream_ipv4)) &&
      can(cidrhost("${var.identity_https_proxy_upstream_ipv4}/32", 0))
    )
    error_message = "Use the observed ECS host IPv4 in the fixed private subnet."
  }
}

variable "identity_https_proxy_review_date" {
  type        = string
  default     = null
  description = "Explicitly reviewed ExpiresOn date for the temporary proxy."
  validation {
    condition     = var.identity_https_proxy_review_date == null ? true : can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.identity_https_proxy_review_date))
    error_message = "Use the reviewed YYYY-MM-DD date."
  }
}

locals {
  identity_proxy_enabled    = local.base_enabled && var.identity_https_proxy_enabled
  identity_proxy_private_ip = "10.64.0.10"
  # Official Caddy2.11.7 Alpine multi-platform index; runtime remains x86_64.
  identity_proxy_image = "docker.io/library/caddy@sha256:eb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f"
  identity_proxy_tags = merge(local.common_tags, {
    Name      = "clip-test-identity-https-ap-south-1-id01"
    Task      = "ID-01"
    Owner     = "Aditya"
    ExpiresOn = var.identity_https_proxy_review_date
  })
  identity_proxy_caddyfile = templatefile("${path.module}/scripts/identity-proxy.Caddyfile.tftpl", {
    upstream_ipv4 = var.identity_https_proxy_upstream_ipv4 == null ? "" : var.identity_https_proxy_upstream_ipv4
  })
}

# A dedicated SSM-only node role: no secrets, application data or ECS registration.
resource "aws_iam_role" "identity_https_proxy" {
  count = local.identity_proxy_enabled ? 1 : 0
  name  = "clip-test-identity-https-ap-south-1-id01"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "ec2.amazonaws.com" } }]
  })
  tags = local.identity_proxy_tags
}

# The managed SSM core policy also permits reading Parameter Store secrets.
# Keep its node/channel functions here without GetParameter/GetParameters.
resource "aws_iam_role_policy" "identity_https_proxy_ssm" {
  count = local.identity_proxy_enabled ? 1 : 0
  name  = "clip-test-identity-https-node-ap-south-1-id01"
  role  = aws_iam_role.identity_https_proxy[0].name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ManagedNodeOnly"
        Effect = "Allow"
        Action = [
          "ssm:DescribeAssociation", "ssm:GetDeployablePatchSnapshotForInstance",
          "ssm:GetDocument", "ssm:DescribeDocument", "ssm:GetManifest",
          "ssm:ListAssociations", "ssm:ListInstanceAssociations", "ssm:PutInventory",
          "ssm:PutComplianceItems", "ssm:PutConfigurePackageResult",
          "ssm:UpdateAssociationStatus", "ssm:UpdateInstanceAssociationStatus",
          "ssm:UpdateInstanceInformation",
        ]
        Resource = "*"
      },
      {
        Sid      = "SessionChannels"
        Effect   = "Allow"
        Action   = ["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"]
        Resource = "*"
      },
      {
        Sid      = "LegacyNodeChannels"
        Effect   = "Allow"
        Action   = ["ec2messages:AcknowledgeMessage", "ec2messages:DeleteMessage", "ec2messages:FailMessage", "ec2messages:GetEndpoint", "ec2messages:GetMessages", "ec2messages:SendReply"]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_instance_profile" "identity_https_proxy" {
  count = local.identity_proxy_enabled ? 1 : 0
  name  = "clip-test-identity-https-ap-south-1-id01"
  role  = aws_iam_role.identity_https_proxy[0].name
  tags  = local.identity_proxy_tags
}

resource "aws_security_group" "identity_https_proxy" {
  count       = local.identity_proxy_enabled ? 1 : 0
  name        = "clip-test-identity-https-ap-south-1-id01"
  description = "Owned HTTPS proxy only; no SSH or direct public API access."
  vpc_id      = aws_vpc.shared[0].id
  ingress {
    description = "ACME and HTTP to HTTPS redirect."
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Reviewed public HTTPS origin."
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description = "SSM, pinned image and ACME endpoints."
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description     = "Private API host port only."
    from_port       = 18000
    to_port         = 18000
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_host[0].id]
  }
  tags = local.identity_proxy_tags
}

resource "aws_vpc_security_group_ingress_rule" "identity_api_from_https_proxy" {
  count                        = local.identity_proxy_enabled ? 1 : 0
  security_group_id            = aws_security_group.ecs_host[0].id
  referenced_security_group_id = aws_security_group.identity_https_proxy[0].id
  description                  = "Only the owned proxy may reach the private API port."
  ip_protocol                  = "tcp"
  from_port                    = 18000
  to_port                      = 18000
  tags                         = local.identity_proxy_tags
}

resource "aws_instance" "identity_https_proxy" {
  count                       = local.identity_proxy_enabled ? 1 : 0
  ami                         = local.ecs_ami_id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.nat_public[0].id
  private_ip                  = local.identity_proxy_private_ip
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.identity_https_proxy[0].id]
  iam_instance_profile        = aws_iam_instance_profile.identity_https_proxy[0].name
  # Stop compute at the run limit; retained IP/disk still need approved cleanup.
  instance_initiated_shutdown_behavior = "stop"
  credit_specification {
    cpu_credits = "standard"
  }
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    encrypted             = true
    delete_on_termination = true
    tags                  = local.identity_proxy_tags
  }
  user_data = templatefile("${path.module}/scripts/identity-proxy-user-data.sh.tftpl", {
    image        = local.identity_proxy_image
    caddy_config = local.identity_proxy_caddyfile
  })
  user_data_replace_on_change = true
  depends_on                  = [aws_iam_role_policy.identity_https_proxy_ssm]
  tags                        = local.identity_proxy_tags
  lifecycle {
    precondition {
      condition     = var.identity_https_proxy_upstream_ipv4 != null && var.identity_https_proxy_review_date != null
      error_message = "Review the run date and observed private upstream before enabling the proxy."
    }
    precondition {
      condition     = var.public_subnet_cidr == "10.64.0.0/24" && var.active_private_subnet_cidr == "10.64.1.0/24"
      error_message = "This proxy is reviewed only for the fixed shared test subnets."
    }
  }
}

resource "aws_eip" "identity_https_proxy" {
  count      = local.identity_proxy_enabled ? 1 : 0
  domain     = "vpc"
  depends_on = [aws_internet_gateway.shared]
  tags       = local.identity_proxy_tags
}

resource "aws_eip_association" "identity_https_proxy" {
  count         = local.identity_proxy_enabled ? 1 : 0
  allocation_id = aws_eip.identity_https_proxy[0].id
  instance_id   = aws_instance.identity_https_proxy[0].id
}

output "identity_https_proxy_public_ip" {
  description = "Reviewed proxy IP for the human-managed domain A record; not a DNS mutation."
  value       = try(aws_eip.identity_https_proxy[0].public_ip, null)
}
