# Outputs expose only nonsensitive identifiers needed by later approved steps.
output "api_ecr_repository_url" {
  description = "Private ECR repository URI for the reviewed API image."
  value       = try(aws_ecr_repository.api[0].repository_url, null)
}

output "ecs_cluster_name" {
  description = "Shared test ECS cluster name."
  value       = try(aws_ecs_cluster.shared[0].name, null)
}

output "ecs_capacity_provider_name" {
  description = "Single-host EC2 capacity provider name."
  value       = try(aws_ecs_capacity_provider.shared[0].name, null)
}

output "database_endpoint_address" {
  description = "Private RDS endpoint hostname; it contains no credential."
  value       = try(aws_db_instance.shared[0].address, null)
}
