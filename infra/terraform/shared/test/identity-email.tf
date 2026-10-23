# ID-01 Step 2: shared-role permission for the verified SES sender.
# Domain verification and recipient ownership remain separately checked;
# this policy neither enables compute nor authorizes a live email test.
resource "aws_iam_role_policy" "api_identity_email" {
  count = local.base_enabled ? 1 : 0

  name = "${local.prefix}-identity-email"
  role = aws_iam_role.api_task[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "SendIdentityEmailFromVerifiedDomain"
      Effect   = "Allow"
      Action   = "ses:SendEmail"
      Resource = "arn:aws:ses:${local.region}:${local.account_id}:identity/clip-iisc.site"
      Condition = {
        StringEquals = {
          "ses:FromAddress" = "no-reply@clip-iisc.site"
        }
      }
    }]
  })
}
