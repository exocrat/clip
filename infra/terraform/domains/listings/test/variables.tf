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
  description = "The exact loopback origin of the local web app used for the isolated upload test."
  type        = string
  default     = "http://127.0.0.1:5173"

  validation {
    condition     = contains(["http://127.0.0.1:5173", "http://localhost:5173"], var.test_web_origin)
    error_message = "test_web_origin must be one of the documented loopback Vite origins."
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
