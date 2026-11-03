# The VPC keeps all workloads private. NAT is placed in the only public subnet
# and supplies outbound-only access to the active private subnet.
resource "aws_vpc" "shared" {
  count = local.base_enabled ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.prefix}-vpc" }
}

resource "aws_internet_gateway" "shared" {
  count = local.base_enabled ? 1 : 0

  vpc_id = aws_vpc.shared[0].id
  tags   = { Name = "${local.prefix}-igw" }
}

resource "aws_subnet" "nat_public" {
  count = local.base_enabled ? 1 : 0

  vpc_id                  = aws_vpc.shared[0].id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.active_availability_zone
  map_public_ip_on_launch = false

  tags = { Name = "${local.prefix}-nat-public" }
}

resource "aws_subnet" "workload_private" {
  count = local.base_enabled ? 1 : 0

  vpc_id                  = aws_vpc.shared[0].id
  cidr_block              = var.active_private_subnet_cidr
  availability_zone       = var.active_availability_zone
  map_public_ip_on_launch = false

  tags = { Name = "${local.prefix}-workload-private" }
}

resource "aws_subnet" "rds_secondary_private" {
  count = local.base_enabled ? 1 : 0

  vpc_id                  = aws_vpc.shared[0].id
  cidr_block              = var.secondary_private_subnet_cidr
  availability_zone       = var.secondary_availability_zone
  map_public_ip_on_launch = false

  tags = { Name = "${local.prefix}-rds-subnet-only" }
}

resource "aws_route_table" "nat_public" {
  count = local.base_enabled ? 1 : 0

  vpc_id = aws_vpc.shared[0].id
  tags   = { Name = "${local.prefix}-nat-public" }
}

resource "aws_route" "nat_public_default" {
  count = local.base_enabled ? 1 : 0

  route_table_id         = aws_route_table.nat_public[0].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.shared[0].id
}

resource "aws_route_table_association" "nat_public" {
  count = local.base_enabled ? 1 : 0

  subnet_id      = aws_subnet.nat_public[0].id
  route_table_id = aws_route_table.nat_public[0].id
}

resource "aws_eip" "nat" {
  count = local.base_enabled ? 1 : 0

  domain = "vpc"
  tags   = { Name = "${local.prefix}-nat" }
}

resource "aws_nat_gateway" "shared" {
  count = local.base_enabled ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.nat_public[0].id
  depends_on    = [aws_internet_gateway.shared]

  tags = { Name = "${local.prefix}-nat" }
}

resource "aws_route_table" "workload_private" {
  count = local.base_enabled ? 1 : 0

  vpc_id = aws_vpc.shared[0].id
  tags   = { Name = "${local.prefix}-workload-private" }
}

# This subnet exists only because RDS requires a subnet group spanning two AZs.
# It has the VPC-local route but no path to NAT or the public internet.
resource "aws_route_table" "rds_secondary_private" {
  count = local.base_enabled ? 1 : 0

  vpc_id = aws_vpc.shared[0].id
  tags   = { Name = "${local.prefix}-rds-subnet-only" }
}

resource "aws_route" "workload_private_default" {
  count = local.base_enabled ? 1 : 0

  route_table_id         = aws_route_table.workload_private[0].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.shared[0].id
}

resource "aws_route_table_association" "workload_private" {
  count = local.base_enabled ? 1 : 0

  subnet_id      = aws_subnet.workload_private[0].id
  route_table_id = aws_route_table.workload_private[0].id
}

resource "aws_route_table_association" "rds_secondary_private" {
  count = local.base_enabled ? 1 : 0

  subnet_id      = aws_subnet.rds_secondary_private[0].id
  route_table_id = aws_route_table.rds_secondary_private[0].id
}

# No ingress is defined for the ECS host. SSM port forwarding reaches the
# fixed host port through the managed instance without opening a VPC port.
resource "aws_security_group" "ecs_host" {
  count = local.base_enabled ? 1 : 0

  name        = "${local.prefix}-ecs-host"
  description = "Private ECS host; no inbound rules, outbound NAT only."
  vpc_id      = aws_vpc.shared[0].id

  egress {
    description = "Outbound-only egress through the private route to NAT."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.prefix}-ecs-host" }
}

resource "aws_security_group" "database" {
  count = local.base_enabled ? 1 : 0

  name        = "${local.prefix}-database"
  description = "Private PostgreSQL reachable only from the ECS host security group."
  vpc_id      = aws_vpc.shared[0].id

  ingress {
    description     = "Database access from the private ECS host for the API and one-shot probe."
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_host[0].id]
  }

  dynamic "ingress" {
    for_each = local.exp03_active ? [1] : []
    content {
      description     = "Temporary EXP-03 Lambda access to private PostgreSQL."
      from_port       = 5432
      to_port         = 5432
      protocol        = "tcp"
      security_groups = [aws_security_group.exp03_lambda[0].id]
    }
  }

  tags = { Name = "${local.prefix}-database" }
}

resource "aws_db_subnet_group" "shared" {
  count = local.base_enabled ? 1 : 0

  name       = "${local.prefix}-database"
  subnet_ids = [aws_subnet.workload_private[0].id, aws_subnet.rds_secondary_private[0].id]

  tags = { Name = "${local.prefix}-database" }
}

# The RDS password is supplied to this write-only field; the input itself is
# ephemeral and is never retained in Terraform state or a saved plan.
resource "aws_db_instance" "shared" {
  count = local.base_enabled ? 1 : 0

  identifier                 = "${local.prefix}-postgres"
  engine                     = "postgres"
  engine_version             = var.db_engine_version
  availability_zone          = var.active_availability_zone
  instance_class             = var.db_instance_class
  allocated_storage          = var.db_allocated_storage_gib
  storage_type               = "gp3"
  storage_encrypted          = true
  db_name                    = var.db_name
  username                   = var.db_master_username
  password_wo                = var.db_master_password
  password_wo_version        = var.db_master_password_version
  db_subnet_group_name       = aws_db_subnet_group.shared[0].name
  vpc_security_group_ids     = [aws_security_group.database[0].id]
  backup_retention_period    = var.db_backup_retention_days
  copy_tags_to_snapshot      = true
  auto_minor_version_upgrade = true
  multi_az                   = false
  publicly_accessible        = false
  deletion_protection        = var.db_deletion_protection
  skip_final_snapshot        = var.db_skip_final_snapshot_on_delete
  final_snapshot_identifier  = var.db_skip_final_snapshot_on_delete ? null : var.db_final_snapshot_identifier
  apply_immediately          = false

  lifecycle {
    precondition {
      condition     = var.db_skip_final_snapshot_on_delete || var.db_final_snapshot_identifier != null
      error_message = "Choose a final snapshot identifier unless teardown is explicitly configured to skip the final snapshot."
    }
  }

  tags = { Name = "${local.prefix}-postgres" }
}
