terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

locals {
  account_id = "335523638354"
  region     = "ap-south-1"
}

provider "aws" {
  region              = local.region
  allowed_account_ids = [local.account_id]

  default_tags {
    tags = {
      Project           = "CLIP"
      Environment       = "bootstrap"
      Owner             = var.resource_owner
      Task              = "PD-15"
      CleanupReviewDate = var.cleanup_review_date
    }
  }
}
