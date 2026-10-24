variable "resource_owner" {
  description = "Named person accountable for the Listings test resources."
  type        = string
  default     = "Suraj"

  validation {
    condition     = length(trimspace(var.resource_owner)) > 0
    error_message = "resource_owner must name an accountable person."
  }
}
variable "cleanup_review_date" {
  description = "Required ExpiresOn tag and cleanup review date for the approved test resources."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.cleanup_review_date))
    error_message = "cleanup_review_date must use YYYY-MM-DD format."
  }
}

variable "test_web_origin" {
  description = "The exact origin of the isolated web app used for browser uploads."
  type        = string
  default     = "http://127.0.0.1:5173"

  validation {
    condition = contains(["http://127.0.0.1:5173", "http://localhost:5173"], var.test_web_origin) || can(regex(
      "^https://[a-z0-9][a-z0-9.-]*\\.[a-z]{2,}$",
      var.test_web_origin
    ))
    error_message = "test_web_origin must be a documented local Vite origin or one HTTPS hostname."
  }
}

variable "test_run_id" {
  description = "Short unique identifier that limits this rehearsal's S3 object prefix."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,39}$", var.test_run_id))
    error_message = "test_run_id must be 3-40 lowercase letters, digits, or hyphens and start with a letter or digit."
  }
}

variable "demo_enabled" {
  description = "Create the temporary public ALB and ECS app service for an approved demo window."
  type        = bool
  default     = false
}

variable "demo_app_enabled" {
  description = "Start the public ECS API task only after the isolated database has been created, migrated, and seeded."
  type        = bool
  default     = false

  validation {
    condition     = !var.demo_app_enabled || var.demo_enabled
    error_message = "demo_app_enabled requires the LI-02 public demo resources to be enabled."
  }
}

variable "api_image_uri" {
  description = "Immutable API plus built-web ECR image digest for the selected source revision."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.api_image_uri == null || can(regex("^335523638354\\.dkr\\.ecr\\.ap-south-1\\.amazonaws\\.com/clip-shared-test-api@sha256:[0-9a-f]{64}$", var.api_image_uri))
    error_message = "api_image_uri must use an immutable digest from the reviewed shared test API ECR repository."
  }
}

variable "database_image_uri" {
  description = "Immutable dbmate plus fixed Listings database lifecycle image digest."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.database_image_uri == null || can(regex("^335523638354\\.dkr\\.ecr\\.ap-south-1\\.amazonaws\\.com/clip-shared-test-api@sha256:[0-9a-f]{64}$", var.database_image_uri))
    error_message = "database_image_uri must use an immutable digest from the reviewed shared test API ECR repository."
  }
}

variable "demo_public_subnet_cidr" {
  description = "LI-02-owned second public subnet required by the two-AZ internet-facing ALB."
  type        = string
  default     = "10.64.3.0/24"

  validation {
    condition     = can(cidrnetmask(var.demo_public_subnet_cidr))
    error_message = "demo_public_subnet_cidr must be a valid IPv4 CIDR block."
  }
}

variable "demo_public_availability_zone" {
  description = "Second ap-south-1 availability zone for the temporary ALB subnet."
  type        = string
  default     = "ap-south-1b"

  validation {
    condition     = contains(["ap-south-1b", "ap-south-1c"], var.demo_public_availability_zone)
    error_message = "demo_public_availability_zone must differ from the shared public subnet's ap-south-1a zone."
  }
}

variable "demo_database_availability_zone" {
  description = "Private Availability Zone for the disposable LI-02 PostgreSQL instance."
  type        = string
  default     = "ap-south-1b"

  validation {
    condition     = var.demo_database_availability_zone == "ap-south-1b"
    error_message = "demo_database_availability_zone must use ap-south-1b, the existing secondary private subnet's Availability Zone."
  }
}

variable "demo_database_engine_version" {
  description = "PostgreSQL engine version for the disposable database; match the shared test foundation's PostgreSQL 18.6 runtime."
  type        = string
  default     = "18.6"

  validation {
    condition     = var.demo_database_engine_version == "18.6"
    error_message = "The LI-02 disposable database must match the shared test foundation's PostgreSQL 18.6 runtime."
  }
}

variable "database_master_password" {
  description = "Existing approved test-RDS master password, supplied only as an ephemeral value to RDS's write-only password field."
  type        = string
  sensitive   = true
  ephemeral   = true
  default     = null
  nullable    = true
}

variable "database_master_password_version" {
  description = "Write-only password version; increment only after an explicitly approved database credential rotation."
  type        = number
  default     = 1
}
