# Listings/Images isolated test Terraform root

This root owns only the domain-exclusive image bucket, its access controls, the
Listings ECS runtime and database-setup execution roles, and the bounded test log group. Its state key is
`domains/listings/test/terraform.tfstate` in the existing PD-15 state bucket;
use the default Terraform workspace. It does not adopt or edit the shared API
roles, shared ECS cluster, RDS instance, VPC, or Terraform state bucket.

## Resource design prepared by LI-02 Step 2

| Field | Design |
|---|---|
| Purpose | Store image bytes for the Listings upload/delivery adapter and run the private LI-02 rehearsal. |
| Owner | Listings/Images, Suraj (B); cloud test operator remains a separately named per-window assignment. |
| Terraform root/state | `infra/terraform/domains/listings/test/`; `domains/listings/test/terraform.tfstate`; resources are declared directly in this root, with no reusable module needed for this single environment. Required `test_run_id` fixes the rehearsal's S3 prefix. |
| Data class | Seller-provided listing photos. Treat them as private user content that may accidentally include personal details. No real user data is allowed in the rehearsal. |
| Exposure | Account `335523638354`, Region `ap-south-1`; the image bucket blocks all public access, enforces bucket-owner ownership, uses SSE-S3 and a TLS-only bucket policy. Step 12's website/API route is public over HTTP only while the LI-02 demo is running. It is unauthenticated and accepts synthetic data only. Browser upload CORS is restricted to the exact generated ALB origin. HTTPS is deferred to real integration. |
| Objects and permissions | Bucket `clip-test-listings-images-ap-south-1-li02`; app keys use `listings/test/<test_run_id>/`, where Terraform fixes the selected run ID. The API task role can only get, put, and delete objects under that exact run prefix. The API execution role can pull the reviewed image from the existing shared API ECR repository, write only to this test log group, and read only `/clip/test/listings-database-url`. A separate one-shot database-setup execution role can pull its reviewed image, write to the same bounded log group, and read only `/clip/test/database-master-password` plus `/clip/test/listings-database-url`. Its task definition has no AWS task role. All three roles use the administrator-owned boundary ARN `arn:aws:iam::335523638354:policy/clip/listings/test/CLIPListingsTestRuntimeBoundary`; each inline policy is narrower than that ceiling. |
| Upload/delivery limits | Reuse the reviewed contract: 1–8 JPEG/PNG/WebP images, each 1–10 MiB; controlled object keys; browser upload uses short-lived signed PUT instructions; authorized reads use the existing maximum five-minute signed delivery URL. |
| Retention and cleanup | Do not expire confirmed images by object age during a run: an attached listing may remain active. The Listings cleanup worker deletes an exact pending/failed/retired key only after the database state permits deletion and S3 confirms absence. Preserve retry metadata until then. S3 lifecycle aborts only incomplete multipart uploads after one day. Versioning is disabled. The isolated run uses a dedicated `clip_test_listings` database on the existing shared RDS instance and a run-scoped S3 prefix. The LI-02 stop command removes test rows/objects and drops only `clip_test_listings`; preserve the shared RDS instance and shared `clip_test` database. Before destroying this root, verify the bucket is empty; `force_destroy` stays disabled. |
| Test window and data cap | Reuse the shared ECS/RDS/VPC/NAT foundation; do not create a second RDS instance or network. The public ALB and LI-02 runtime exist only while demonstrating. Enforce at most ten synthetic listings in the isolated test profile and retain the existing 1–8 image, 10 MiB per-image contract (up to 800 MiB across ten full listings). There is no fixed two-hour test duration; the operator starts the demo for verification/showing and runs stop when done. Refresh current shared-account spend, credit eligibility, and exact ALB/runtime costs before Step 12 approval. Shared RDS/network/storage costs continue outside LI-02 and are not represented as demo teardown savings. |
| Rollback | Stop public ingress, clean the isolated Listings database and run prefix, remove LI-02 runtime resources and LI-02-owned logs/images, then verify no demo task or endpoint remains. Never delete shared RDS/VPC/NAT or another domain's ECR images/resources. Restoring the RDS start/stop state is a separate approved operation; it must preserve the captured baseline and must not disrupt a new shared consumer. Prepare a fresh destroy plan for this root only after the bucket is verified empty; never use `force_destroy`. |

