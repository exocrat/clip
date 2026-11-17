# Release deployment runbook: AMD64 build on an SSM-driven builder → ECR → Terraform

This is the end-to-end procedure for deploying a reviewed CLIP revision (for
example the integration branch, once verified and merged to `main`) to the
`shared/test` environment at <https://clip-iisc.site>.

It consolidates the authoritative pieces that already live in the repo:
- the bounded AMD64 image build in [`scripts/identity_amd64_build.sh`](../../scripts/identity_amd64_build.sh);
- the Turnstile runtime handoff in [`turnstile-deployment.md`](./turnstile-deployment.md);
- the Terraform rollout in [`infra/terraform/shared/test/README.md`](../../infra/terraform/shared/test/README.md)
  and the general [Terraform workflow](../../infra/terraform/README.md).

> **This document describes a separately approved cloud operation.** It does not
> authorize any AWS write, image publication, Terraform apply, secret read or
> deployment. Each cloud step below needs its own explicit approval of the exact
> command/plan. Never print a decrypted secret as evidence.

## 0. Why the build runs on a remote host

The deployed serving image is **`linux/amd64` (x86-64)**. A developer workstation
on **ARM64** (e.g. a Raspberry Pi) cannot build or validate that image natively,
and emulated builds are not an approved path. The build therefore runs on an
**approved x86-64 EC2 host, driven entirely through AWS Systems Manager Run
Command (`aws ssm send-command`) — there is no SSH.** The image is produced and
saved there, then published to ECR, then selected by Terraform.

## 1. Fixed inventory

| Thing | Value |
|---|---|
| AWS account | `335523638354` |
| Region | `ap-south-1` |
| Operator profile | `adityalaxmi1` (use your own logged-in project profile; do not share cached creds) |
| ECR repository (API) | `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api` (immutable digests) |
| x86-64 builder host | an approved build instance driven via SSM — `i-086045c48487471de` was used previously; **confirm the current builder instance ID before use** (`aws ec2 describe-instances`) |
| Terraform root | `infra/terraform/shared/test` |
| Dockerfile | `apps/api/Dockerfile` (the Hybrid image layers on this API image) |

The builder host must be `x86_64`, have Docker, run the build as root, have
≥10 GiB free in the run directory and swap headroom (the build script enforces
all of these and fails closed otherwise).

## 2. Build-time feature flags (web bundle)

These are **`docker build --build-arg` values**, baked into the web bundle at
build time. The Dockerfile defaults both VITE flags to `false`, so Microsoft SSO
must be explicitly enabled:

| Build arg | Value for this release | Effect |
|---|---|---|
| `VITE_MICROSOFT_SIGN_IN_ENABLED` | **`true`** | Enables the Microsoft SSO sign-in path in the built web bundle. Default `false` ⇒ without this, the deployed site has no Microsoft sign-in button. |
| `VITE_LISTINGS_PUBLIC_DEMO` | `false` | Keeps the synthetic public demo off in production. |
| `CLIP_WEB_BUILD_NODE_OPTIONS` | `--max-old-space-size=768` | Bounds the web build's Node heap on the small builder. |

There is **no Turnstile build arg**. The Turnstile site key is a *runtime*
environment value injected by Terraform (see §6), not baked into the image.

## 3. Prepare the source archive (local, no cloud)

Pick the exact reviewed commit (the merged `main` revision) and record its SHA.
Produce the allowlisted build context as a tar — the build script only accepts
these paths:

```bash
REV=$(git rev-parse HEAD)            # the reviewed, merged commit
git archive --format=tar --output=/tmp/clip-src-"${REV:0:12}".tar "$REV" \
  apps/api/app apps/web contracts/generated \
  pyproject.toml uv.lock package.json package-lock.json \
  apps/api/Dockerfile apps/api/Dockerfile.dockerignore
sha256sum /tmp/clip-src-"${REV:0:12}".tar   # record this; the builder verifies it
```

(The build script's extractor rejects anything outside `apps/api/app/`,
`apps/web/`, `contracts/generated/` plus those exact files, and rejects
traversal/symlinks and oversized input.)

## 4. Transfer the source to the builder (via SSM)

