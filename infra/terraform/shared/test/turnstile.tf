# Targeted sign-in recovery is opt-in. Only the public site key enters Terraform;
# the production verifier secret is provisioned separately as a SecureString.
variable "turnstile_site_key" {
  description = "Public production Turnstile widget key for clip-iisc.site. Null preserves the existing disabled profile. The verifier secret must already exist at /clip/test/turnstile/secret-key; never pass it to Terraform or an image build."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.turnstile_site_key == null ? true : can(regex("^[A-Za-z0-9_-]{10,256}$", var.turnstile_site_key))
    error_message = "turnstile_site_key must be null or a valid public widget key."
  }
}

locals {
  turnstile_enabled              = var.turnstile_site_key != null
  turnstile_secret_parameter_arn = "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/turnstile/secret-key"
  turnstile_environment = local.turnstile_enabled ? [
    { name = "CLIP_TURNSTILE_SITE_KEY", value = var.turnstile_site_key },
  ] : []
  turnstile_secrets = local.turnstile_enabled ? [
    { name = "CLIP_TURNSTILE_SECRET_KEY", valueFrom = local.turnstile_secret_parameter_arn },
  ] : []
}

# ECS resolves the exact parameter before starting the container. The application
# task role, proxy and Lambda read runtime receive no additional secret access.
# Use the AWS-managed aws/ssm key; a custom KMS key requires separately reviewed
# decrypt permissions and is not configured by this change.
resource "aws_iam_role_policy" "api_turnstile_secret" {
  count = local.service_enabled && local.turnstile_enabled ? 1 : 0
  name  = "${local.prefix}-api-turnstile-secret"
  role  = aws_iam_role.api_execution[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameters"]
      Resource = local.turnstile_secret_parameter_arn
    }]
  })
}
