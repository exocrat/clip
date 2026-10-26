# Listings/Images isolated test Terraform root

This root owns the domain-exclusive image bucket, its access controls, the
disposable LI-02 database, the dedicated Listings ECS cluster/capacity,
database-setup execution roles, and the bounded test log group. Its state key is
`domains/listings/test/terraform.tfstate` in the existing PD-15 state bucket;
use the default Terraform workspace. It does not adopt or edit the shared API
roles, shared ECS cluster or capacity provider, shared RDS instance, VPC, or
Terraform state bucket.

## Resource design prepared by LI-02 Step 2

The current selected runtime and RDS-AZ design is recorded in
[`DEC-13`](../../../../../docs/decisions/li02-isolated-ecs-runtime.md).

| Field | Design |
|---|---|
| Purpose | Store image bytes for the Listings upload/delivery adapter and run the private LI-02 rehearsal. |
| Owner | Listings/Images, Suraj (B); cloud test operator remains a separately named per-window assignment. |
| Terraform root/state | `infra/terraform/domains/listings/test/`; `domains/listings/test/terraform.tfstate`; resources are declared directly in this root, with no reusable module needed for this single environment. Required `test_run_id` fixes the rehearsal's S3 prefix. |
| Data class | Seller-provided listing photos. Treat them as private user content that may accidentally include personal details. No real user data is allowed in the rehearsal. |
| Exposure | Account `335523638354`, Region `ap-south-1`; the image bucket blocks all public access, enforces bucket-owner ownership, uses SSE-S3 and a TLS-only bucket policy. Step 12's website/API route is public over HTTP only while the LI-02 demo is running. It is unauthenticated and accepts synthetic data only. Browser upload CORS is restricted to the exact generated ALB origin. HTTPS is deferred to real integration. |
| Objects and permissions | Bucket `clip-test-listings-images-ap-south-1-li02`; app keys use `listings/test/<test_run_id>/`, where Terraform fixes the selected run ID. The API task role can only get, put, and delete objects under that exact run prefix. The API execution role can pull the reviewed image from the existing shared API ECR repository, write only to this test log group, and read only `/clip/test/listings-database-url`. A separate one-shot database-setup execution role can pull its reviewed image, write to the same bounded log group, and read only `/clip/test/database-master-password` plus `/clip/test/listings-database-url`. Its task definition has no AWS task role. All three roles use the administrator-owned boundary ARN `arn:aws:iam::335523638354:policy/clip/listings/test/CLIPListingsTestRuntimeBoundary`; each inline policy is narrower than that ceiling. |
| Upload/delivery limits | Reuse the reviewed contract: 1–8 JPEG/PNG/WebP images, each 1–10 MiB; controlled object keys; browser upload uses short-lived signed PUT instructions; authorized reads use the existing maximum five-minute signed delivery URL. |
| Retention and cleanup | Do not expire confirmed images by object age during a run: an attached listing may remain active. The Listings cleanup worker deletes an exact pending/failed/retired key only after the database state permits deletion and S3 confirms absence. Preserve retry metadata until then. S3 lifecycle aborts only incomplete multipart uploads after one day. Versioning is disabled. Each rehearsal uses the dedicated disposable `clip-test-listings-ap-south-1-li02` RDS instance, creates `clip_test_listings` inside it, and uses a run-scoped S3 prefix. Stop runs the owner-check cleanup, empties the run prefix, then destroys the disposable RDS without a final snapshot; shared RDS and its `clip_test` database remain untouched. Before destroying this root, verify the bucket is empty; `force_destroy` stays disabled. |
| Test window and data cap | Use a dedicated LI-02 ECS cluster, capacity provider, and ASG-backed private EC2 host; reuse the shared VPC, private workload subnet, NAT, ECR repository, and state backend without changing the shared ECS cluster/provider or shared ASG. The LI-02 ASG has min/desired capacity 0 and max 1. It launches one `c7i-flex.large` only while the demo runs, with a 30 GiB gp3 root volume deleted on instance termination. Stop returns the ASG to 0 and verifies that the instance and root volume are gone; the empty LI-02 cluster, provider, and ASG may remain for quick restart and have no EC2/ECS compute charge. Try the disposable Single-AZ PostgreSQL 18.6 `db.t4g.micro` in `ap-south-1b` first; only after AWS reports insufficient capacity, prepare an exact-plan fallback for `ap-south-1a`. Each distinct plan requires its own hash review and approval; if a failed apply leaves an RDS instance or ambiguous state, stop and inspect rather than retry automatically. The RDS instance uses 20 GiB encrypted gp3 storage in a private subnet and matches the shared test foundation's engine version. The RDS and storage exist only while the LI-02 demo is on; stop deletes the instance and storage. The public ALB also exists only while demonstrating. Enforce at most ten synthetic listings and retain the existing 1–8 image, 10 MiB per-image contract (up to 800 MiB across ten full listings). There is no fixed two-hour test duration; the operator starts the demo for verification/showing and runs stop when done. Refresh current shared-account spend and exact RDS/ALB/runtime costs before Step 12 approval. Shared RDS/network/storage costs continue outside LI-02 and are not represented as demo teardown savings. |
| Rollback | Stop public ingress, clean the disposable Listings database and run prefix, remove LI-02 demo resources, terminate the dedicated host and delete its root volume, then verify no demo task, endpoint, RDS instance, or database remains. Keep the empty LI-02 ECS cluster/capacity provider/ASG at zero unless a separate reviewed plan removes them. Never delete shared RDS/VPC/NAT/ECS cluster/capacity provider or another domain's ECR images/resources. The stop plan deletes only the LI-02-owned RDS instance and its data; no shared RDS or ECS state is changed. Prepare and review the exact plan before apply; never use `force_destroy` for the image bucket. |

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

