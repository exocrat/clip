# Optional controlled recipient resource required by the observed SES sandbox
# authorization check. Sensitive masks the private address in plan rendering;
# the exact ARN remains in the access-controlled Terraform state/IAM policy.
# Preserve this input in later sandbox plans; remove it deliberately after the
# production-access/configuration review, never replace it with identity/*.
variable "ses_sandbox_recipient_identity_arn" {
  description = "Private exact verified recipient identity ARN for the bounded SES sandbox test; null omits the additional resource."
  type        = string
  sensitive   = true
  default     = null

  validation {
    condition     = var.ses_sandbox_recipient_identity_arn == null ? true : can(regex("^arn:aws:ses:ap-south-1:335523638354:identity/[^@ /]+@[^@ /]+$", var.ses_sandbox_recipient_identity_arn)) && !strcontains(var.ses_sandbox_recipient_identity_arn, "*") && !strcontains(var.ses_sandbox_recipient_identity_arn, "?")
    error_message = "Select one exact verified email identity in the approved account/region, or null; wildcards are forbidden."
  }
}

# ID-01 Step 2: shared-role permission for the verified SES sender.
# Desired sender changed by Aditya to verify@; deployed role still uses the old
# sender until a separately approved exact plan/apply updates this condition.
# Domain verification and recipient ownership remain separately checked;
# this policy neither enables compute nor authorizes a live email test.
resource "aws_iam_role_policy" "api_identity_email" {
  count = local.base_enabled ? 1 : 0

  name = "${local.prefix}-identity-email"
  role = aws_iam_role.api_task[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SendIdentityEmailFromVerifiedDomain"
        Effect = "Allow"
        Action = "ses:SendEmail"
        Resource = compact([
          "arn:aws:ses:${local.region}:${local.account_id}:identity/clip-iisc.site",
          var.ses_sandbox_recipient_identity_arn,
        ])
        Condition = {
          StringEquals = {
            "ses:FromAddress" = ["verify@clip-iisc.site", "updates@clip-iisc.site"]
          }
        }
      },
      {
        Sid    = "ReadOnlyIdentityRuntimeParameters"
        Effect = "Allow"
        Action = ["ssm:GetParameter"]
        Resource = [
          "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/identity/authentication-keys",
          "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/identity/database-url",
          "arn:aws:ssm:${local.region}:${local.account_id}:parameter/clip/test/identity/email-delivery",
        ]
      },
      {
        Sid    = "PrivateListingsImageObjectAccess"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Resource = [
          "${aws_s3_bucket.listings_images[0].arn}/id01/*",
        ]
      },
    ]
  })
}
