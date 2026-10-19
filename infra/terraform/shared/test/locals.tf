# Shared constants and derived values keep the account, Region, tags, and
# secret reference consistent across resources in this root.
locals {
  account_id = "335523638354"
  region     = "ap-south-1"
  prefix     = "clip-shared-test"

  base_enabled    = contains(["base", "service"], var.deployment_phase)
  service_enabled = var.deployment_phase == "service"

  common_tags = {
    Project     = "CLIP"
    Environment = "test"
    Owner       = "shared-team"
    Task        = "PD-16"
    ExpiresOn   = var.cleanup_review_date
  }

}
