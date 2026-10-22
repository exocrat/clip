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
| Exposure | Account `335523638354`, Region `ap-south-1`; bucket blocks all public access, enforces bucket-owner ownership, uses SSE-S3 and a TLS-only bucket policy. Browser upload CORS is limited to the local Vite origin `http://127.0.0.1:5173` (or the documented `localhost` equivalent). No website hosting or public app ingress is created. |
| Objects and permissions | Bucket `clip-test-listings-images-ap-south-1-li02`; app keys use `listings/test/<test_run_id>/`, where Terraform fixes the selected run ID. The API task role can only get, put, and delete objects under that exact run prefix. The API execution role can pull the reviewed image from the existing shared API ECR repository, write only to this test log group, and read only `/clip/test/listings-database-url`. A separate one-shot database-setup execution role can pull its reviewed image, write to the same bounded log group, and read only `/clip/test/database-master-password` plus `/clip/test/listings-database-url`. Its task definition has no AWS task role. All three roles use the administrator-owned boundary ARN `arn:aws:iam::335523638354:policy/clip/listings/test/CLIPListingsTestRuntimeBoundary`; each inline policy is narrower than that ceiling. |
| Upload/delivery limits | Reuse the reviewed contract: 1–8 JPEG/PNG/WebP images, each 1–10 MiB; controlled object keys; browser upload uses short-lived signed PUT instructions; authorized reads use the existing maximum five-minute signed delivery URL. |
| Retention and cleanup | Do not expire confirmed images by object age: an attached listing may remain active. The Listings cleanup worker deletes an exact pending/failed/retired key only after the database state permits deletion and S3 confirms absence. Preserve retry metadata until then. S3 lifecycle aborts only incomplete multipart uploads after one day. Versioning is disabled so a successful object delete does not leave old image versions behind. The isolated run uses a dedicated `clip_test_listings` database on the existing RDS instance and a run-scoped S3 prefix. Remove synthetic rows and objects through the reviewed cleanup path, then drop only that dedicated database with the one-shot setup task. Do not alter the shared `clip_test` database; `force_destroy` is not enabled. |
| Test window and data cap | Reuse the shared private ECS/RDS/VPC/NAT foundation; do not create a second database or network. Proposed isolated rehearsal cap: one ECS host/task, up to two active hours, and at most one listing with eight maximum-size images (80 MiB total). The previously reviewed shared-stack reference is about USD 0.35 for two fully active hours before traffic, startup/scale-in tail, and continuing base charges. The bucket itself has no hourly fee; storage, request, transfer, and log charges depend on actual use. Refresh account spend, credit eligibility, and the exact cost estimate before the Step 3/Step 12 approvals. |
| Rollback | Disable the Listings test task first; keep the shared cluster/RDS/network/state resources untouched. Delete only LI-02-owned images and metadata through the reviewed cleanup procedure. Prepare a fresh destroy plan for this root after the bucket is verified empty; never use `force_destroy`. |

The local browser uploads directly to S3 using a Listings-issued URL that is
valid for at most five minutes and requires the signed `Content-Type` and
`If-None-Match: *` headers. The bucket policy denies PUT requests under the
current test-run prefix if the create-only condition is missing, and CORS
allows the browser to send that header from the loopback Vite origin. It is
not a public bucket: the origin restriction is a browser rule, while IAM
remains the authority for object access. A later hosted frontend origin must
be separately reviewed and added to the test root before that origin is used.

The isolated cloud API may enable its fixed seller only with
`CLIP_ISOLATED_LISTINGS_TEST_CALLER=true` and
`CLIP_DEVELOPMENT_AUTH=true`. Settings also require `CLIP_ENVIRONMENT=test`,
database URL path `clip_test_listings`, the exact private test bucket and
`ap-south-1` region, and a single-segment `listings/test/<test_run_id>` prefix.
The API database URL must use the dedicated login `clip_test_listings_app`.
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

## Isolated app route for Step 12

Step 12 will add a Listings-owned ECS task definition/service to the existing
private `clip-shared-test` cluster and its capacity provider; it will not
replace or edit the shared API service. Use bridge networking with container
port `8000` mapped to host port `18001`, no public IP, listener, or inbound
security-group rule. The API task uses the API task and execution role ARNs
output by this root and the exact `/clip/test/listings-database-url`
SecureString reference. The API execution role is also used by the fixed
one-shot migration task; that task has no task role. A separate fixed
one-shot database-setup task uses the database-setup execution role, reads
the existing RDS master secret and the Listings database URL, creates or
removes only `clip_test_listings` and its dedicated application login, and
does not receive AWS credentials inside the container. Its startup, migration,
and cleanup commands must be fixed in reviewed task definitions rather than
supplied as arbitrary ECS overrides. The database URL is a SecureString
created through the existing `/clip/*` Parameter Store access; its value is
never put in Terraform state, output, tags, or logs.

Build the API and database-task images from the same selected source revision
and push immutable digests to the existing `clip-shared-test-api` ECR
repository. The migration task must use the repository's pinned migration
tool/version and exact checked-in migrations. The dedicated database login
owns only the isolated Listings test database so migrations can create their
schemas there; the RDS master login is used only by the one-shot setup task.

Run the local Vite UI at `http://127.0.0.1:5173`; its existing `/api` proxy
targets local port `8000`. The named operator opens an SSM port-forward from
local port `8000` to port `18001` on the private ECS host. The browser then
uses the Listings UI and its short-lived S3 URL from the operator's machine.
Only the operator reaches the API through SSM; S3 remains private and grants
the ECS task role only the `listings/test/<test_run_id>/*` object operations. This route uses the
existing private network/cluster and does not create web hosting or a public
endpoint. Step 12 must verify the actual SSM target and mapping before use.

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
review and apply approval. Step 12 adds task definitions and the service using
the three role ARNs prepared here, then verifies the private SSM route against
the approved target.