**Selected Step 2 design, implemented in the LI-02 Step 12 Terraform and
lifecycle driver:** use a dedicated LI-02 ECS cluster and ASG-backed EC2
capacity. The shared ECS cluster, capacity provider, ASG, and host security
group are not Terraform-managed or used by the demo service.

Step 12 serves the built Listings website and API from ECS in the dedicated
LI-02 cluster, using only LI-02's capacity provider and host security group.
The shared ECS cluster, provider, ASG, and host security group remain unchanged.
The browser must not depend on a Vite server or proxy running on the operator's
laptop. A public load balancer routes the
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
role and the approved `/clip/test/database-master-password` parameter only
against the disposable LI-02 RDS instance. Terraform passes its value through
an ephemeral variable to RDS's write-only `password_wo` argument; the value is
not stored in the plan or state, and the parameter itself is not changed. The
setup task does not receive AWS credentials inside its container. Startup,
migration, and cleanup commands are fixed in reviewed task definitions rather
than supplied as arbitrary ECS overrides. The database URL is never put in
Terraform state, output, tags, or logs.
Build the website/API and database-task artifacts from one selected source
revision and pin deployments by immutable digest. The migration task uses the
repository's pinned migration tool/version and checked-in migrations.

The private ECS host uses a dedicated EC2 instance role with the AWS-managed
ECS container-instance policy. Its security group accepts the app port only
from the temporary ALB and sends outbound traffic through the existing private
subnet/NAT. The host has IMDSv2 required and an encrypted 30-GiB gp3 root disk
tagged for exact teardown verification; its launch template sets the dedicated
LI-02 cluster name. A persistent systemd firewall rule blocks bridge-mode task
containers from reaching the EC2 metadata address, following [AWS's ECS task
role guidance](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/security-iam-roles.html);
the separate task role remains bounded to Listings S3 and the application
never receives the EC2 instance credentials.

The test profile rejects client-supplied owner IDs and refuses startup unless
it is in `clip_test_listings` with the least-privilege application role. The
caller remains source-fixed and production settings reject the profile.
S3 stays private; short-lived signed uploads and reads use the existing
run-scoped prefix and role permissions. Bucket CORS allows only the exact
deployed HTTP origin and `If-None-Match: *` upload header.

The lifecycle has two operator commands:
`make li02-demo-start AWS_PROFILE=<approved-profile>` and
`make li02-demo-stop AWS_PROFILE=<approved-profile>`. Start also continues a
recorded partial run, so there is no separate resume command. The work log
records earlier run evidence and the current cloud-check gate.
Start requires clean committed build inputs, preflights account/region, budget,
the LI-02 cluster/ASG state, and Terraform state, then builds/pushes uniquely
tagged images from that immutable source. It asks once for
`START LI02 DEMO <run-id>` before its first cloud write; that confirmation
covers the run's image publication, generated secret, isolated database setup,
and public demo start. The first exact-hash-approved plan creates the
LI-02 cluster, capacity provider, ASG and zero-capacity host configuration,
private disposable RDS, database tasks, and temporary ALB while keeping app
count zero. Start creates the database URL as one SecureString without
printing its value, bootstraps only `clip_test_listings`, applies checked-in
migrations, seeds one fixed synthetic seller, then enables the app and prints
the ALB URL. Each Terraform saved plan is displayed with a SHA-256 and requires
that exact text to be typed before apply. RDS is attempted in `ap-south-1b`; only an explicit
`InsufficientDBInstanceCapacity` response may advance the same start command to
a fresh `ap-south-1a` plan, with a separate hash approval. The script verifies
that neither AWS nor Terraform state contains a failed-attempt RDS instance
before fallback. Shared RDS and shared ECS are not started or changed. No custom domain or
subdomain is needed for this HTTP endpoint.

