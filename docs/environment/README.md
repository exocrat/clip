# Environment records

This directory holds non-secret records for contributor workstations, commands, secret-access procedures, and any shared cloud environment. Record observed facts accurately and keep credentials and secret values out of the repository.

## Current records

- [Development workstation](development-workstation.md): verified facts for the contributor's local machine.
- [Command registry](commands.md): project commands and their owners, targets, and readiness.
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
