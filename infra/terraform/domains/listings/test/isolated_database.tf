# This database is disposable and belongs only to the LI-02 rehearsal. It is
# placed in the existing private VPC, but it does not reuse or modify the
# shared RDS instance or its database contents. The approved test master
# password is reused only as the disposable instance's administrator secret.
data "aws_subnet" "shared_workload_private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.shared.id]
  }

  filter {
    name   = "tag:Name"
    values = ["clip-shared-test-workload-private"]
  }
}

data "aws_subnet" "shared_rds_secondary_private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.shared.id]
  }

  filter {
    name   = "tag:Name"
    values = ["clip-shared-test-rds-subnet-only"]
  }
}

data "aws_rds_engine_version" "postgres" {
  engine  = "postgres"
  version = var.demo_database_engine_version
  latest  = false
}

resource "aws_db_subnet_group" "demo" {
  count = var.demo_enabled ? 1 : 0

  name = "clip-test-listings-ap-south-1-li02"
  subnet_ids = [
    data.aws_subnet.shared_workload_private.id,
    data.aws_subnet.shared_rds_secondary_private.id,
  ]

  tags = { Name = "clip-test-listings-ap-south-1-li02" }
}

resource "aws_security_group" "demo_database" {
  count = var.demo_enabled ? 1 : 0

  name        = "clip-test-listings-db-ap-south-1-li02"
  description = "Private PostgreSQL for the disposable LI-02 cloud rehearsal."
  vpc_id      = data.aws_vpc.shared.id

  tags = { Name = "clip-test-listings-db-ap-south-1-li02" }
}

resource "aws_vpc_security_group_ingress_rule" "demo_database_from_ecs" {
  count = var.demo_enabled ? 1 : 0

  security_group_id            = aws_security_group.demo_database[0].id
  referenced_security_group_id = data.aws_security_group.shared_ecs_host.id
  description                  = "PostgreSQL from the existing private ECS host only."
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_db_instance" "demo" {
  count = var.demo_enabled ? 1 : 0

  identifier                 = "clip-test-listings-ap-south-1-li02"
  engine                     = "postgres"
  engine_version             = data.aws_rds_engine_version.postgres.version_actual
  instance_class             = "db.t4g.micro"
  availability_zone          = var.demo_database_availability_zone
  allocated_storage          = 20
  storage_type               = "gp3"
  storage_encrypted          = true
  db_name                    = "clip_test"
  username                   = "clip_test_admin"
  password_wo                = var.database_master_password
  password_wo_version        = var.database_master_password_version
  db_subnet_group_name       = aws_db_subnet_group.demo[0].name
  vpc_security_group_ids     = [aws_security_group.demo_database[0].id]
  backup_retention_period    = 0
  copy_tags_to_snapshot      = false
  auto_minor_version_upgrade = true
  multi_az                   = false
  publicly_accessible        = false
  deletion_protection        = false
  skip_final_snapshot        = true
  delete_automated_backups   = true
  apply_immediately          = true

  lifecycle {
    precondition {
      condition     = var.database_master_password != null
      error_message = "The reviewed LI-02 database master password must be supplied ephemerally when creating or updating the disposable RDS instance."
    }
  }

  tags = { Name = "clip-test-listings-ap-south-1-li02" }
}

output "database_endpoint" {
  description = "Private endpoint for the disposable LI-02 test database."
  value       = var.demo_enabled ? aws_db_instance.demo[0].address : null
}

output "database_port" {
  description = "Port for the disposable LI-02 test database."
  value       = var.demo_enabled ? aws_db_instance.demo[0].port : null
}
