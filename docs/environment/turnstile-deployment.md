# Turnstile sign-in recovery: deployment handoff

This prepares the combined #52/#65 fix. It does not authorize an AWS write,
Terraform apply, image publication or deployment. Follow the existing
[Terraform rollout process](../../infra/terraform/README.md) and
[secret-handling rules](secret-handling.md) with the current approved inputs.

## Build versus runtime

| Input | Where it belongs | Safe to share? |
|---|---|---|
| `VITE_MICROSOFT_SIGN_IN_ENABLED=true` | Build argument for the ordinary API image's web stage | Yes; existing Microsoft activation flag |
| Production Turnstile site key | Terraform `turnstile_site_key`; injected as backend `CLIP_TURNSTILE_SITE_KEY` | Public; safe in the handoff fragment |
| Production Turnstile secret key | Standard SSM SecureString `/clip/test/turnstile/secret-key`; ECS injects backend `CLIP_TURNSTILE_SECRET_KEY` | Never send in chat/email, commit, image or Terraform input/state |
| Local-test widget keys | Private developer-only files | Keep separate; never deploy them |

There is no Turnstile build argument or `VITE_*` secret. The backend advertises
the public widget key only when a sign-in is refused with a challenge-marked 429.
The browser obtains a token; the backend verifies it using the secret.

The deployed module is named `shared/test` and uses account `335523638354`, Region
`ap-south-1`, and website `clip-iisc.site`. “Production widget” here means the widget
for that public website, not the separate `localhost` widget. This does not create
a new AWS production environment or change existing resource ownership.

## One-time preparation by the key holder

1. In Cloudflare, confirm the **website widget** allows `clip-iisc.site`, uses
   Managed mode, and has pre-clearance disabled. Keep the separate local-test
   widget for `localhost`. Use the matching website site/secret pair.
2. Keep those keys in a private owner-only JSON file outside Git:
   `{"site_key":"...","secret_key":"..."}`. Do not paste real values into a
   shell command. The existing hidden-input setup helper may be used; restrict
   the resulting file with `chmod 600` if necessary.
3. Prepare the non-secret handoff locally, from the repository root:

   ```bash
   uv run --locked python scripts/prepare_turnstile_deployment.py \
     --keys-file /absolute/private/path/keys.json \
     --output /absolute/private/path/turnstile-handoff
   ```

   This makes **no AWS calls**. It writes `turnstile.tfvars.json` containing only
   the public `turnstile_site_key`, plus `handoff.json` with the exact parameter
   reference and whether an AWS write was performed. A local receipt with
   `aws_write_performed: false` does not establish that the parameter exists.
4. After approval of the exact AWS write, the key holder can run the same helper
   with their own logged-in project profile:

   ```bash
   uv run --locked python scripts/prepare_turnstile_deployment.py \
     --keys-file /absolute/private/path/keys.json \
     --output /absolute/private/path/turnstile-handoff \
     --write-secret --profile YOUR_OWN_PROJECT_PROFILE
   ```

   This uses your existing AWS CLI login, checks STS account identity before
   writing, then creates exactly one
   **Standard SecureString** in `ap-south-1`, using the default AWS-managed
   `aws/ssm` key. It does not overwrite an existing parameter, change IAM, deploy,
   or retry a failed write. It passes the secret through a seekable Linux memory-only descriptor without a
   temporary disk payload file, captures private CLI diagnostics and uses fixed regional
   AWS endpoints with bounded timeouts. Stop on failure; inspect the parameter privately
   before retrying, because a timeout may still have committed the creation.
   Rotating/replacing an existing value is a separate approved operation.
5. Give the collaborator the branch/reviewed revision, this guide, and the two
   **non-secret handoff files**. Once SSM creation is confirmed, they do not need
   the raw secret. Each operator uses their own AWS identity; do not share cached
   AWS credentials. IAM access to the parameter is still required for operators
   who administer it, and ECS receives the exact runtime read permission below.

The secret stays in AWS until a task starts. It is injected into that container's
environment, not made public. Operators with permission to inspect the container
can access runtime secrets; never dump process environments or task-exec output.

## Deploying the reviewed revision

1. Preserve all existing reviewed rollout settings: Hybrid image/artifacts,
   database/proxy settings, Microsoft activation, Conversations, notifications,
   capacity and rollback image. The small public tfvars fragment is **additional**
   configuration, not a replacement for the environment's complete input set.
2. Build the normal web/API image from the exact reviewed commit using the
   existing `--build-arg VITE_MICROSOFT_SIGN_IN_ENABLED=true`. If the deployment
   uses `Dockerfile.hybrid`, extend that newly built API image using the existing
   pinned semantic-artifact procedure; the Hybrid Dockerfile inherits the web
   bundle from its `API_IMAGE`. Do not rebuild a reduced/non-Hybrid image as a
   substitute. No Turnstile key is passed to either build stage.
3. Confirm the SecureString exists at the exact ARN below and uses the expected
   website widget's secret. Do not print its decrypted value as evidence:

   ```text
   arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/turnstile/secret-key
   ```

