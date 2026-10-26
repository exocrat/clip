terraform {
  required_version = "= 1.15.9"
  backend "s3" {
    bucket              = "clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0"
    key                 = "domains/identity/test/terraform.tfstate"
    region              = "ap-south-1"
    use_lockfile        = true
    encrypt             = true
    allowed_account_ids = ["335523638354"]
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}
provider "aws" {
  region              = "ap-south-1"
  allowed_account_ids = ["335523638354"]
  default_tags {
    tags = {
      Project     = "CLIP"
      Environment = "test"
      Owner       = "Aditya"
      Task        = "ID-01"
      ExpiresOn   = "2026-10-23"
    }
  }
}
variable "builder_enabled" {
  description = "Required explicit selection. True creates the approved temporary builder; false removes owned builder resources and requires cleanup approval."
  type        = bool
}

variable "email_smoke_task_enabled" {
  description = "Required explicit selection. True registers only the reviewed one-shot email task; it never starts it or authorizes sending. False deregisters the owned task and requires cleanup approval."
  type        = bool
}
