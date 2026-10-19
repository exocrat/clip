# This root intentionally has no backend block until PD-15 backend setup and
# migration are approved. The version and provider match the repository pin.
terraform {
  required_version = "= 1.15.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region              = local.region
  allowed_account_ids = [local.account_id]

  default_tags {
    tags = local.common_tags
  }
}