Before bootstrap, start runs the fixed owner-check cleanup task. It drops only
`clip_test_listings` when owned by `clip_test_listings_app`, removes only that
exact orphaned login, and fails closed on any owner mismatch. The run-level
start confirmation covers this cleanup followed by bootstrap, migrations, and
the synthetic seller seed. The shared `clip_test` database and
shared RDS are never started, used for a database connection, or modified; the
driver reads RDS inventory metadata only to detect a stray LI-02 instance. If a
start phase fails, rerun the same start command to
continue from the saved baseline; use stop to discard the partial run.

The database lifecycle uses a separate bounded query helper to capture fixed
metadata internally; write output and client diagnostics remain suppressed.
Empty or malformed query results stop execution before database writes. Normal
start retries reuse the recorded immutable image digests. If a published image
has a defect, publish a corrected image from a reviewed commit and apply its
separately reviewed task-definition plan with the app count at zero before
rerunning start. The driver never substitutes local code for an existing
deployed digest or task definition.

Bootstrap supports the non-superuser RDS administrator: it grants that operator
permission to `SET ROLE` only into the newly created dedicated Listings role,
with inherited privileges disabled. Ownership operations explicitly switch to
that role; cleanup resets the role before dropping the dedicated login, which
also removes its operator membership. The application login receives no
administrator membership. Statement/duration/error-statement logging remains
disabled and verified in the password-setting transaction; error bind values
are suppressed. The non-error bind-parameter cap is not changed because RDS
does not permit it and it only affects statement/duration logs that the guard
already disables. See [PostgreSQL logging settings](https://www.postgresql.org/docs/18/runtime-config-logging.html)
and the shared [password logging boundary](../../../../../docs/decisions/private-postgresql-probe-login.md).
The idle guard treats another role's database session with a hidden backend
type as busy, so restricted statistics visibility cannot hide an active client
and incorrectly permit deleting the disposable LI-02 database.

Stop asks once for `STOP LI02 DEMO <run-id>` before run teardown. This
run-scoped confirmation is recorded for safe retries; the Terraform removal
plan still requires its exact hash approval. Stop scales the LI-02 service to
zero, drops only the isolated Listings
database/login, verifies the database is idle, removes the exact S3 run prefix
and database URL parameter, then uses a reviewed plan to delete the disposable
RDS instance and remove the temporary ALB, subnet/route, host ingress rule, ECS
service and task definitions. It then scales only the LI-02 ASG to zero and
waits until its EC2 host and tagged root volume are absent. It retains the empty
LI-02 ECS cluster/capacity-provider/ASG and dedicated host SG/role for restart.
It retains LI-02 ECR image digests for reproducible restart and clears LI-02 log
streams. It preserves the Step 4 empty image
bucket, IAM roles, empty log group, state backend, shared RDS and `clip_test`
database, VPC, NAT, shared ECS cluster/capacity provider/ASG/host security
group, and other domains' artifacts. It never deletes or Terraform-manages a
shared resource. Shared foundation costs continue while the demo is off.

If a database task or owner check fails, retain the ignored baseline file and
rerun `make li02-demo-start AWS_PROFILE=<approved-profile>` to continue the
recorded phase. The driver fails closed if a required cleanup task definition
is missing or a saved state is ambiguous. For teardown, use the single stop
command; it retains baseline metadata until database cleanup and dedicated
LI-02 capacity termination are confirmed. The file contains no credentials. Do not
delete it to bypass a failed check or infer live cloud state from the file
alone.

The app uses the disposable LI-02 RDS instance only while the demo is on; stop
deletes it after the owner check and idle check. The shared RDS is neither
started nor stopped by this lifecycle. Human
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
