# Environment records

This directory holds non-secret records for contributor workstations, commands, secret-access procedures, and any shared cloud environment. Record observed facts accurately and keep credentials and secret values out of the repository.

## Local foundation setup

This is the common setup path for the current API/web shell and local database.
Marketplace features and final domain datasets are not implemented. No AWS login,
provider account or cloud deployment is needed for these commands.

### Prerequisites

Use the existing clone, with Git, GNU Make and Bash 3.2+ on Linux/macOS. Run the
examples in Bash from the clone root. Windows contributors use their existing
[verified WSL route](wsl-and-first-session.md); native Windows is not this workflow.

- [uv](https://docs.astral.sh/uv/getting-started/installation/), verified at 0.10.7;
  Python 3.14 (`>=3.14,<3.15`), which uv can obtain. CI uses 3.14.3.
- Node 24/npm 11; the verified CI pair is **24.22.0/11.19.1**. Keep the root
  `package.json`/lockfile; do not create a second web installation.
- Local Docker Engine/Desktop with Compose v2-compatible commands and a local
  Unix-socket context. Database images require PostgreSQL 18.6/dbmate 2.36.0.
- Optional, for Terraform targets only: Terraform **1.15.9**. Set `TERRAFORM_BIN`
  to its executable if PATH selects another version. No Terraform apply is needed.

Current local runtime evidence covers Linux ARM64. On 2026-10-20 (Asia/Kolkata),
the user confirmed that the previously deferred Linux AMD64 and macOS checks
passed on other machine(s); the exact machine architecture, commands, and raw
outputs are not retained in this checkout. See the
[database platform record](../../database/README.md) for this reported status
and its evidence limits. Provider checksums for four platforms do not establish
native execution.
Dependency/image/provider downloads need internet access; subsequent commands
use local tools, caches and synthetic inputs.

### First run

```bash
make setup
make install-hooks
make help
```

Setup installs locked Python/Node dependencies. Hook installation is explicit,
per clone; commits require uv on PATH. Black changes stop the commit for review
and restaging. See [hook behavior](../../CONTRIBUTING.md#black-pre-commit-hook-pd-12).

For the database, supply a **local-only** password through the process environment.
The wrapper accepts ASCII letters, digits, `_`, `.`, `~`, `-` only. In Bash, this
prompt keeps the value out of command history/output:

```bash
read -r -s -p 'Local-only PostgreSQL password: ' CLIP_LOCAL_POSTGRES_PASSWORD
printf '\n'
export CLIP_LOCAL_POSTGRES_PASSWORD
make start-db
make seed
make migration-status
```

Reuse the initialization password when restarting an existing volume; changing
the environment value does not rotate it. Preserve it privately. No `.env` file
is sourced by these commands; copying `.env.example` is not setup. `seed` applies
all pending migrations, including eight categories/four conditions, without fake
accounts/listings. Status should show four applied migrations, none pending,
head **20261018152702**. Never reset to fix an unknown authentication error.

In separate terminals, run `make start-api` and `make start-web`. They run in the
foreground and fail on occupied ports. The API is health-only and does not yet
use the database; the web shell does not yet call an application API.

| Service | Local address / success check |
|---|---|
| API | `curl --fail http://127.0.0.1:8000/health` returns `{"status":"ok"}`. This is liveness, not domain readiness. |
| Web | Open `http://127.0.0.1:5173`; the shell/routes appear. |
| PostgreSQL | `make start-db` waits for authenticated TCP on `127.0.0.1:5432`; inspect migration status separately. |
| Built web preview | After `npm run build` or `make test-web`, run `make preview-web`; open `http://127.0.0.1:4173`. |

### Checks and data tooling

Run `make check` for the shared CI-equivalent gates, including explicit data tests,
contract freshness, web lint/types/tests/build and isolated database/secret checks.
The checks create their own disposable containers; they do not reset or reuse the
retained Compose database. Exit zero means pass; skipped/failed checks do not.
Plain `make` only checks Python formatting. `make test`, `make format-check`,
`make contracts-check` and `make terraform-check` select documented subsets;
Terraform remains outside the general aggregate. `make format` rewrites Python;
`make contracts-generate` regenerates outputs from canonical sources.

To create preview scaffolding, choose a fresh explicit name:

```bash
make data-generate RUN_NAME=preview-42 SEED=42 USERS=3 LISTINGS=2
make data-validate RUN_NAME=preview-42
```

These are schema-independent preview files, not final database records.
`make data-load` deliberately fails until DL-00/domain/SE-01 prerequisites exist.
There is no fallback loader or overwritten dataset.

### Stop, retain data, and troubleshoot

Stop each foreground API/web/preview process with Ctrl+C in its own terminal,
then run `make stop-db`. Database volume contents are retained. Repeating
`make start-db`/`make stop-db` does not delete data. No command kills unrelated
listeners or performs automatic volume cleanup. Destructive reset needs separate
explicit approval under the [database procedure](../../database/README.md).
Generated previews follow [the data retention rules](../../data/README.md);
setup caches/build outputs are ignored and are not evidence of a passing check.

| Symptom | Recovery |
|---|---|
| Tool missing/wrong version | Check prerequisites/PATH; rerun `make setup` for project dependencies. Do not relax lockfiles. For Terraform, select 1.15.9 using `TERRAFORM_BIN`. |
| Docker unavailable/remote context refused | Enable the local engine and select its Unix-socket context. Inspect/unset conflicting target overrides; do not substitute a remote host. |
| Port already used | Stop your own existing service or coordinate with its owner; do not kill an unidentified process. Ports do not silently change. |
| Missing password/authentication failure | Supply the local initialization password; inspect the existing volume and sanitized diagnostic. Do not delete/reset it as a retry. |
| Migrations fail or remain pending | Inspect safe output and expected head. Serialize migration runs; never bypass locks or edit applied migrations. |
| Hook reformats files | Review the diff, stage the changes and retry the commit. CI still checks formatting independently. |
| Preview name exists/inputs rejected | Choose a fresh valid name and explicit counts/seed; no overwrite flag exists. Loading refusal is expected. |
| Contract stale/check failure | Regenerate from source, inspect artifacts and rerun the failing check; do not hand-edit generated files or accept a skipped gate. |

Detailed effects, failure behavior and target mappings are in the
[command registry](commands.md). PD-13 Step 5 exercised this workflow in a fresh private local clone/home/cache
on Linux ARM64, with the tested corrective source overlay recorded in the work
log. Persistent database lifecycle was checked through its original owner clone;
clean migrations used disposable containers. Native platform verification and
final task review remain separate gates.

## Current records

- [Development workstation](development-workstation.md): verified facts for the contributor's local machine.
- [Command registry](commands.md): common project commands and links to current owner guides.
- [Local API foundation setup and tests](../../apps/api/README.md): API-specific commands/settings; the common setup path is above.
- [Secret handling](secret-handling.md): approved references and access procedures, without secret values.
- [Cloud inventory](cloud-inventory.md): shared account, region, resource, and cost status. Update it from approved plans and actual outputs; do not infer or invent cloud facts.
- [DEC-03 resource naming and tags](../decisions/cloud-resource-naming-and-tags.md): verified CLIP resource-name and tag convention; this is a convention, not provisioning approval.

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

Do not put credentials, secret values, personal email addresses, or other sensitive data in names or tags. Include exact names, tag values, expiry/review dates, and any unsupported tagging limitations in the approved plan and resource inventory. These conventions do not authorize creation, modification, adoption, or cleanup of any AWS resource. The selected pattern and required tags are recorded in [DEC-03](../decisions/cloud-resource-naming-and-tags.md).
