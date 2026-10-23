locals {
  bucket_name        = "clip-test-listings-images-ap-south-1-li02"
  task_role          = "clip-test-listings-task-ap-south-1-li02"
  exec_role          = "clip-test-listings-execution-ap-south-1-li02"
  db_setup_exec_role = "clip-test-listings-db-setup-execution-ap-south-1-li02"
  log_group          = "/ecs/clip-test-listings-ap-south-1-li02"
  image_prefix       = "listings/test/${var.test_run_id}"

  db_url_parameter_arn    = "arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/listings-database-url"
  db_master_parameter_arn = "arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/database-master-password"
  ecr_repository_arn      = "arn:aws:ecr:ap-south-1:335523638354:repository/clip-shared-test-api"
  runtime_boundary_arn    = "arn:aws:iam::335523638354:policy/clip/listings/test/CLIPListingsTestRuntimeBoundary"
  browser_origins = var.demo_enabled ? [
    "http://${aws_lb.demo[0].dns_name}",
  ] : [var.test_web_origin]
}

resource "aws_s3_bucket" "images" {
  bucket = local.bucket_name

  tags = {
    Name = local.bucket_name
  }
}

resource "aws_s3_bucket_public_access_block" "images" {
  bucket = aws_s3_bucket.images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "images" {
  bucket = aws_s3_bucket.images.id

  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_cors_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  cors_rule {
    allowed_headers = ["content-type", "if-none-match", "x-amz-*"]
    allowed_methods = ["GET", "HEAD", "PUT"]
    allowed_origins = local.browser_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 300
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

data "aws_iam_policy_document" "images_bucket" {
  statement {
    sid    = "DenyUnconditionalRunObjectWrites"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.images.arn}/${local.image_prefix}/*"]

    condition {
      test     = "Null"
      variable = "s3:if-none-match"
      values   = ["true"]
    }
  }

  statement {
    sid    = "DenyRunObjectWritesWithoutCreateOnlyValue"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.images.arn}/${local.image_prefix}/*"]

    condition {
      test     = "StringNotEquals"
      variable = "s3:if-none-match"
      values   = ["*"]
    }
  }

  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.images.arn,
      "${aws_s3_bucket.images.arn}/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "images" {
  bucket = aws_s3_bucket.images.id
  policy = data.aws_iam_policy_document.images_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.images]
}

resource "aws_cloudwatch_log_group" "api" {
  name              = local.log_group
  retention_in_days = 7

  tags = {
    Name = local.log_group
  }
}

data "aws_iam_policy_document" "ecs_tasks_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:ecs:${local.region}:${local.account_id}:*"]
    }
  }
}

data "aws_iam_policy" "runtime_boundary" {
  arn = local.runtime_boundary_arn
}

resource "aws_iam_role" "execution" {
  name                 = local.exec_role
  path                 = "/clip/listings/test/"
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_trust.json
  permissions_boundary = data.aws_iam_policy.runtime_boundary.arn

  tags = {
    Name = local.exec_role
  }
}

resource "aws_iam_role_policy" "execution" {
  name = "clip-test-listings-execution-ap-south-1-li02"
  role = aws_iam_role.execution.id

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
        Resource = local.ecr_repository_arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.api.arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameters"]
        Resource = local.db_url_parameter_arn
      },
    ]
  })
}

resource "aws_iam_role" "task" {
  name                 = local.task_role
  path                 = "/clip/listings/test/"
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_trust.json
  permissions_boundary = data.aws_iam_policy.runtime_boundary.arn

  tags = {
    Name = local.task_role
  }
}

resource "aws_iam_role_policy" "task_images" {
  name = "clip-test-listings-images-ap-south-1-li02"
  role = aws_iam_role.task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
      ]
      Resource = "${aws_s3_bucket.images.arn}/${local.image_prefix}/*"
    }]
  })
}

# A fixed one-shot database bootstrap task uses the approved test master secret
# only against the disposable LI-02 RDS to create/drop its Listings database
# and dedicated login; it never connects to shared RDS.
# Its task definition has no task role; the execution role injects only the
# required SecureStrings and writes to the Listings test log group.
resource "aws_iam_role" "db_setup_execution" {
  name                 = local.db_setup_exec_role
  path                 = "/clip/listings/test/"
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_trust.json
  permissions_boundary = data.aws_iam_policy.runtime_boundary.arn

  tags = {
    Name = local.db_setup_exec_role
  }
}

resource "aws_iam_role_policy" "db_setup_execution" {
  name = "clip-test-listings-db-setup-execution-ap-south-1-li02"
  role = aws_iam_role.db_setup_execution.id

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
        Resource = local.ecr_repository_arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.api.arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameters"]
        Resource = [local.db_master_parameter_arn, local.db_url_parameter_arn]
      },
    ]
  })
}
