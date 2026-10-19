# Shared test Terraform root

PD-16 owns the shared test-environment root and planned state key `shared/test/terraform.tfstate`; use the default workspace. After the resource inventory is human-verified, PD-16 may add and run local backend-free Terraform source checks here. Do not initialize the remote backend, create a plan, or change AWS resources until the separate backend, target, cost, and exact-plan approval gates pass. See [Terraform ownership boundaries](../../../../docs/architecture/terraform-ownership.md) and the [Terraform change workflow](../../README.md).
