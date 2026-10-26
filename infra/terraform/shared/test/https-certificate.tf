# Shared application certificate only. Enabling this does not publish DNS, attach a
# listener, start compute or expose the application. Review a full root plan first.
variable "https_certificate_enabled" {
  description = "Explicitly request the non-exportable public certificate for the approved Identity HTTPS origin; defaults to no certificate resource."
  type        = bool
  default     = false
}

variable "https_certificate_review_date" {
  description = "Reviewed ExpiresOn date for the retained certificate; required before enabling it."
  type        = string
  default     = null

  validation {
    condition     = var.https_certificate_review_date == null ? true : can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.https_certificate_review_date))
    error_message = "Use an explicitly reviewed YYYY-MM-DD date."
  }
}

resource "aws_acm_certificate" "identity_https" {
  count = local.base_enabled && var.https_certificate_enabled ? 1 : 0

  domain_name       = "clip-iisc.site"
  validation_method = "DNS"
  key_algorithm     = "RSA_2048"
  # ACM's default public certificate is non-exportable; no private key is exposed.
  tags = {
    Name      = "clip-test-identity-https-ap-south-1-id01"
    ExpiresOn = var.https_certificate_review_date
  }

  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.https_certificate_review_date != null
      error_message = "Set the human-reviewed certificate retention/review date before enabling HTTPS certificate creation."
    }
  }
}

# Public DNS validation records only. The operator adds them at Spaceship; no
# Route53 zone is adopted and no blocking certificate-validation resource runs.
output "identity_https_certificate_arn" {
  description = "Certificate ARN for a later separately reviewed shared HTTPS listener."
  value       = try(aws_acm_certificate.identity_https[0].arn, null)
}

output "identity_https_dns_validation" {
  description = "Public CNAME records to add at the existing DNS provider; retain for managed renewal."
  value = local.base_enabled && var.https_certificate_enabled ? {
    for record in aws_acm_certificate.identity_https[0].domain_validation_options : record.domain_name => {
      name  = record.resource_record_name
      type  = record.resource_record_type
      value = record.resource_record_value
    }
  } : {}
}