4. **One-time change to the maintained environment inputs:** copy the single
   public `turnstile_site_key` setting from the handoff into the same input file
   already used by the normal deployment commands. Keep it there for every later
   plan. Then the usual build/push/plan/apply command sequence can continue.
   Alternatively, supply the public fragment as an additional `-var-file` every
   time, as illustrated below. Do not replace the existing complete input file.
   This opt-in requires `identity_runtime_enabled=true`. Omitting the key selects
   null, proposes removing the runtime challenge configuration/permission and
   does **not** preserve complete recovery.
5. Review that the plan:
   - injects public `CLIP_TURNSTILE_SITE_KEY` in the API runtime environment;
   - injects `CLIP_TURNSTILE_SECRET_KEY` through the exact SSM `secrets.valueFrom`;
   - grants only `ssm:GetParameters` on that parameter to the **API execution
     role**, not the application task role, proxy or Lambda read runtime;
   - retains the existing capacity, network, storage, databases, providers and
     workload settings, apart from separately approved image changes;
   - creates no secret value in Terraform and performs no unrelated deletions.
6. Obtain approval of that concrete plan, then apply and deploy the matching
   frontend/backend image together. No database migration is needed for this fix.
   ECS must start new tasks to receive injected keys. Updating an SSM value alone
   does not refresh already-running containers; use a separately approved rollout.

An EC2 host running the **ECS task** receives the configuration from ECS; nothing
needs adding to the host's shell profile. A standalone Docker run outside ECS
would require its own reviewed runtime secret-injection procedure. This guide
does not authorize a plaintext secret in `docker run` command arguments.

## Commands in the existing rollout workflow

There is no one-command `make deploy` target. The existing
[Terraform workflow](../../infra/terraform/README.md#3-prepare-and-review-an-exact-plan)
owns plan review and applying the exact approved saved plan. The
[shared/test guide](../../infra/terraform/shared/test/README.md#application-rollout-start-here)
is the target-specific entry point; the
[command index](commands.md) links image/build and runtime procedures.

If the public setting has been added to the maintained environment inputs, use
those existing rollout commands unchanged. If using the separate handoff file,
the only extra plan argument is the second `-var-file` below. Replace all paths
with the current private input/plan paths, preserve the environment's complete
settings, and select the newly reviewed image URI through the existing input
process. These are instructions for a separately approved cloud operation:

```bash
terraform -chdir=infra/terraform/shared/test plan -input=false \
  -var-file=/absolute/private/path/current-environment.tfvars \
  -var-file=/absolute/private/path/turnstile-handoff/turnstile.tfvars.json \
  -out=/absolute/private/path/turnstile-rollout.tfplan

sha256sum /absolute/private/path/turnstile-rollout.tfplan
terraform -chdir=infra/terraform/shared/test show -no-color \
  /absolute/private/path/turnstile-rollout.tfplan
```

Review that private plan and obtain approval for its exact checksum and changes.
Only after that approval, use the normal saved-plan apply:

```bash
terraform -chdir=infra/terraform/shared/test apply \
  /absolute/private/path/turnstile-rollout.tfplan
```

Creating the SSM parameter by itself does not update ECS. Building/pushing a new
image by itself does not create the parameter or grant access. Once the initial
runtime setup is applied, later image rollouts retain it through the maintained
Terraform inputs and existing deployment process. Never reuse a historical
saved plan or omit current required inputs to simplify this step.

## Smoke checks and rollback

Check normal temporary login and Microsoft SSO first; neither should contact
Turnstile below the thresholds. In an approved bounded test-account window,
verify challenge-backed recovery from email and shared-IP limits, including
Microsoft redirect completion. Confirm a signed-in neighbour stays usable,
onboarding/messaging key checks work, and wrong credentials still fail. Do not
flood public traffic without the separate test-window approval. Use an ordinary
browser: the automated Chromium challenge failed before resubmission, whereas
the human-operated ordinary browser completed the real-provider local checks.

A missing parameter or execution-role permission can prevent a new ECS task from
starting. A wrong widget pair or hostname can fail challenged sign-ins even if
`/health` passes. Keep the last healthy task/image available and inspect sanitized
startup/provider symptoms. Rolling back to the old image/settings also rolls back
the #52/#65 recovery; report that explicitly. Do not delete/rotate keys as an
automatic rollback step. Do not close the issues before the required red-team
retest and acceptance.

## Free-plan limits

Checked 2026-11-17 against [Cloudflare's plan documentation](https://developers.cloudflare.com/turnstile/plans/):
the free plan permits up to **20 widgets**, **10 hostnames per widget**, unlimited
challenges/verification requests, and at most **seven days of analytics**. It does
not include unrestricted-hostname widgets, Ephemeral IDs or branding removal.
The website and local-test widgets use two slots. Provider plan limits can change;
recheck before relying on them for a later expansion. These limits do not promise
immunity to automated abuse or continuous provider availability.

AWS injection/reference behavior is documented in
[ECS Parameter Store environment secrets](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-ssm-paramstore.html).


## OTP recovery extension (#78)

The same runtime site/secret pair now also protects temporary registration and
password reset, including final OTP completion when rate limited. No new widget,
SSM parameter, IAM permission or image build argument is needed. Existing
hardened-runtime configuration remains mandatory for recovery. After rollout,
verify normal first-code delivery, guarded resend/security-check completion,
account creation and password reset; a proof does not replace the emailed code.
Provider failure must leave the action refused and retryable. See the
[OTP recovery decision](../decisions/otp-and-conversation-recovery-isolation.md).