The local browser uploads directly to S3 using a Listings-issued URL that is
valid for at most five minutes and requires the signed `Content-Type` and
`If-None-Match: *` headers. The bucket policy denies PUT requests under the
current test-run prefix if the create-only condition is missing, and CORS
allows the browser to send that header from the exact configured origin. For
Step 12, Terraform uses the generated ALB HTTP origin. The bucket remains
private, object requests use HTTPS, and IAM remains the authority for access.

The isolated cloud API may enable its fixed seller only with
`CLIP_ISOLATED_LISTINGS_TEST_CALLER=true` and
`CLIP_DEVELOPMENT_AUTH=true`. Settings also require `CLIP_ENVIRONMENT=test`,
database URL path `clip_test_listings`, the exact private test bucket and
`ap-south-1` region, and a single-segment `listings/test/<test_run_id>` prefix.
The API database URL must use the dedicated login `clip_test_listings_app`,
and `CLIP_ISOLATED_LISTINGS_MAX_COUNT=10` enables the serialized database cap.
On startup, the API checks the connected database and both the login/effective
role names; it refuses to serve this caller outside `clip_test_listings` or
when the role is a superuser, can create databases or roles, can replicate, or
can bypass row security. The one-shot setup task must create this login as a
non-elevated owner of only the isolated database. The caller is a source-fixed
UUID (`10000000-0000-4000-8000-000000000001`); it reads
no request header, query, cookie, or body field. The separate setup step must
seed that one regular synthetic row in `clip_test_listings` before the API
starts. Request models reject extra fields, including a client-supplied owner
ID. Production settings reject this profile flag, and shared deployment must
leave it false while using the real Identity caller.

## Isolated public app route and demo lifecycle for Step 12

Step 12 serves the built Listings website and its API from ECS in the existing
`clip-shared-test` cluster. The browser must not depend on a Vite server or
proxy running on the operator's laptop. A public load balancer routes the
website and API over one reviewed origin; desktop and phone use the same URL.
Use the ALB's generated HTTP hostname for the isolated demo. The demo has no sign-in flow:
while it is running, visitors use the same fixed synthetic seller. The page
must identify the environment as a demo and must not accept real user data.
Backend enforcement caps the isolated test database at ten synthetic listings;
the cap is unavailable in shared/production profiles. Existing per-listing
image limits remain 1–8 images, 10 MiB maximum each.

The app container serves its bundled UI from `/` and the API under `/api`; its
health endpoint remains `/health`. Runtime static serving is enabled only
alongside the isolated caller. The build marks the isolated demo disclosure in
the Listings UI, while development-only synthetic helper endpoints remain
compiled out of the deployed bundle.

The API task uses this root's API task/execution roles and the exact
`/clip/test/listings-database-url` SecureString reference. The API execution
role is also used by the fixed one-shot migration task, which has no task role.
A separate fixed one-shot database-setup task uses the database-setup execution
role and the existing RDS master secret only to create/drop the dedicated
`clip_test_listings` database and login. It does not receive AWS credentials
inside the container. Startup, migration, and cleanup commands are fixed in
reviewed task definitions rather than supplied as arbitrary ECS overrides.
The database URL is never put in Terraform state, output, tags, or logs.
Build the website/API and database-task artifacts from one selected source
revision and pin deployments by immutable digest. The migration task uses the
repository's pinned migration tool/version and checked-in migrations.

The test profile rejects client-supplied owner IDs and refuses startup unless
it is in `clip_test_listings` with the least-privilege application role. The
caller remains source-fixed and production settings reject the profile.
S3 stays private; short-lived signed uploads and reads use the existing
run-scoped prefix and role permissions. Bucket CORS allows only the exact
deployed HTTP origin and `If-None-Match: *` upload header.

The lifecycle commands are registered as
`make li02-demo-start AWS_PROFILE=<approved-profile>` and
`make li02-demo-stop AWS_PROFILE=<approved-profile>`. They are implemented but
have not been exercised against AWS. Start requires clean committed build
inputs, preflights account/region, budget, shared task use, and state, captures
the RDS and ECS capacity baselines in an ignored non-secret local file, and
builds/pushes uniquely tagged images from that immutable source. It creates the
database URL as one SecureString without printing its value, creates the ALB
and fixed task definitions with the app count at zero, bootstraps only
`clip_test_listings`, applies the checked-in migrations, seeds one fixed
synthetic seller, then enables the app and prints the ALB URL. Each Terraform
saved plan is displayed with a SHA-256 and requires that exact text to be typed
before apply. RDS start is a separate exact prompt when it was stopped at
baseline. No custom domain or subdomain is needed for this HTTP endpoint.

