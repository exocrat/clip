output "state_bucket_name" {
  description = "Generated private S3 bucket name for Terraform state; publishing this identifier is not a secret."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "state_bucket_region" {
  description = "AWS Region containing the Terraform state bucket."
  value       = local.region
}
