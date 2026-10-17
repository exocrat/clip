variable "bucket_name" {
  description = "Exact globally unique S3 bucket name selected and reviewed before planning."
  type        = string

  validation {
    condition     = can(regex("^clip-tfstate-335523638354-ap-south-1-[a-z0-9][a-z0-9-]{1,24}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name must use the required prefix and a 3–26 character lowercase alphanumeric/hyphen suffix that starts and ends with a letter or digit (maximum total length 63)."
  }
}

variable "resource_owner" {
  description = "Named person responsible for the bootstrap bucket and first-line cleanup. Set before planning or applying."
  type        = string

  validation {
    condition     = length(trimspace(var.resource_owner)) > 0
    error_message = "resource_owner must be a non-empty name."
  }
}

variable "cleanup_review_date" {
  description = "ISO-8601 date for the next human review of bucket retention and cleanup; set before planning or applying."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.cleanup_review_date))
    error_message = "cleanup_review_date must use YYYY-MM-DD format."
  }
}