Stop scales the LI-02 service to zero, drops only the isolated Listings
database/login, removes the exact S3 run prefix and the database URL parameter,
then uses a reviewed plan to remove the temporary ALB, subnet/route, host
ingress rule, ECS service and task definitions. It deletes only unreferenced
LI-02 ECR image digests and clears LI-02 log streams. It preserves the Step 4
empty image bucket, IAM roles, empty log group, state backend, shared RDS and
`clip_test` database, VPC, NAT, ECS cluster/capacity provider, and other
domains' artifacts. It never deletes or Terraform-manages a shared resource.
When no other task/session depends on shared capacity or RDS, stop waits for
the recorded ECS capacity baseline and may restore the shared RDS stopped state
after its idle check and separate exact prompt. If another workload appears or
the capacity check fails, leave shared resources available and report the
difference. Shared foundation costs continue while the demo is off.

If interrupted, retain the ignored baseline file and resume with `stop`; it
contains no credentials. Do not infer cloud state from the file alone: refresh
the account inventory and review Terraform/AWS state before any manual recovery.

The app uses the existing RDS instance only while available. If it was stopped
at baseline, start may bring it up only under its separate approved operation;
stop restores the prior state only after checking there is no other shared
consumer. Human
mobile verification happens after deployment using the phone's browser over
the same public URL; no Wi-Fi, hotspot, WSL forwarding, or separate camera
behavior check is required. Record desktop upload and mobile website/image-flow
observations separately. Have Security review public exposure, the fixed
synthetic caller, ten-listing cap, logs, teardown, and current costs. This
remains an isolated rehearsal and does not accept ID-READY, LI-CORE, real
authentication, or full LI-02 integration.

## Operator access for self-operated LI-02

The live account check on 2026-10-21 confirmed that `surajs2` has direct
`IAMFullAccess` and the read-only billing policies, and receives
`PowerUserAccess` plus `CLIPParameterStoreTeamAccess` from
`DS252-Project-Developers`. The exact Listings Terraform state prefix was
empty. The existing Parameter Store policy covers `/clip/*`; IAMFullAccess
covers Terraform's IAM role operations. The initially prepared, narrower
[`operator-iam-policy.json`](operator-iam-policy.json) is therefore not
required while IAMFullAccess remains attached. No additional standing AWS
permission is currently identified through LI-02 Step 12; exact plans, run
windows, security review, and cleanup still have their own approval gates.

Suraj created the customer-managed runtime boundary from
[`runtime-role-boundary.json`](runtime-role-boundary.json) at
`arn:aws:iam::335523638354:policy/clip/listings/test/CLIPListingsTestRuntimeBoundary`
on 2026-10-21 (default version `v1`). Terraform applies this boundary to the
three Listings roles it creates. It limits those task roles to the S3 image
path, ECR image pull, bounded logs, and exact database parameters they need;
only the one-shot setup execution role may read the RDS master parameter. The
boundary grants no permissions to `surajs2`. Step 3's original plan has been
applied and verified. Any later Terraform update, including the Step 4
conditional-write policy change, still needs its own exact-plan review and
approval before apply. Step 12 adds task definitions and a service that use
these already planned roles; no additional IAM role is planned there.

## Keeping the later shared switch small

The API, migration, and database-setup artifacts are built from a selected
source revision and pinned by ECR digest. The isolated rehearsal selects its
dedicated database URL, run-scoped bucket prefix, local browser origin, and
fixed synthetic seller through explicit test configuration. The test caller
must reject a browser-supplied owner ID and fail startup unless the process is
in the isolated test target. It must be impossible to enable that caller in
the shared or production profile.

Shared integration must use the same Listings service behavior and storage
adapter interfaces, with configuration selecting the approved shared database
and bucket and real Identity supplying the trusted caller. The shared target
must never seed the isolated synthetic identity or enable the test caller.
Those provider/configuration changes and guards are implemented in LI-02
Steps 4–11; this infrastructure design prepares the isolated profile and keeps
Step 12 from requiring new IAM roles. The later shared deployment still needs
its own reviewed configuration and run plan.

No backend initialization, Terraform plan, AWS mutation, upload, database
write, deployment, or cleanup is performed by Step 2. Step 3 owns exact-plan
review and apply approval. Step 12 adds the public endpoint and ECS service,
then verifies the browser, API, database and image paths against the approved
target.
