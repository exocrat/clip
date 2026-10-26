# Shared API storage for the hosted Listings runtime. This bucket is separate
# from LI-02's isolated demo bucket and remains private; the API signs short-lived
# upload/download requests only under the id01/ prefix.
resource "aws_s3_bucket" "listings_images" {
  count = local.base_enabled ? 1 : 0

  bucket        = "clip-test-listings-images-ap-south-1-id01"
  force_destroy = false

  tags = merge(local.common_tags, {
    Name  = "clip-test-listings-images-ap-south-1-id01"
    Owner = "Aditya"
    Task  = "ID-01"
  })
}

resource "aws_s3_bucket_public_access_block" "listings_images" {
  count = local.base_enabled ? 1 : 0

  bucket                  = aws_s3_bucket.listings_images[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "listings_images" {
  count = local.base_enabled ? 1 : 0

  bucket = aws_s3_bucket.listings_images[0].id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "listings_images" {
  count = local.base_enabled ? 1 : 0

  bucket = aws_s3_bucket.listings_images[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = false
  }
}

resource "aws_s3_bucket_cors_configuration" "listings_images" {
  count = local.base_enabled ? 1 : 0

  bucket = aws_s3_bucket.listings_images[0].id
  cors_rule {
    allowed_headers = ["content-type", "if-none-match"]
    allowed_methods = ["PUT", "GET", "HEAD"]
    allowed_origins = ["https://clip-iisc.site"]
    expose_headers  = ["ETag"]
    max_age_seconds = 300
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "listings_images" {
  count = local.base_enabled ? 1 : 0

  bucket = aws_s3_bucket.listings_images[0].id
  rule {
    id     = "abort-incomplete-id01-uploads"
    status = "Enabled"
    filter {
      prefix = "id01/"
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_s3_bucket_policy" "listings_images" {
  count = local.base_enabled ? 1 : 0

  bucket = aws_s3_bucket.listings_images[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource = [
        aws_s3_bucket.listings_images[0].arn,
        "${aws_s3_bucket.listings_images[0].arn}/*",
      ]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.listings_images]
}
