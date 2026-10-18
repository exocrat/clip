# Environment records

This directory holds non-secret records for contributor workstations, commands, secret-access procedures, and any shared cloud environment. Record observed facts accurately and keep credentials and secret values out of the repository.

## Current records

- [Development workstation](development-workstation.md): verified facts for the contributor's local machine.
- [Command registry](commands.md): project commands and their owners, targets, and readiness.
- [Local API foundation setup and tests](../../apps/api/README.md): verified Python API commands and settings; database/web/combined setup remain later task outputs.
- [Secret handling](secret-handling.md): approved references and access procedures, without secret values.
- [Cloud inventory](cloud-inventory.md): shared account, region, resource, and cost status. Update it from approved plans and actual outputs; do not infer or invent cloud facts.
- [DEC-03 resource naming and tags](../decisions/DEC-03-cloud-resource-naming-and-tags.md): verified CLIP resource-name and tag convention; this is a convention, not provisioning approval.

Cloud creation, changes, and deletion require the separate approvals and checks defined by the project workflow.

## AWS CLI sign-in

For local AWS CLI development, Rahul's verified project profile is named `clip-project`. The sign-in command used for that profile is:

```sh
aws login --profile clip-project
```

This uses an interactive AWS Management Console sign-in to establish local CLI credentials; each contributor must authenticate as their own authorized identity and must not share passwords, MFA codes, credential files, or cached session credentials. The profile name is local configuration, not a credential. After signing in, verify the selected account and identity before any cloud operation:

```sh
aws sts get-caller-identity --profile clip-project
```

For this project, the expected account ID is recorded in [cloud inventory](cloud-inventory.md). Stop if the returned account differs. Sign out of the named profile when appropriate with `aws logout --profile clip-project`. See the official [AWS CLI sign-in guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html) for prerequisites and interactive prompts. Never put credential or session-token values in repository files, logs, or evidence.
## Cloud resource naming and tags

For a nameable resource, use the lowercase pattern `clip-<environment>-<resource>-ap-south-1-<unique-suffix>` when the AWS service permits it. Follow service-specific character, length, and uniqueness constraints; the exact name and suffix must be included in the reviewed resource plan before creation. The Terraform state bucket uses its separately documented pattern in [DEC-02](../decisions/terraform-backend-design.md).

Apply these tags wherever the resource type supports tags:

| Tag key | Value |
|---|---|
| `Project` | `CLIP` |
| `Environment` | The approved environment identifier for the owning task (for example, `test`) |
| `Owner` | The named person accountable for the resource and its cleanup; the person who starts it has first cleanup responsibility |
| `Task` | The owning task ID (for example, `PD-16`) or approved domain slug |
| `ExpiresOn` | The agreed cleanup/expiry review date in `YYYY-MM-DD` format |

Do not put credentials, secret values, personal email addresses, or other sensitive data in names or tags. Include exact names, tag values, expiry/review dates, and any unsupported tagging limitations in the approved plan and resource inventory. These conventions do not authorize creation, modification, adoption, or cleanup of any AWS resource. The selected pattern and required tags are recorded in [DEC-03](../decisions/DEC-03-cloud-resource-naming-and-tags.md).
