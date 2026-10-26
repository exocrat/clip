locals {
  database_task_family_prefix = "clip-test-listings-db-${local.region}-li02"
  database_admin_username     = "clip_test_admin"
  # Stop plans set demo_enabled=false and remove the disposable RDS instance.
  # Keep locals valid while its counted resource is absent.
  database_task_environment = [
    { name = "PGHOST", value = try(aws_db_instance.demo[0].address, "") },
    { name = "PGPORT", value = try(tostring(aws_db_instance.demo[0].port), "") },
    { name = "PGSSLMODE", value = "require" },
  ]
}

# These one-shot definitions have no task role. Their execution roles inject
# only the exact SecureStrings needed for each fixed database operation.
resource "aws_ecs_task_definition" "database_bootstrap" {
  count = var.demo_enabled ? 1 : 0

  family                   = "${local.database_task_family_prefix}-bootstrap"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.db_setup_execution.arn

  container_definitions = jsonencode([{
    name       = "listings-database-bootstrap"
    image      = var.database_image_uri
    essential  = true
    cpu        = 256
    memory     = 512
    entryPoint = ["/usr/local/bin/listings-database-lifecycle"]
    command    = ["bootstrap"]
    environment = concat(local.database_task_environment, [
      { name = "PGDATABASE", value = "clip_test" },
      { name = "PGUSER", value = local.database_admin_username },
    ])
    secrets = [
      { name = "PGPASSWORD", valueFrom = local.db_master_parameter_arn },
      { name = "CLIP_DATABASE_URL", valueFrom = local.db_url_parameter_arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "database-bootstrap"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.database_image_uri != null
      error_message = "Set database_image_uri to the reviewed immutable database image digest before starting the demo."
    }
  }

  depends_on = [aws_iam_role_policy.db_setup_execution]
}

resource "aws_ecs_task_definition" "database_migration" {
  count = var.demo_enabled ? 1 : 0

  family                   = "${local.database_task_family_prefix}-migration"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.execution.arn

  container_definitions = jsonencode([{
    name       = "listings-database-migration"
    image      = var.database_image_uri
    essential  = true
    cpu        = 256
    memory     = 512
    entryPoint = ["/usr/local/bin/listings-dbmate-migration"]
    environment = [
      { name = "DBMATE_MIGRATIONS_DIR", value = "/db/migrations" },
      { name = "DBMATE_NO_DUMP_SCHEMA", value = "true" },
    ]
    secrets = [{ name = "DATABASE_URL", valueFrom = local.db_url_parameter_arn }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "database-migration"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.database_image_uri != null
      error_message = "Set database_image_uri to the reviewed immutable database image digest before starting the demo."
    }
  }

  depends_on = [aws_iam_role_policy.execution]
}

resource "aws_ecs_task_definition" "database_seed" {
  count = var.demo_enabled ? 1 : 0

  family                   = "${local.database_task_family_prefix}-seed"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.execution.arn

  container_definitions = jsonencode([{
    name       = "listings-database-seed"
    image      = var.database_image_uri
    essential  = true
    cpu        = 256
    memory     = 512
    entryPoint = ["/usr/local/bin/listings-database-lifecycle"]
    command    = ["seed"]
    environment = concat(local.database_task_environment, [
      { name = "PGDATABASE", value = "clip_test_listings" },
      { name = "PGUSER", value = "clip_test_listings_app" },
    ])
    secrets = [{ name = "CLIP_DATABASE_URL", valueFrom = local.db_url_parameter_arn }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "database-seed"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.database_image_uri != null
      error_message = "Set database_image_uri to the reviewed immutable database image digest before starting the demo."
    }
  }

  depends_on = [aws_iam_role_policy.execution]
}

resource "aws_ecs_task_definition" "database_cleanup" {
  count = var.demo_enabled ? 1 : 0

  family                   = "${local.database_task_family_prefix}-cleanup"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.db_setup_execution.arn

  container_definitions = jsonencode([{
    name       = "listings-database-cleanup"
    image      = var.database_image_uri
    essential  = true
    cpu        = 256
    memory     = 512
    entryPoint = ["/usr/local/bin/listings-database-lifecycle"]
    command    = ["cleanup"]
    environment = concat(local.database_task_environment, [
      { name = "PGDATABASE", value = "clip_test" },
      { name = "PGUSER", value = local.database_admin_username },
    ])
    secrets = [{ name = "PGPASSWORD", valueFrom = local.db_master_parameter_arn }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "database-cleanup"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.database_image_uri != null
      error_message = "Set database_image_uri to the reviewed immutable database image digest before starting the demo."
    }
  }

  depends_on = [aws_iam_role_policy.db_setup_execution]
}

resource "aws_ecs_task_definition" "database_idle_check" {
  count = var.demo_enabled ? 1 : 0

  family                   = "${local.database_task_family_prefix}-idle-check"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.db_setup_execution.arn

  container_definitions = jsonencode([{
    name       = "listings-database-idle-check"
    image      = var.database_image_uri
    essential  = true
    cpu        = 256
    memory     = 512
    entryPoint = ["/usr/local/bin/listings-database-lifecycle"]
    command    = ["check-idle"]
    environment = concat(local.database_task_environment, [
      { name = "PGDATABASE", value = "clip_test" },
      { name = "PGUSER", value = local.database_admin_username },
    ])
    secrets = [{ name = "PGPASSWORD", valueFrom = local.db_master_parameter_arn }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "database-idle-check"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = var.database_image_uri != null
      error_message = "Set database_image_uri to the reviewed immutable database image digest before starting the demo."
    }
  }

  depends_on = [aws_iam_role_policy.db_setup_execution]
}
