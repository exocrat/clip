# Identity test Terraform root

Reserved for resources exclusive to the Identity domain. Its planned state key is `domains/identity/test/terraform.tfstate`; use the default workspace. Shared infrastructure remains owned by PD-16 and must be consumed through reviewed interfaces, not recreated here. Do not add resources or initialize a backend until the domain task reviews the design and cloud approval gates pass. See [Terraform ownership boundaries](../../../../../docs/architecture/terraform-ownership.md).