Stage the archive onto the builder as `/var/tmp/clip-id01-build-<rev12>/source.tar`
using a bounded SSM Run Command transfer (the same loopback/base64-chunk transfer
helper pattern used previously). The run directory **must** be named exactly
`/var/tmp/clip-id01-build-${REV:0:12}` or the build script refuses to run.

All builder commands follow this shape:

```bash
aws ssm send-command \
  --instance-ids <BUILDER_INSTANCE_ID> \
  --document-name AWS-RunShellScript \
  --parameters '{"commands":["<bounded shell>"]}' \
  --timeout-seconds <bounded> --max-concurrency 1 --max-errors 0 \
  --comment '<what this does>' \
  --profile adityalaxmi1 --region ap-south-1 \
  --query 'Command.CommandId' --output text
# then poll:
aws ssm get-command-invocation --command-id <ID> --instance-id <BUILDER_INSTANCE_ID> \
  --profile adityalaxmi1 --region ap-south-1
```

Verify on the builder that `source.tar` matches the sha256 recorded in §3 before
building.

## 5. Build and validate the AMD64 image on the builder (via SSM)

Run the reviewed build script on the builder. It does **not** call AWS and does
**not** push — it builds, validates and `docker save`s a local image + a
`result.json` receipt:

```bash
# sent via aws ssm send-command (AWS-RunShellScript), as root on the builder:
sudo /path/to/repo/scripts/identity_amd64_build.sh \
  /var/tmp/clip-id01-build-<rev12> <SOURCE_TAR_SHA256> <FULL_40_CHAR_REVISION>
```

What it does (for reference — see the script for the exact bounds):
- extracts the allowlisted context;
- `DOCKER_BUILDKIT=0 docker build --platform linux/amd64` with
  `--build-arg VITE_MICROSOFT_SIGN_IN_ENABLED=true`,
  `--build-arg VITE_LISTINGS_PUBLIC_DEMO=false`,
  `--build-arg CLIP_WEB_BUILD_NODE_OPTIONS=--max-old-space-size=768`;
- asserts the image is `amd64`/`linux`, runs as user `10001`, and passes a
  bounded `/health` + bundled-UI check with `CLIP_SERVE_WEB_APP=true`;
- `docker save`s to `image.tar` and writes `result.json` with the image id,
  archive sha256 and `registry_published: false`.

Record `result.json` (source commit, image id, archive sha256).

## 6. Publish the image to ECR (separate approval)

Publication is a distinct approved operation; the build script deliberately does
not do it. On the builder (which holds the built image), authenticate to ECR and
push under an **immutable, commit-derived tag**:

```bash
# on the builder, via SSM, after approval of this exact push:
aws ecr get-login-password --region ap-south-1 --profile adityalaxmi1 \
  | docker login --username AWS --password-stdin 335523638354.dkr.ecr.ap-south-1.amazonaws.com
docker tag clip-api:id01-<rev12> \
  335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api:api-<REVISION_SHA>
docker push \
  335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api:api-<REVISION_SHA>
```

Record the **pushed manifest digest** (`aws ecr describe-images … --image-ids
imageTag=api-<SHA>`); Terraform selects the image by digest. The repository uses
immutable tags, so never reuse a tag. If the Hybrid runtime is in use, extend the
newly built API image with the existing pinned semantic-artifact procedure rather
than building a reduced non-Hybrid substitute; the Hybrid Dockerfile inherits the
web bundle (and therefore the VITE flags) from its `API_IMAGE`. The Lambda image,
if being rolled, is built/published separately (see
[`scripts/evaluation/build_lambda_image.sh`](../../scripts/evaluation/build_lambda_image.sh)
and the deployment plan) under `exp03-lambda-<SHA>`.

## 7. Terraform rollout (separate approval)

The site key opt-in and the new image URI are supplied to Terraform through the
**existing private environment input set** — not the repo. See
[`turnstile-deployment.md`](./turnstile-deployment.md) for the full detail; the
shape is:

```bash
terraform -chdir=infra/terraform/shared/test plan -input=false \
  -var-file=/your/private/current-environment.tfvars \
  -var-file=/your/private/turnstile.tfvars.json \
  -out=/your/private/release.tfplan
sha256sum /your/private/release.tfplan
terraform -chdir=infra/terraform/shared/test show -no-color /your/private/release.tfplan
# review, get approval of the exact checksum/changes, then:
terraform -chdir=infra/terraform/shared/test apply /your/private/release.tfplan
```

Select the new image **digest** from §6 through the environment's existing image
input. Review that the plan:
- updates the API task to the new image digest;
- injects public `CLIP_TURNSTILE_SITE_KEY` and references `CLIP_TURNSTILE_SECRET_KEY`
  via SSM `secrets.valueFrom` (only when the site key is set — see §8);
- grants `ssm:GetParameters` on that one parameter to the **API execution role**;
- retains capacity, network, storage, databases, providers and unrelated settings;
- creates no secret value in Terraform and performs no unrelated deletions.

**ECS must start new tasks** to pick up a new image *and* newly injected env/secrets.
An image-only push, or an SSM value change alone, does not refresh running tasks.

## 8. Turnstile key nuances (read before enabling)

"The turnstile key" is **two different keys**:

| Key | Secret? | Where it lives | Status |
|---|---|---|---|
| **Secret key** (verifier) | Yes | SSM SecureString `/clip/test/turnstile/secret-key` (`ap-south-1`, `aws/ssm` KMS, Standard tier) | ✅ provisioned v1 by `surajs2`, independently verified (metadata only) |
| **Site key** (widget) | No (public) | Terraform variable `turnstile_site_key` → runtime env `CLIP_TURNSTILE_SITE_KEY` | ⬜ supplied at apply from your private deploy inputs (the public widget key; its value is in PR #72) |

Key points:
- The **secret stays in SSM** exactly as it is — that is correct and done. It is
  never passed to Terraform, a build arg, an image, or chat/email.
- The site key is **public** and is a Terraform **variable**, not an SSM value.
  Putting it in SSM would require rewriting `turnstile.tf` and is unnecessary.
- The **entire Turnstile block is gated**: `turnstile_enabled = var.turnstile_site_key != null`.
  Until the site key is supplied, the secret reference, the `ssm:GetParameters`
  IAM grant and the recovery behaviour are all **off** — the SSM secret just sits
  unused. Supplying the site key is what turns the feature on.
- A Terraform **precondition** requires `identity_runtime_enabled = true` when
  Turnstile is enabled (fake auth is not an integration path).
- Keep `turnstile_site_key` in the **maintained private deploy inputs** for every
  later plan; the variable's default stays `null` in the repo.

The public fragment (`turnstile.tfvars.json`) is simply:

```json
{ "turnstile_site_key": "<public-widget-key; value in PR #72 / your deploy inputs>" }
```

## 9. What a deploy resolves

A plain deploy of the merged revision (Turnstile **off**) resolves: #53, #55,
#57, #58, #59, #60, #62, #63, **#65 request-rate isolation**, #66, #69, #71.

**#52** (email-keyed sign-in lockout) and the **#65 sign-in variant** (per-IP
sign-in cap) are only mitigated when **Turnstile is enabled** (the challenge
bypass in `sessions.py`). Enabling Turnstile = supplying the site key in §7–§8
with the SSM secret already present. Microsoft SSO on the site requires the
`VITE_MICROSOFT_SIGN_IN_ENABLED=true` build arg from §2.

## 10. Smoke checks and rollback

Follow [`turnstile-deployment.md` §Smoke checks](./turnstile-deployment.md):
verify normal temporary login and Microsoft SSO first (neither contacts Turnstile
below thresholds), then, in an approved bounded test-account window, verify
challenge-backed recovery from the email and shared-IP limits, that a signed-in
neighbour on the same IP stays usable, and that wrong credentials still fail. Use
an ordinary browser (automated Chromium failed to obtain a real widget token).

Keep the last healthy task/image for rollback. Rolling back to the old
image/settings also rolls back the #52/#65 recovery and Microsoft SSO — report
that explicitly. Do not delete or rotate the Turnstile secret as a rollback step.
Do not close #52/#65 before the required red-team retest and acceptance.
