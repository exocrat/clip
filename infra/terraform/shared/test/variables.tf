# Cloud-changing phases stay disabled unless a reviewed operation selects one.
variable "deployment_phase" {
  description = "Set to base for shared infrastructure or service for the later ECS API/login-setup/probe tasks; disabled creates no AWS resources."
  type        = string
  default     = "disabled"

  validation {
    condition     = contains(["disabled", "base", "service"], var.deployment_phase)
    error_message = "deployment_phase must be disabled, base, or service."
  }
}

variable "api_service_enabled" {
  description = "Run the API service during an approved test window. False keeps the service at zero tasks so ECS can scale the EC2 capacity provider to zero. One-shot tasks can still request capacity through the cluster default strategy."
  type        = bool
  default     = false
}

variable "cleanup_review_date" {
  description = "Required ExpiresOn tag and cleanup review date for the approved environment."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.cleanup_review_date))
    error_message = "cleanup_review_date must use YYYY-MM-DD format."
  }
}

variable "vpc_cidr" {
  description = "Approved CIDR for the dedicated PD-16 VPC."
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

variable "public_subnet_cidr" {
  description = "Approved subnet CIDR for the NAT gateway only."
  type        = string

  validation {
    condition     = can(cidrhost(var.public_subnet_cidr, 0))
    error_message = "public_subnet_cidr must be a valid IPv4 CIDR block."
  }
}

variable "active_private_subnet_cidr" {
  description = "Approved private subnet CIDR for the ECS host and Single-AZ RDS instance."
  type        = string

  validation {
    condition     = can(cidrhost(var.active_private_subnet_cidr, 0))
    error_message = "active_private_subnet_cidr must be a valid IPv4 CIDR block."
  }
}

variable "secondary_private_subnet_cidr" {
  description = "Approved second-AZ private subnet CIDR used only by the RDS subnet group."
  type        = string

  validation {
    condition     = can(cidrhost(var.secondary_private_subnet_cidr, 0))
    error_message = "secondary_private_subnet_cidr must be a valid IPv4 CIDR block."
  }
}

variable "active_availability_zone" {
  description = "Approved ap-south-1 AZ for the running ECS host, NAT, and Single-AZ database."
  type        = string
}

variable "secondary_availability_zone" {
  description = "Different ap-south-1 AZ for the RDS subnet-group-only private subnet."
  type        = string
}

variable "ecs_instance_type" {
  description = "The one approved x86_64 ECS host type; c7i-flex.large is the current provisional selection."
  type        = string
  default     = "c7i-flex.large"
}

variable "db_instance_class" {
  description = "PostgreSQL RDS instance class; set after the exact size and cost review."
  type        = string
}

variable "db_engine_version" {
  description = "Exact supported PostgreSQL engine version for the approved plan."
  type        = string
}

variable "db_allocated_storage_gib" {
  description = "RDS gp3 allocation in GiB, set after the storage and cost review."
  type        = number

  validation {
    condition     = var.db_allocated_storage_gib >= 20
    error_message = "db_allocated_storage_gib must be at least 20 GiB for the selected PostgreSQL gp3 configuration."
  }
}

variable "db_backup_retention_days" {
  description = "RDS automated-backup retention in days; choose explicitly before planning."
  type        = number

  validation {
    condition     = var.db_backup_retention_days >= 1 && var.db_backup_retention_days <= 35
    error_message = "db_backup_retention_days must be between 1 and 35."
  }
}

variable "db_skip_final_snapshot_on_delete" {
  description = "Whether approved teardown may delete RDS without a final snapshot; choose explicitly."
  type        = bool
}

variable "db_final_snapshot_identifier" {
  description = "Required when db_skip_final_snapshot_on_delete is false."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.db_final_snapshot_identifier == null || can(regex("^[a-z][a-z0-9-]{0,254}$", var.db_final_snapshot_identifier))
    error_message = "db_final_snapshot_identifier must start with a lowercase letter and contain only lowercase letters, digits, and hyphens."
  }
}

variable "db_name" {
  description = "Initial synthetic-test database name."
  type        = string
  default     = "clip_test"
}

variable "db_master_username" {
  description = "Non-secret master username for the disposable test database."
  type        = string
  default     = "clip_test_admin"
}

variable "db_master_password" {
  description = "Sensitive write-only password supplied for the base create or intentional rotation; omit for the service phase. Never commit or log it."
  type        = string
  sensitive   = true
  ephemeral   = true
  default     = null
  nullable    = true
}

variable "db_master_password_version" {
  description = "Increment only when the write-only database password is intentionally rotated."
  type        = number
  default     = 1
}

variable "db_probe_password" {
  description = "Sensitive single-line write-only password for the dedicated PostgreSQL probe login; supply only for the service phase and never commit or log it."
  type        = string
  sensitive   = true
  ephemeral   = true
  default     = null
  nullable    = true
}

variable "db_probe_password_version" {
  description = "Increment only when the write-only probe password is intentionally rotated."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "Explicit CloudWatch log retention period; select before planning."
  type        = number

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "log_retention_days must be one of the supported CloudWatch Logs retention periods."
  }
}

variable "api_image_uri" {
  description = "Reviewed immutable ECR image URI including the linux/amd64 image digest; required for the service phase."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.api_image_uri == null || can(regex("@sha256:[0-9a-f]{64}$", var.api_image_uri))
    error_message = "api_image_uri must use an immutable sha256 digest when supplied."
  }
}

variable "postgres_probe_image_uri" {
  description = "Reviewed immutable PostgreSQL client image URI including a sha256 digest; required for the service phase."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.postgres_probe_image_uri == null || can(regex("@sha256:[0-9a-f]{64}$", var.postgres_probe_image_uri))
    error_message = "postgres_probe_image_uri must use an immutable sha256 digest when supplied."
  }
}
