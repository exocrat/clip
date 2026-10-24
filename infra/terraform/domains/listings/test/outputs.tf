output "image_bucket_name" {
  description = "Private bucket used for Listings image objects."
  value       = aws_s3_bucket.images.bucket
}

output "image_bucket_arn" {
  description = "Non-secret ARN for the Listings image bucket."
  value       = aws_s3_bucket.images.arn
}

output "image_object_prefix" {
  description = "Run-scoped object prefix authorized for this isolated rehearsal."
  value       = "${local.image_prefix}/"
}

output "task_role_arn" {
  description = "Least-privilege role for a Listings ECS task to access the image prefix."
  value       = aws_iam_role.task.arn
}

output "execution_role_arn" {
  description = "Role for ECR image pulls, bounded logs, and the exact database URL parameter."
  value       = aws_iam_role.execution.arn
}

output "db_setup_execution_role_arn" {
  description = "One-shot role for ECR, bounded logs, and the two exact database setup secrets."
  value       = aws_iam_role.db_setup_execution.arn
}

output "log_group_name" {
  description = "Seven-day CloudWatch log group for the isolated Listings task."
  value       = aws_cloudwatch_log_group.api.name
}

output "database_url_parameter_arn" {
  description = "Selected SecureString reference name; this output never contains its value."
  value       = local.db_url_parameter_arn
}
