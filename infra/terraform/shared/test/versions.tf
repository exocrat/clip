# PD-15 created and migrated the bootstrap state; this root uses a separate
# key in that existing bucket. The version and provider match repository pins.
terraform {
  required_version = "= 1.15.9"

  backend "s3" {
    bucket              = "clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0"
    key                 = "shared/test/terraform.tfstate"
    region              = "ap-south-1"
    use_lockfile        = true
    encrypt             = true
    allowed_account_ids = ["335523638354"]
  }

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
