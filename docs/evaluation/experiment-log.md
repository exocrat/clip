# Experiment log

This log tracks detailed progress and decisions for the ECS-only versus ECS+Lambda
comparison and related NFR measurements. The [project work log](../status/work-log.md)
remains the task-status and verification record. Approved manifests, raw results,
and analysis belong in the [evaluation evidence homes](README.md), linked from
this log. Record UTC times; never include credentials or private data.

For each meaningful checkpoint, record its task and step, purpose, environment,
revisions, inputs and target, changes and decisions, exact checks and outcomes,
evidence links, verification state, limitations, and next action. For measured
runs also record the run ID, configuration, manifest, workload and intervals,
validity, results, costs and cleanup; link raw evidence instead of copying it.
Record skipped, failed and inconclusive checks as such and retain prior entries.

## Current checkpoint

### 2026-11-03 04:40:44 UTC — Synthetic Lambda read event builder

**Work:** `apps/api/app/overflow_event.py` builds a bounded ALB-shaped event
for a selected bodyless Listing GET, preserving repeated query parameters and
headers while rejecting forwarded and hop-by-hop headers. Its synthetic target
group marker is restricted to the project/account naming shape. The builder
does not establish an authenticated caller or trusted HTTPS; trusted ingress
metadata and authentication remain integration gates. It is not app-wired.
`apps/api/tests/test_overflow_event.py` checks synthetic round-trip preservation,
selected routes and rejection of unsafe headers. AWS documents the
[multi-value ALB event shape and raw query encoding](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html).

**Checks:** Thirty-six synthetic event, policy and transport tests passed;
strict mypy and Black passed after formatting. No real Lambda Web Adapter event,
session, AWS call or measurement occurred. The required trusted HTTPS/host
handoff and real Web Adapter behavior must be reviewed and tested before use;
the module deliberately cannot establish either. Terraform B remains blocked.

### 2026-11-03 04:38:52 UTC — Unwired Lambda Invoke adapter

**Work:** `apps/api/app/overflow_invoke.py` accepts an injected SDK client,
a project-account/region EXP-03 function ARN and bounded event bytes. It
requires SDK retries disabled, invokes synchronously once without log tails,
closes and bounds the response stream, rejects function errors and sanitizes
failures. Only the prior precise throttle classifier permits ECS overflow.
`apps/api/tests/test_overflow_invoke.py` checks one-call behavior, throttling,
failed/oversized responses and refusal before calls with synthetic clients.

**Checks and limitations:** Nineteen policy/classifier/transport tests passed;
strict mypy and Black passed. Initial mypy found a possibly missing stream; it
was fixed before rerunning. No real client, AWS call, ASGI wiring or request was
used. Event encoding, Lambda Web Adapter compatibility, trusted HTTPS/session
handling, response validation, bounded timeouts, concurrency, telemetry and
deployed parity remain unverified. The 64 KiB event and 1 MiB response limits
are local safety bounds, not measurements or proven product limits. The
Terraform B guard remains in force until the full mechanism is reviewed.

### 2026-11-03 04:36:51 UTC — Offline Lambda rejection classification

**Work:** `apps/api/app/overflow_aws_errors.py` translates only a synthetic
SDK `Invoke` error with HTTP 429 and `TooManyRequestsException` to the existing
overflow signal. Other SDK errors become a generic safe error; raw provider
messages and exception chains are suppressed. The error can mean account or
function throttling, so it is not proof of which concurrency limit was hit.
The helper has no client or network calls and is not wired to the app.
`apps/api/tests/test_overflow_aws_errors.py` checks the exact match and rejects
other status, operation and error-code combinations, including redaction.

**Basis and checks:** AWS documents that synchronous Invoke API errors prevent
function execution and that `TooManyRequestsException` may reflect account or
function concurrency ([Invoke API](https://docs.aws.amazon.com/lambda/latest/api/API_Invoke.html)).
Nine combined policy/classification tests, strict mypy and individual Black
checks passed. A future actual SDK transport must disable retries, handle
function errors separately and remain subject to integration/privacy review.
No AWS call, deployed request or measurement was made.

### 2026-11-03 04:35:00 UTC — Local overflow decision policy

**Direction:** The user accepted an ECS-hosted Lambda-first router and the
proposed narrow fallback: only a confirmed Lambda capacity rejection invokes
the ECS handler. Timeouts and other errors do not trigger a second request.

**Local work:** `apps/api/app/overflow_dispatch.py` implements this decision
against injected async callables, without network access or app integration.
It identifies the selected backend and suppresses response values in its
representation. `apps/api/tests/test_overflow_dispatch.py` verifies Lambda
success, one capacity fallback and no fallback on other errors with synthetic
callbacks. The transport must independently classify real AWS rejection before
execution; it does not exist yet. Route selection, ASGI event conversion,
authentication, request/response privacy, bounded timeouts, backend telemetry,
IAM, database capacity and real integration remain open. Terraform B stays
blocked. No AWS call, deployment or measurement occurred.

**Checks:** Four focused pytest cases and strict mypy passed. Black passed when
checking each file separately. Its initial multi-file invocation could not
create a sandboxed worker socket; a single-worker retry was interrupted after
waiting, and the individual-file checks succeeded. No source was reformatted.

- **New EXP-03 direction (2026-11-03):** The user requested Lambda-first reads
  with ECS overflow when Lambda reaches capacity. The old direct-to-Lambda B
  configuration is blocked pending an implemented, reviewed overflow path.

### 2026-11-03 03:07:09 UTC — Lambda-first overflow direction

**Decision:** The user directed Lambda-first handling for selected reads with
overflow to ECS when Lambda has no capacity. The previous direct Lambda rule
does not provide that behavior. The PRD leaves the exact route allocation open;
the prior detailed comparison design needs affected-owner review and revision.

**Preparation:** Added a Terraform precondition refusing the old configuration B
and a mock test of that refusal. Configuration A remains available for local
planning. The implementation approach, bounded concurrency, failure behavior,
database capacity, per-backend evidence, cost, safety and real deployment
remain open. An ALB weighted split or unhealthy-target routing does not itself
provide per-request Lambda capacity overflow. No AWS action or measurement.

**Checks:** `terraform fmt -check -recursive infra/terraform/shared/test` and
`git diff --check` passed. A backend-free temporary copy ran `terraform test`
using the mock AWS provider with credentials removed: 18 passed, including the
new B refusal. Local provider communication required approved escalation; no
AWS API calls or applies were made. This is a guard test, not overflow proof.

- **EXP-03 Terraform:** An opt-in local A/B infrastructure draft and mock
  tests are ready for review. No AWS resources have been created or changed.
  A concrete live plan, independent review, interruption-safe cleanup,
  dataset verification and explicit approval remain necessary.

### 2026-11-02 19:56:04 UTC — EXP-03 Terraform and deployment planning

**Scope:** On `task/exp-03-lambda`, prepared an opt-in Terraform draft for
the HTTPS ALB, Lambda, networking and ECS routing. No AWS resource was created,
started, changed or deleted; no deployed requests or measurements were made.
Rahul owns this Terraform work, with independent and affected-domain review
still required. The [preparation record](exp-03-terraform-preparation.md)
describes each input, the A/B routing, IAM, shared-resource changes and gaps.

**Local checks:** Terraform 1.15.9 and AWS provider 6.69.1 validated a
backend-free temporary copy; all 18 mock-provider plan tests passed, including
the nine EXP-03 cases. Seven synthetic proxy-trust tests passed. Mock plans
cannot establish effective IAM, actual security-group attachments, adapter
header handling or service readiness. A mock apply attempt failed on synthetic
provider-generated identifiers and was removed; a security-group assertion on
unknown mock values also failed and was replaced with checks of known plan
properties. Neither failure involved a real apply.
On repeat, the sandbox prevented the local provider plugin from starting;
the same mock-only test passed all 18 cases with approved local escalation and
AWS credential environment variables removed. The full Identity test file passed
21 tests; `terraform fmt -check -recursive` and `git diff --check` also passed.

**Read-only inventory:** The project account/profile and region were verified;
the ECS service, RDS and retained EC2 hosts were stopped. The ASG's launch and
termination processes were suspended. The retained t3.micro host is too small
for the existing Hybrid ECS task guard, and a launch-template update would not
resize or update it. A second public subnet and an issued project certificate
were identified as candidates; their real use needs a fresh plan and review.
The historical synthetic reference database and the current secret target have
not been proven to match. No secret values were read.

**Costs and limits:** The user capped credit use at USD 10; a free-plan metadata
response showed approximately USD 154.11 remaining, subject to billing delay
and eligibility. Read-only public Mumbai price-list queries returned USD
0.08479/hour for on-demand c7i-flex.large, 0.021/hour for running db.t4g.micro
PostgreSQL, 0.0239/hour for the ALB and 0.008 per ALB capacity-unit-hour.
These are individual price inputs, not a complete estimate: NAT, storage,
public IP, Lambda, transfers, logging, taxes and other usage still need review.
One initial SDK pricing query failed because the CLI login's optional CRT
dependency was absent; subsequent CLI price-list queries succeeded.

**Open gates:** The declared Terraform budget and expiry tags do not enforce a
spending or runtime limit. An interruption-safe cleanup path, exact image and
host rollout, database/data access, costed runtime and stop conditions, full
plan review, and explicit approval remain necessary before any live operation.
See the linked preparation record for restoration and dataset constraints.

- **EXP-01:** Design verified; see the [comparison protocol](ecs-only-vs-ecs-lambda-task-list.md).
- The experiment-design document's proposed 300 concurrent-client-request
  ceiling is explicitly non-binding per user direction. Do not enforce it as a
  code guard; the actual client/generator concurrency limit remains open for the
  reviewed pre-run plan.
- **EXP-02:** Retained upstream work-log evidence records DATA-READY accepted
  as reported by Aditya, with Suraj's review reported by Aditya; the immutable
  frozen artifact keeps its capture-time flag. Actual ECS/Lambda database and
  configuration equivalence remains pending.
- An offline paired-plan checker and blank template now describe the approved
  three-cycle A/B, B/A, A/B order and nine low/normal/burst pairs. They validate
  the declared plan and can compare all 18 captured manifests to it, including
  the recorded chronological order and non-overlap. Actual deployment identity,
  timestamp accuracy and generator suitability remain future gates. No
  concurrency ceiling is encoded.
- The offline input preflight also validates profile timeout, worker-value shape
  and an operator-supplied exact file hash; it cannot prove review or later use.
- A combined offline input preflight now checks the completed source/dataset/
  corpus binding and 18-run pair plan together, including matching dataset and
  corpus fingerprints. It does not obtain credentials, send requests or
  authorize measurement, and has not yet been wired into a real-target runner.
- Each local workload invocation now requires one condition and schedules only
  its warm-up and measured cohorts; staging records the selected planned condition
  and the report CLI requires it. The local workload also accepts one
  case-sequence start per traffic condition.
  The offline preflight can compare a supplied profile's starts and cases with
  a selected cycle of the paired plan. The user approved the seeded rotation
  rule; the actual seed remains open, and a future real-target runner must
  enforce these checks before credentials.
- An offline builder can now create a separate profile for each cycle using
  the checked plan/cases and supplied worker limits. Each cycle's profile is
  reusable for A and B. The version-3 run template records a separate profile
  reference/hash; offline checks compare saved bytes and require the six run
  records in a cycle to agree. Actual use remains a future runner/evidence gate.
- **EXP-02 Steps 3–5:** The user confirmed reviewed search labels already
  exist and directed comparing the ECS and ECS+Lambda responses. No separate
  hand-authored ordered Hybrid results are required. On `task/exp-02-workload`,
  commits `ca5904f`, `db57507` and `845a809` add parity-bound offline staging,
  preflight and mock-session ordering; `a52adea` adds local k6 phase previews. The real runner, owner review and
  actual deployed parity remain open; those changes are not merged into this
  Lambda branch. The earlier ordered-reference `k6 inspect` refusal is a
  historical tool limitation, not a request for new search results.
- **EXP-02 Step 6:** Client accounting/reporting is implemented and locally
  checked with synthetic metrics. Offline metadata checks expose declared timing,
  generator limits, VU headroom and drops. The user prefers built-in k6 phases;
  affected-owner review is needed to revise the verified-monotonic requirement.
  Real resource telemetry and a real k6 run remain pending. Reports mark latency
  timing unverified even when counts match.
- **EXP-02 Step 7:** A per-run capture template and validator are ready. No
  measured run exists, so run-specific values remain blank. An offline telemetry
  metadata validator now checks run binding, artifact references and windows; it
  does not open or attest actual artifacts.
- **EXP-02 Step 8:** The existing report tool reads raw k6 output and opens
  derived reports as new files. The offline evidence verifier now hashes raw
  output and derived reports against the captured manifest and rejects files
  that resolve to the same inode. This checks recorded digests and distinctness;
  it cannot prove when the digest was recorded or authenticate the artifacts.
  No run output has been captured.
- **EXP-02 session input:** Aditya has recommended signing in before the measured
  run and privately passing the resulting HttpOnly CLIP session cookie to k6;
  the user reports receiving two temporary test accounts. The repository already
  has a preflight-gated, in-memory handoff draft using
  `CLIP_COMPARISON_SESSION_COOKIE`, tested only with synthetic values. The real
  session has not been acquired or handed off, and this report does not verify
  either account, settle whether temporary accounts satisfy the approved account
  class, or authorize a run. Do not record account identifiers or cookie values.
- **Measurements:** No ECS/Lambda comparison or final NFR run is recorded here.

- **EXP-03 narrow Lambda app composition:** The local app now exposes only the
  two reviewed GET routes and caps its Listings and Hybrid pools at one
  connection each; Conversations, notifications, wanted/saved stores, the
  embedding worker and S3 image storage are skipped. Existing ECS composition
  remains unchanged. This does not settle aggregate DB headroom or concurrency.
  The Lambda entry point remains fail-closed by default; explicit hosted-test
  opt-in now selects the session-only binding described below. Real authenticated
  parity is still unverified.
- A local image builder now requires a revision-labelled cached Hybrid image and
  cached pinned Lambda Adapter digest, verifies both are Linux AMD64, and refuses
  to overwrite an existing local output tag. It is indexed in the command
  registry; the existing output tag caused the test invocation to stop before
  rebuilding. No registry upload or cloud action is possible through the script.
- A synthetic Hybrid lifecycle test confirms the Lambda override requests a
  one-connection read pool and suppresses the optional worker. It does not prove
  startup with the real database/model or endpoint response parity.
- `apps/api/tests/test_lambda_read_routes.py` exercises the actual read-only
  FastAPI routes over in-process ASGI transport with test-only trusted callers
  and Listings adapters. It checks a successful Hybrid-labelled query envelope
  and preserved filters/pagination, missing-session 401, malformed-query 422,
  ineligible-user 403, detail identity/404, and safe 503 mapping for synthetic
  database and pool-timeout failures. It does not prove real Identity, Hybrid
  ranking/model startup or live database behavior.
- The user assigned Rahul the scoped session-only Identity binding work. A new
  read binding now reuses the existing session/browser middleware and public
  eligibility dispatch without mounting Identity routes. Explicit Lambda test
  opt-in prepares the existing real session service from only authentication-key
  and database references, retaining the existing role/key audit and last-seen
  session update. It skips email-route loading, sender warmup and Microsoft
  metadata setup. Default startup remains unauthorized. Offline mock checks pass;
  real SQL sessions, expiry/revocation, package startup, trusted HTTPS ingress and
  owner/independent review remain pending.
- A new offline transport test wraps the session-only app in Uvicorn's
  `ProxyHeadersMiddleware` and checks that HTTPS is accepted only when the ASGI
  peer is the configured loopback adapter; forwarded HTTP, missing forwarded
  scheme and an untrusted peer fail before session authentication. The focused
  four-file suite passed 98 tests. This tests Uvicorn's policy with synthetic
  ASGI requests; it does not exercise Lambda Web Adapter event conversion or
  establish ALB/Lambda invocation permissions, host trust, SQL or deployed parity.
- The ordinary local container startup does not activate Lambda Web Adapter:
  its official local guide says the adapter activates inside the Lambda
  execution environment and recommends SAM CLI to simulate it locally. SAM CLI
  is not installed here, so no adapter invocation simulation was run. See the
  [AWS Lambda Web Adapter local debugging guide](https://aws.github.io/aws-lambda-web-adapter/development/local-debugging.html).
- EXP-03 steps 4–5 do not yet have an owned Terraform implementation path:
  `infra/terraform/shared/test/` and `infra/terraform/modules/shared/` are
  assigned to the PD-16 integration owner, and the ownership map defines no
  Lambda-specific root. It forbids speculative modules and shared-resource
  declarations from a domain root. Therefore no listener, Lambda, role, or
  network Terraform was added on this branch. The exact resource owner/root and
  reviewed shared interface must be settled before that code can be prepared.
- User later authorized AWS access under a USD 10 credit cap and assigned
  Terraform ownership. Read-only identity, resource and parameter-metadata
  checks were performed; no resource mutation or secret read occurred. Exact
  deployment, pilot and cleanup plans retain their separate approval gates.

## History

### 2026-11-02 19:36:53 UTC — EXP-03 Lambda access log control

The Lambda image command now sets Uvicorn `--no-access-log`, matching the
existing hosted ECS intent to avoid logging raw paths and search queries. The
controlled application logging still applies; this flag does not attest Lambda
Web Adapter or AWS service logging. Fifteen focused bootstrap/image-command
tests passed. No image build, AWS call or workload occurred for this change.


### 2026-11-02 19:35:40 UTC — EXP-03 read-only settings without email

The previous Lambda-only bootstrap inherited the full Identity email settings,
which required a recipient even though the read-only app never starts an email
sender. The opt-in path now uses a dedicated `LambdaReadSettings` subclass: it
requires the existing hosted test identity, exact browser origin and Listings DB,
while rejecting email provider/recipients, web serving, storage, notification
and Hybrid worker startup. Ordinary ECS `Settings` and its controlled-recipient
requirements remain unchanged. Secret retrieval stays fixed-path and only after
all non-secret settings pass. This is local code, not live security acceptance;
Identity and affected owners must review before deployment.

Focused Lambda, Identity, route and architecture checks passed 112 tests with
warnings as errors. Fake inputs cover refusal of email, recipients, extra
services and bad setup before provider access. No AWS call or real secret read
was made for this increment. [Design](exp-03-lambda-design.md).


### 2026-11-02 19:32:53 UTC — EXP-03 Lambda database secret bootstrap

**Direction and scope:** User authorized AWS under a USD 10 credit cap and
assigned Terraform ownership. No deployment or secret retrieval was authorized
by this local preparation; exact deployment/pilot/cleanup plans remain gated.
EXP-02 commit `a52adea` on its separate branch prepares candidate k6 phase
metrics; its real runner and real comparison remain incomplete.

**Implementation:** The existing Identity-owned runtime configuration adds a
Lambda-only opt-in loader for `/clip/test/listings-database-url`. It requires
the Lambda runtime marker, test mode, Identity opt-in, no database environment
override and otherwise valid settings before creating a parameter client; the
fixed SecureString is retained as `SecretStr` in memory. Provider errors and
invalid settings are redacted. `lambda_main.py` uses this loader; defaults
remain unchanged and the existing Identity session code still reads its two
fixed Identity parameters. The existing settings require controlled recipients
even though this composition never starts an email sender. The architecture
checker permits this exact composition-root import only.

**Checks:** 108 focused synthetic Lambda, route, Identity and architecture
tests passed with warnings as errors; boundary scan passed with zero violations.
Strict Mypy passed for the runtime and entry point. The first test run exposed three private-domain boundary violations in a new
bootstrap module; the loader was moved to the Identity-owned runtime and only
its exact composition-root entry was allowed before the passing run. Fake
providers verify refusal before reads and redaction; no actual secret was read.

**AWS metadata:** Three targeted `ssm describe-parameters` calls using the
verified non-root project identity returned SecureString version 1 for the
fixed Listings database URL, Identity database URL and Identity authentication
keys. Names/type/version only were requested; no values or SQL were read and
no AWS resource was changed. Effective Lambda IAM, connectivity, session
behavior, deployment and credit balance remain unverified.


### 2026-11-02 19:23:06 UTC — EXP-03 local image revision declaration

**Finding and change:** The existing helper checked only matching tag suffixes;
a tag can point to an unrelated image. `scripts/evaluation/build_lambda_image.sh`
now requires a full OCI revision label on the cached Hybrid image matching the
tag prefix, and propagates that label to the local Lambda output. The label is
a producer declaration, not proof that the image was built from that revision;
image provenance and later deployment checks still need review. Existing
unlabelled Hybrid images will be refused until rebuilt with a declared label.
`docs/environment/commands.md` describes that requirement and limitation.

**Checks:** Five fake-Docker tests cover matching, absent, short, mismatched
and malformed labels, no build on refusal, and offline build options. `bash -n`
passed. No real Docker build, AWS action, workload or measurement occurred.
The EXP-02 status above reflects the user's parity direction and separate branch
commits; no cross-branch merge occurred.


### 2026-11-02 18:37:36 UTC — EXP-02 corpus gate and EXP-03 proxy policy check

**Direction and scope:** User directed that no AWS work or resource creation be
performed and asked to finish the remaining tasks. Work in this checkpoint was
limited to local tests, static inspection, and documentation; no cloud calls,
deployment, live request, workload, or measurement occurred.

**EXP-02:** `/usr/bin/k6 inspect` was first invoked without its mandatory local
target and failed at `local_target_required`, before script setup. A second
inspection supplied an explicit loopback target, a temporary profile built from
the retained case corpus, a synthetic cookie placeholder, and the low condition.
It then refused initialization with `invalid_expected_case`: all five browse
and two detail expectations pass the k6 shape check, while the three Hybrid
cases have `expected: null` until independently reviewed ordered results
exist. This is the intended fail-closed behavior. No cookie was read and no
request was sent. Node 24.22.0 tests for case construction, schedules, outcomes,
and response checks passed (4 files); the 10-case corpus remains incomplete for
the scheduled load script.

**EXP-03:** Added a parameterized ASGI check in
`apps/api/tests/test_lambda_identity.py` around the existing session-only app.
It accepts HTTPS only from Uvicorn's configured `127.0.0.1` trusted peer and
rejects forwarded HTTP, absent forwarded scheme, or an untrusted peer before
Identity session lookup. Focused command
`.venv/bin/python -m pytest -q -W error apps/api/tests/test_lambda_identity.py
apps/api/tests/test_lambda_read_routes.py apps/api/tests/test_lambda_read_app.py
tests/architecture/test_boundaries.py` passed **98 tests**. Pinned Black check
and `git diff --check` passed. Existing local API/Lambda images were inspected
as Linux AMD64 with their recorded IDs unchanged. This test does not prove the
AWS Lambda Web Adapter's ALB conversion, ingress host trust, invocation policy,
real session/SQL, database headroom, or deployed A/B parity. Those remain open.

The previously recorded local container start does not count as adapter
invocation evidence. The official [Lambda Web Adapter local debugging guide](https://aws.github.io/aws-lambda-web-adapter/development/local-debugging.html)
says the extension activates inside Lambda and documents SAM CLI for local
simulation. SAM CLI is unavailable in this environment; no AWS API, local Lambda
runtime simulator, or deployment was used in this checkpoint.

**Files:** the test adds only synthetic transport peers/headers; this log and
the status rows record the expected k6 refusal and limitations. The checkpoint
is ready for local review/commit; independent peer/owner review remains required.
No AWS action was attempted.

### 2026-11-02 18:42:57 UTC — EXP-03 local image builder and Terraform ownership review

**Scope:** Continued local preparation after the user's no-AWS direction. No
cloud service, AWS CLI/API, image registry, workload, or measurement was used.

**Local builder:** Added `scripts/evaluation/build_lambda_image.sh` and indexed
it in `docs/environment/commands.md`. It requires the same commit suffix on a
prebuilt local Hybrid API image and new Lambda output tag, confirms Docker's
default context uses a Unix socket, requires the exact pinned adapter digest to
be cached, checks both cached base images are Linux AMD64, refuses existing
output tags, and uses `--pull=false`,
`--network=none`, and `linux/amd64`. It only builds and inspects a local image;
it has no Docker login, pull, run, push or deployment command. The checked-in
image tag already exists, so the no-overwrite guard stopped before a build.

**Checks:** `bash -n scripts/evaluation/build_lambda_image.sh` passed. `--help`
printed the required source-matched tag syntax. Running it with the existing
`clip-exp03-hybrid:local-8a60f83` and
`clip-exp03-lambda:local-8a60f83` tags exited 2 with the expected refusal to
replace the existing output. The local Docker endpoint and pinned cached inputs
were therefore available; no image was created or changed. ShellCheck is not
installed. At 18:44:38 UTC, reran the syntax/help checks and the safe Docker
preflight; both cached images reported `linux/amd64`, then the existing output
tag was refused before build. Terraform checks were not run because no Terraform
files changed.

**Infrastructure ownership:** Reviewed
`docs/architecture/terraform-ownership.md`, the shared Terraform root, and the
EXP-03 steps. The shared test root belongs to the PD-16 integration owner, the
shared module has the same owner, and no Lambda root/interface is recorded.
Those rules prohibit placing shared ALB/Lambda resources in the domain root or
inventing a root/module without an approved owner and interface. No Terraform
files were changed. EXP-03 steps 4–5 remain open for ownership/interface review,
ALB rule/resource code, adapter/runtime proof, and later independent review.

**Changed files:** `scripts/evaluation/build_lambda_image.sh` provides a
network-disabled, no-overwrite local build path; `docs/environment/commands.md`
records its invocation and effects; this experiment log and the status row
record the checks and Terraform ownership blocker. No cloud action occurred.

### 2026-11-02 18:28:38 UTC — EXP-03 local image build and planning inputs

**Scope/direction:** User authorized autonomous local implementation/checks and
local commits for the session, retaining exact-plan approval for AWS changes,
live smoke and measurements. User confirms Rahul as operator with profile
`clip-project`, account `335523638354`, region `ap-south-1`. They selected one
temporary account for comparison and two only for conversations; this differs
from the plan's initial regular-account workload and still requires the affected
Identity/Search/experiment review and protocol/tool update. User prefers public
HTTPS on the ALB without a client-IP allowlist. They set a $5–10 credit range;
use $5 as the conservative working ceiling for a proposed plan until clarified.
User requests pilot checks after a separately approved concrete AWS plan, not an
assumed authorization for the measured comparison. If the deployed dataset is
missing, stop rather than load/modify it. Dataset/evidence should be retained;
no destructive cleanup is inferred.

**S3 clarification:** Recorded NEXT-06 evidence says listing image objects were
uploaded to S3, while the actual users/listings/vector data were loaded into an
isolated RDS database. `data/transfer/next06-reference-20261030.tar.gz` and its
manifest contain the reviewed transfer payloads/photos; the repository has an
existing controlled load/transfer design. This is not evidence that S3 contains
a restorable full database backup, that the current RDS/S3 contents still match,
or that the approved experiment may reload them. No S3, database or loader call
occurred. Verify the deployed copy under an approved plan; stop if absent.

**AWS identity only:** A bounded STS caller-identity request using the explicit
profile and region, with ambient AWS credential environment variables excluded,
confirmed the specified project account and a non-root principal. The check did
not verify permissions, resources, actual spend, data or session validity. No
other AWS request or resource change was made in this checkpoint.

**Local builds, all Linux AMD64 from clean source commit `8a60f83`:**
- `clip-exp03-api:local-8a60f83`:
  `sha256:081c63b78785d29aa3e99214fbbb45b8accae1e7f7dc85b2e24f774e6dfcedfc`,
  local size 319,479,821 bytes. The existing API Dockerfile used its restricted
  source context and locked npm/uv dependencies; public build inputs were
  separately authorized. Web typecheck/build completed with its chunk advisory.
- `clip-exp03-hybrid:local-8a60f83`:
  `sha256:0ea4a8859dade5611c06b8df29fd0855e0e51c36ed327dd29899c568ecb85a19`,
  891,296,081 bytes. Both local model/tokenizer SHA-256 values matched the
  checked-in pipeline; 24 locked wheels installed offline. The existing build's
  one network-disabled synthetic inference returned 384 dimensions. This is a
  functional packaging check, not a benchmark, relevance score or NFR result.
- `clip-exp03-lambda:local-8a60f83`:
  `sha256:ea8b7d58342fa5070b8016401746994750df5988bf38d53a9f0ad82cc54bbefe`,
  896,353,157 bytes. It used adapter image digest
  `sha256:17cfd08eff1dfea3f6a9a1e9c65fdac80aa4919b6085e746615530f43f57d2f1`
  and the deny-all Lambda context. Docker emitted two warnings because required
  build arguments have intentionally invalid empty defaults; supplied arguments
  built successfully. All images run as UID/GID 10001:10001. No image was pushed.

**Offline startup check:** Ran a disposable `--rm --network none --read-only`
container with no credentials or database. Hybrid and Identity were disabled;
the adapter file existed, exactly the two read routes plus health were mounted,
app lifespan/health passed, and a synthetic in-process missing-session read
returned 401. The first attempt failed safely because disabling Hybrid while
retaining its inherited interpreter/model paths is an invalid configuration;
clearing those two paths in the test process resolved it. No deployed endpoint,
Lambda Runtime API, actual adapter invocation, real session, SQL, or performance
load was used. Scoped Docker inspection found no leftover containers from this
image. The three task-tagged local images are retained for subsequent local
integration, owned by Rahul, until EXP-03 local validation/cleanup; they have
local disk cost only, no AWS runtime cost. Shared base images/cache are untouched.

**Open:** The live adapter's forwarding/HTTPS host trust, Lambda initialization
and memory fit, real shared SQL sessions including expiry/revocation, aggregate
DB connections/concurrency, account/protocol review, actual dataset parity,
resource inventory/cost, approved deployment/pilot plan, and independent review
remain open. No experiment/NFR pass or EXP-02/03 completion is claimed.

### 2026-11-02 18:06:34 UTC — EXP-03 packaging checkpoint at user-requested stop

User approved public build-image/locked-dependency retrieval and parallel work,
then directed stopping work and committing all current repository changes locally.
All image pulls completed before the stop; no build was started. An empty,
task-specific Docker configuration was used without account credentials. Public
Linux AMD64 image references resolved to these registry digests:
- AWS adapter `public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0`:
  `sha256:17cfd08eff1dfea3f6a9a1e9c65fdac80aa4919b6085e746615530f43f57d2f1`.
- `node:24.22.0-slim`:
  `sha256:91acba91b842bec0bf7ea6f5e09c644c7ccad72c4996ed9616d861d1c7cd60d4`.
- `python:3.14.8-slim-trixie`:
  `sha256:fbecd461fc72d21b2143c6eaba25143738079154a6d0ea3da3aec724f50eed4a`.
- `ghcr.io/astral-sh/uv:0.10.7`:
  `sha256:edd1fd89f3e5b005814cc8f777610445d7b7e3ed05361f9ddfae67bebfe8456a`.

These are observed pull digests, not independent human artifact acceptance or
image-build evidence. A parallel read-only packaging audit found that Lambda's
Dockerfile lacked a context ignore file. Added
`apps/api/Dockerfile.lambda.dockerignore` with a deny-all rule: the Lambda recipe
copies exclusively from image stages and needs no repository build context.
This prevents a root-context build from sending unrelated worktree/local files.
The audit also retained the existing test-mode and trusted-HTTPS ingress gates;
neither image health nor route mounting proves authentication. The separate
parallel static rerun produced no result and is not counted; earlier recorded
checks remain the last test evidence. Parallel work was stopped at user direction.

Pending: local image builds/startup, actual adapter/ALB behavior, real shared SQL
sessions/Hybrid, DB/concurrency limits, Steps 4–6 and independent/affected-owner
review. No deployment, account/secret access, cloud mutation, workload or NFR
measurement occurred. Downloaded tools/wheels/images remain local ignored files
or Docker cache and are not source-commit contents. No push is authorized.

### 2026-11-02 17:38:25 UTC — EXP-03 contract/tooling blockers resolved locally

**Direction/checkpoint:** User verified the 24-wheel preparation. Continued
Step 3 with local artifact/tool discovery and static checks; no new dependency
download was authorized or performed in this increment.

**Node/contract result:** Found the previously retained executable at
`/tmp/clip-cn02-final-node-FbkElB/node-v24.22.0-linux-x64/bin/node`; it reports
**v24.22.0**. Using only a command-scoped PATH, ran
`.venv/bin/python scripts/generate_contracts.py check`: **all eight registered
artifacts current, format 2**. No generated output, lockfile, system Node, global
link or existing environment was changed. This resolves the failed contract
freshness check; it does not verify an upstream Node signature or establish a
permanent tool installation. The temporary tool path must still exist for reuse.

**Docker/privacy result:** The approved read-only Docker cache listing succeeded
with sandbox escalation, without changing socket permissions or daemon settings.
The required API/Hybrid/Lambda build bases and AWS adapter were not listed in the
local cache. The pinned Gitleaks image was cached; the repo's source-only scanner
then ran in its local container with network disabled and passed: **Gitleaks
8.30.1 source snapshot, not Git history**. No application container was started
or modified and no image was downloaded. Docker use remains subject to sandbox
escalation rather than a permanent access repair.

**Remaining:** Session-only wiring, wheel inputs and generated-contract freshness
are locally checked. Public build-image/adapter retrieval and locked npm/Python
dependency retrieval during container packaging need an explicit exception to
the original external-service prohibition (the existing exception covers only
the hash-pinned PyPI wheel download). Adapter digest, local image build/startup,
real SQL/session/Hybrid parity, aggregate DB/concurrency, routing/infrastructure
steps and independent review remain open. No deployment, cloud/account/secret
access, API workload, NFR measurement, commit or publication occurred. Updated
status checkpoint; whitespace check passed. This tooling check awaits verification.

### 2026-11-02 17:35:56 UTC — EXP-03 pinned Linux wheel context prepared with pip

**Authorization/scope:** User verified the explicit exception permitting pip to
download only the repository's hash-pinned wheels from public PyPI. Network
escalation for that exact action was approved. This does not authorize other
public registry/Node downloads, credentials, cloud actions or measurements.
Arch host/system packages and existing helper/API venvs were preserved.

**Download and correction:** Used standalone Python 3.13.12's pip with explicit
public PyPI, isolated configuration, required hashes, binary-only/no-dependency
selection, CPython 3.13/ABI selectors, fixed platforms, zero retries and bounded
timeouts. The initial allowed download stopped on protobuf: the numeric platform
list selected its universal wheel, whose hash differed from the locked binary
wheel. Pip refused it; no wheel files were saved. Installed wheel metadata showed
the `cp310-abi3-manylinux2014_x86_64` tag. Adding that explicit compatible platform
selected the locked binary archive; the retry downloaded all 24 wheels. No pin
or hash was changed and no hash check was bypassed. The canonical deployment
handoff now records the corrected platform list and exact pip-only command.

**Artifact evidence:** `.tools/semantic/wheels` contains **24 wheels totaling
51,910,303 bytes**. Independent checking parsed every requirement and wheel
filename, compared exact version and SHA-256, refused duplicates/missing packages,
and checked ZIP integrity. All passed. A new ignored inventory preserves each
filename, size and SHA-256 plus the requirements file's SHA-256:
`.tools/semantic/wheels-inventory-20261102T173541Z.json`, inventory SHA-256
`eeac7a1f0b3ea3d6c738676ffce52f1af9f6c5ddbf70afea301bf0b306f90be8`.

**Offline installation check:** Created a fresh disposable Python 3.13 venv,
installed all frozen requirements through pip with `--no-index`, only the local
wheel directory, `--require-hashes --only-binary :all: --no-deps`, and ran
`pip check`. Both passed; no broken requirements. The owned disposable venv was
removed afterward; existing helper venv was not replaced. No model inference,
API request, experiment or performance data was produced. No source code,
requirement lock, model/dataset/frozen manifest or system package changed.

**Remaining/checkpoint:** Missing wheel archives are resolved locally. The
adapter v1.1.0 image/digest, Node 24 contract check, Docker socket access, image
build/startup, real DB/session/Hybrid parity and independent review remain open.
Updated the package audit/design and work-log checkpoint; `git diff --check`
passed. No deployment, account/secret access, cloud resource change, commit,
push or PR occurred. This package-input increment awaits user verification.

### 2026-11-02 17:33:16 UTC — EXP-03 Arch/pip-only dependency check and download gate

**Direction/environment:** User reports Arch Linux, initially permits pacman/yay,
then specifically directs Python installation through pip inside a virtual
environment. Read-only evidence shows Linux x86_64, pacman/yay available,
system Node 26.8.2 and pip 26.2.1; no system package was installed or changed.
The existing `.tools/semantic/venv` is already Python 3.13.12, separate from the
API's Python 3.14 environment. Model files remain present and unchanged.

**Offline pip result:** Used the existing standalone Python's pip with
`--isolated --python .tools/semantic/venv/bin/python` to install/check the frozen
Linux requirements with `--no-index --require-hashes --only-binary :all:
--no-deps`. All **24 pinned versions were already satisfied**; no package was
installed or replaced. `pip check` passed: no broken requirements. Pip disabled
its unwritable external cache; no cache permission was changed. Already-installed
packages are not rehashed by this operation: this verifies version satisfaction
and dependency consistency, not the original wheel bytes or image reproducibility.
No inference, workload or performance probe was run.

**Public-download attempt/blocker:** A pip-only wheel-download attempt against
explicit public PyPI failed inside the sandbox; a bounded connectivity check
confirmed DNS resolution was unavailable. The ignored wheel directory now exists
but contains no downloaded artifacts. Requested network escalation for the exact
hash-pinned download. Automatic approval review rejected it because the original
preparation instructions prohibit external-service calls and it found no explicit
scope exception. No alternate execution or download workaround was attempted.
Public wheel retrieval remains pending explicit user approval of that exception.

**Other limits:** A read-only local Docker image-list attempt was denied access
to its Unix socket; no daemon state was changed or image-cache result inferred.
No Node package, adapter manifest/image, model, system package, live account,
secret, database or cloud resource was retrieved or changed. Existing installed
libraries do not replace the missing hash-pinned wheel archives consumed by
`Dockerfile.hybrid`; the package build, adapter digest, Node 24 contract check,
real session/runtime parity and independent review remain pending.

### 2026-11-02 17:24:53 UTC — EXP-03 package-input recheck after session verification

User verified the session-only Identity implementation. Read the Step 3 task,
Lambda/Hybrid image recipes and deployment artifact instructions. Local metadata
checks confirm the CPython 3.13.12 Linux runtime and both model/tokenizer files
are present; the required `.tools/semantic/wheels` directory is still absent.
No adapter image digest is recorded in the searched source/configuration, and
the repository-local Node executable is absent (available system Node 26 remains
incompatible with the contract generator's Node 24 gate). This recheck does not
reverify artifact hashes or inspect the Docker image cache. No download, registry
lookup, build, account/secret access or cloud action occurred.

Next necessary package inputs are the lock-selected Linux wheels, reviewed
adapter v1.1.0 manifest/digest/image and Node 24.22.0 for the outstanding contract
check. Retrieval requires permission to make the public artifact requests because
the user's preparation-only scope forbids external-service calls. Package startup,
real SQL/session checks and independent review remain open; the verified local
implementation does not establish integration or EXP-03 completion.

### 2026-11-02 17:23:04 UTC — EXP-03 Step 3 session-only Identity composition

**Direction/scope:** User took ownership of the previously Aditya-owned session
binding slice and verified implementation. Updated the task index with that
scoped assignment; all ID-01 ownership and independent/affected-owner review
requirements are otherwise retained. This is local Step 3 implementation on
`task/exp-03-lambda`, not Step 4 routing, deployment or measurement. Earlier
paired app-response checks are user-verified. This increment awaits verification.

**Changed code:**
- `apps/api/app/domains/identity/http.py`: `IdentityReadDependencies` validates
  explicit session/browser bindings; `install_identity_reads` installs the
  existing `IdentityBrowserMiddleware` without any Identity HTTP routes. Both
  installation modes reject duplicate or mixed installation. Existing current
  session/account checks, HTTPS/Origin policy, public eligibility dispatch and
  last-seen update are reused. No cookie-derived user claim bypass is introduced.
- `apps/api/app/domains/identity/runtime_configuration.py`:
  `prepare_hosted_test_identity_reads` requires the existing hosted test opt-in,
  reads only the fixed authentication-key and database references, uses existing
  role/key validation and constructs real `IdentitySessions`. Email-route reads,
  sender warmup and Microsoft metadata initialization are skipped. Errors are
  sanitized. It reuses the existing full Identity role and session constructor,
  including dummy Argon2 startup work; this is not a narrowed role or a measured
  startup optimization. No bootstrap was run against real secrets or a database.
- `apps/api/app/application.py`: adds the explicit `identity_reads` parameter,
  permits it only in the guarded Lambda read mode, checks its policy against
  configured origins, and refuses full Identity route installation in Lambda.
  Added missing lifespan factory annotations discovered by Mypy; annotations do
  not change resource behavior. The normal ECS Identity path is retained.
- `apps/api/app/lambda_main.py`: defaults to unauthorized; the existing hosted
  test opt-in selects the new bootstrap and passes its bindings to the restricted
  app. Logging uses the existing safe formatter. Enabling real startup would
  read secrets and audit the DB; no live startup was performed or authorized.
- `apps/api/tests/test_lambda_identity.py`: offline checks cover both account
  classes, cookie-to-session invocation, real public eligibility dispatch,
  missing cookie/forged header denial, simulated session 401/503, expired trusted
  context, ineligible account, HTTPS/Origin rejection before authentication,
  route-surface limits, mode/duplicate guards, opt-in entry selection and
  bounded/sanitized bootstrap behavior. Session/storage callbacks are mocks;
  Starlette threadpool dispatch is replaced only in the offline fixture.
- `scripts/check_boundaries.py` and `tests/architecture/test_boundaries.py`:
  register the Lambda composition root's Identity runtime-module import and
  explicit read-binding names, retaining rejection of other private modules
  and cross-domain consumers. This follows the existing exact-file/module
  exception model rather than granting general access to Identity internals.

**Checks/results:** Focused Lambda routes/app/Identity/Hybrid-runtime plus boundary
suite: **114 passed**. Existing offline Identity key/parameter/transport tests:
**20 passed, 15 deselected**. Existing default ECS startup test: **1 passed,
1 deselected**. Boundary scan: **0 violations**. Mypy passed all four changed
production source files. Pinned Black 26.10.1 and compilation passed all seven
changed Python files; whitespace checks passed. Initial mock assertions expected
keyword arguments where generated public dispatch passes positional arguments:
two tests failed, assertions were corrected, and the full focused suite passed.
The first boundary scan correctly rejected the unregistered composition root;
its scoped registry/test update passed. Mypy initially flagged pre-existing
untyped lifespan factories; annotations resolved it.

**Unavailable/remaining:** Generated-contract freshness check failed before
generation because the available Node is 26.8.2 and the generator requires
Node 24. No generated file was changed, no tool downloaded and no dependency
installed. Full CI, packaged startup, real SQL session expiry/revocation and
concurrency, ECS/Lambda shared-session parity, ingress trust, package inputs,
independent review and merge remain open. The existing session validator updates
last-seen even for listing reads; this preserves ECS behavior and is not a
read-only-SQL claim. No real account/cookie, secret, DB, cloud/provider service,
load workload or measurement was used. Raw results/frozen manifests are untouched.
No commit, push or PR was made. Design and status checkpoints reflect these limits.

### 2026-11-02 17:13:51 UTC — EXP-03 Step 3 local app response parity

**Scope/verification:** User verified comparing the real ECS and restricted
Lambda app compositions with identical synthetic dependencies. Work remains on
`task/exp-03-lambda`, based on `ee4739a774b5cc39e0d6f0c0f07e3089c425aac7`;
existing worktree changes were preserved. This increment changes only the route
test file and these checkpoint documents. Its result awaits user verification.

**Implementation:** Extended `apps/api/tests/test_lambda_read_routes.py` with a
shared fixed detail fixture and nine paired response scenarios: nonempty browse,
Hybrid-labelled search, detail, invalid query, missing authentication, forbidden
account, missing detail, database failure and pool timeout. Each scenario creates
the actual hosted ECS app and narrow Lambda app, requests their real `/api`
routes through in-process ASGI, and compares status, all response headers except
the generated request ID, and JSON except the generated body request ID. Each
ID is validated as a UUID and error body IDs must match their response header.
Success responses and errors are also checked against independently constructed
fixture values and the public error vocabulary, so equality alone cannot make
two incorrect responses pass. Nonempty browse/search checks preserve supplied
item order, complete summary fields, page 2/page size 50/has-next, repeated
category filters and Hybrid query settings. A temporary static web fixture
satisfies hosted ECS composition without requiring a frontend build.

**Checks:** `.venv/bin/python -m pytest -q
apps/api/tests/test_lambda_read_routes.py apps/api/tests/test_lambda_read_app.py
apps/api/tests/domains/listings/test_search_runtime.py` passed: **38 tests**.
Pinned Black 26.10.1 single-file check, Python compilation and `git diff --check`
passed. No production code, configuration, generated contract or frozen input
changed; aggregate/packaged/deployed checks were not run.

**Limits/next gates:** Lifespans are not entered; callers, eligibility and
Listings data are explicit test-only overrides. The ordered results are fixture
transport checks, not reference rankings or proof of SQL availability filtering,
real Identity expiry/revocation, Hybrid inference, ALB/Web Adapter behavior,
connection capacity or package startup. No real account, cookie, network socket,
database, cloud/provider call, k6 workload or measurement was used. Step 3 remains
partial pending the Identity-owned session binding, required package inputs and
real runtime/parity checks. Steps 4–6 and all experiment deployment/measurement
gates remain pending; no commit or publication occurred in this increment.

### 2026-11-02 17:05:05 UTC — EXP-03 Identity binding integration gate

Reviewed the real Identity composition sources after the user verified the
offline route-contract slice. `create_app(identity=...)` installs the full
Identity HTTP router, while `prepare_hosted_test_identity` is the only hosted
initializer found: it reads three SecureStrings, validates the Identity DB
role and warms the email sender. It is guarded for a hosted test environment,
and its complete dependency object would expose Identity routes in the Lambda
app in addition to browse/detail. Therefore it is not a safe drop-in for the
two-read Lambda surface. No secret, Identity account, SSM, database or provider
was accessed. The A/Identity owner must provide/review a session-only binding
that validates the existing cookie/session and eligibility without adding
Identity mutation routes or email warmup; real auth parity remains blocked.

The AWS Web Adapter v1.1.0 release documentation confirms the versioned image
tag used by the recipe, but no immutable image digest is supplied there. The
exact digest and Linux wheels remain package inputs; no registry call, download
or build was made. [AWS Web Adapter release](https://github.com/aws/aws-lambda-web-adapter/releases).

### 2026-11-02 17:07:59 UTC — EXP-02 session approach and account availability

**Direction/input:** The user shared Aditya's recommendation to authenticate
before the measured run and pass the resulting HttpOnly CLIP session cookie to
k6 through a private mechanism. The user also reports that Aditya supplied two
temporary test accounts. This records reported availability only; no account
details or credentials are retained.

**Repository match:** `scripts/evaluation/k6/comparison_session_handoff.py`
already defines `CLIP_COMPARISON_SESSION_COOKIE`. Its helper requires a
caller-provided successful local-preflight marker, accepts only a bounded
`__Host-clip_session` cookie shape, and returns a mapping containing only that
variable. The helper's docstring explicitly says it does not establish session
validity, approval or run readiness. Existing checks use fake values; this is
not yet the real k6 handoff or a verified secure transfer mechanism. The
recommendation is consistent with the prepared pre-run handoff concept, but
does not resolve the EXP-03 need for Identity-owned server-side session and
eligibility validation in the narrow Lambda application.

**Checks and limits:** Read the helper, current checkpoint, EXP-02 history,
EXP-03 design and status rows. No account was accessed, no session was created,
no request or workload was sent, and no cloud/provider/database action occurred.
The approved account class and use of the reported temporary accounts remain
subject to the existing owner/protocol gate; secure local transfer, session
expiry/validity checks and actual-run authorization remain open.

### 2026-11-02 17:00:11 UTC — EXP-03 Step 3 offline route-contract checks

**Scope and environment:** User verified this Step 3 increment. Work is on the
isolated local branch `task/exp-03-lambda`; prior uncommitted EXP-03 changes were
preserved. The tests use the pinned local Python environment, synthetic callers
through an explicit dependency override, in-memory ASGI transport and fake
Listings adapters. No socket, database, Identity account, cloud service or live
API was contacted.

**Change:** Added `apps/api/tests/test_lambda_read_routes.py`. The test exercises
the actual restricted app and router while replacing only the trusted caller
and Listings dependency boundaries. It checks a successful Hybrid-labelled
request preserves repeated category filters, price, page, page size, query and
sort in the service input and emits the expected page shape; missing caller
returns 401; invalid price returns a value-free 422; ineligible caller returns
403 before store access; detail returns the requested listing ID and retains
404 behavior; synthetic PostgreSQL operational and pool timeout exceptions are
translated to the safe 503 envelope without exposing diagnostics. These are
contract checks over test doubles, not proof that the model, real session or
real database behaves on Lambda.

**Harness finding:** A full-app request using the normal synchronous service
factory stalled in this sandbox. The reliable test harness uses an async,
test-only dependency override at the Listings service boundary. This avoids the
stall; the underlying cause has not been established. Production app wiring was
not changed.

**Checks:** Three focused suites passed: `test_lambda_read_routes.py`,
`test_lambda_read_app.py` and Listings `test_search_runtime.py` (29 passed).
Black's multi-file CLI invocation could not start its process pool in the
sandbox (`PermissionError`); Black's in-process formatter check passed for all
11 touched Python files. `py_compile` for those files and `git diff --check`
passed. No workload or measurement was run.

**Remaining:** Real Identity session composition and owner review, real
Hybrid/model startup, database headroom/concurrency review, Linux wheels,
approved adapter digest and image build, routing implementation, and all
deployment/experiment gates remain pending. This Step 3 route-test increment
awaits user verification; continue only within Step 3 after verification.

### 2026-11-02 16:41:04 UTC — EXP-03 bounded Hybrid runtime check

**Verification:** User verified the preceding narrow app-composition checkpoint.
The next offline check targeted the Hybrid pool override without an external
database, model process, Identity account or cloud service.

**Change:** `apps/api/tests/domains/listings/test_search_runtime.py` adds a
synthetic ready-runtime case that enables the normal worker setting, then calls
the Lambda override with `pool_max_size=1` and `enable_worker=False`. It asserts
the constructed pool min/max are both one and that no dispatcher starts. This
tests the override itself, not actual model inference or DB capacity.

**Check:** The full `test_search_runtime.py` and `test_lambda_read_app.py` suites
passed: 22 tests. Black CLI remains unable to start its sandbox forkserver, so
formatting was checked through Black's in-process API. Python compilation and
`git diff --check` passed. An experimental in-process HTTP/ASGI harness stalled
inside request handling, as did Starlette `TestClient`; that harness was removed.
No route-level HTTP status/parity result is claimed.

**Remaining:** EXP-03 Step 3 still needs reliable route-level success, validation,
auth/forbidden/not-found and dependency failure/timeout checks. Real Identity
session composition and real Hybrid startup are separate owner/integration
gates. No experiment, deployment or external request was made.

### 2026-11-02 16:36:10 UTC — EXP-03 narrow Listings/Search app composition

**Direction and scope:** User verified implementing a separate read-only Lambda
startup path while preserving normal ECS startup. Work was local and offline;
no deployed target, database, credentials, cloud resources or experiment were
used. No worktree changes from other contributors were overwritten.

**Changes:** `apps/api/app/application.py` adds an explicit
`listings_read_only` composition mode. It mounts only browse/search GET
`/api/listings` and detail GET `/api/listings/{listing_id}`, caps the Listings
pool at one connection and requests a one-connection Hybrid pool, disables the
Hybrid worker, and skips Conversations, notifications, wanted/saved stores and
S3 image storage. Default ECS mode retains its prior route and pool settings.
`apps/api/app/domains/listings/routes.py` provides the separate route collection
using the existing browse and detail handlers. `apps/api/app/domains/listings/search_runtime.py`
accepts a pool cap and worker override while preserving its existing defaults.
`apps/api/app/lambda_main.py` is the restricted ASGI entry point and intentionally
does not create Identity bindings or a synthetic user;
missing caller context still returns unauthorized. `apps/api/Dockerfile.lambda`
selects this entry point while the ECS Dockerfile remains unchanged.

**Tests:** `apps/api/tests/test_lambda_read_app.py` verifies the exact app route
and method surface through OpenAPI metadata and checks with fake/no-resource
lifecycles that each pool is bounded and Conversations, S3 and notifications do
not start. The new tests passed (2). Existing combined-lifecycle tests passed
(10). Black's normal command could not create its multiprocessing forkserver
socket in this sandbox (`PermissionError`); the modified Python files were
formatted with Black's in-process API. `git diff --check` passed. Attempts to
start the repository's Starlette `TestClient` hung even on the unchanged health
app in this environment, so request-level transport behavior is not claimed.

**Limits and next gate:** This does not prove Hybrid can start in the one-pool
configuration, that an authenticated request can reach the Lambda app, or that
the aggregate DB budget supports any concurrency. Current `create_app` wiring
does not provide a production-ready Identity binding; this Lambda entry fails
closed until Identity provides and reviews its supported real-session
composition. DB owner review must determine concurrency/headroom. Linux wheels,
adapter digest, image build, listener, cloud deployment and A/B parity remain
open. No experiment was run; EXP-03 remains in progress.

### 2026-11-02 16:22:12 UTC — EXP-03 database connection budget check

Inspected application pool settings and the installed psycopg-pool signature.
Listings max is 10 and inherits min 4; Hybrid max is 2; the separate Conversations
pool max is 1. Full app maximum is therefore 13 retained pooled connections per
Lambda environment (12 from Listings+Hybrid alone), or 260 at proposed
concurrency 20; two retained ECS tasks could add up to 26. Identity uses fresh
direct DB connections, not included, so actual peaks may be higher. At proposed
DB cap 60, 20 Lambda instances with just one persistent connection per pool would
already consume 40 before Identity and leave no headroom for ECS/admin. The
default pool/concurrency proposals do not fit together. Lower concurrency,
narrower lifecycle/pools, or a separately reviewed connection-proxy/DB limit
decision is required. No live DB or cloud query was made.

### 2026-11-02 16:18:30 UTC — EXP-03 Lambda image recipe

Added `apps/api/Dockerfile.lambda`, which extends the existing Hybrid API image
with the AWS Lambda Web Adapter 1.1.0 binary from its versioned OCI image. The
build requires a SHA-256 image digest and does not alter the ECS image. It sets
the adapter to the inherited Uvicorn port 8000 and `/health` readiness route.
The digest has not been resolved from an approved artifact receipt, the adapter
was not downloaded, and the image was not built. Existing Hybrid Linux wheels
are also absent. The exact adapter digest, target platform and runtime image
remain build gates. `git diff --check` passed; no network or cloud call was made.


### 2026-11-02 16:16:29 UTC — EXP-03 ALB rule proposal specified

After the user verified the AWS Lambda Web Adapter direction, specified
configuration B listener candidates: GET exact `/api/listings` and GET
`/api/listings/*`, with ECS as the default, and configuration A routing both to
ECS. Multi-value headers are required. Extra detail-path segments may hit the
Lambda target but must retain API 404 semantics; writes and other operations
must remain ECS-bound. Existing Uvicorn uses port 8000, and `/health` is the
readiness candidate. This is a local design proposal, not Terraform or a claim
that ALB behavior was tested. Exact listener review, target-group settings,
origin and deployment plan remain open.

### 2026-11-02 16:15:00 UTC — EXP-03 adapter recommendation refined

Read the AWS Lambda Web Adapter's official guide and ALB's official Lambda target
documentation. The AWS-maintained web adapter supports ALB events and container
images, translating events to HTTP for a normal web server; the API already runs
Uvicorn. Recommend pinning and locally verifying this extension instead of
maintaining the custom event-to-ASGI bridge as a production adapter. ALB
multi-value headers must be enabled and checked for repeated filters/cookies;
ALB documents a 1 MB Lambda response JSON limit. The custom `alb_event.py` and
`alb_asgi.py` remain synthetic probes only and should not be wired into the app.
This is a refinement proposal; no extension artifact was downloaded or tested,
and trusted host/scheme, app lifecycle, response size and resource startup remain
to verify. Sources: [AWS Lambda Web Adapter guide](https://aws.github.io/aws-lambda-web-adapter/),
[ALB Lambda target guide](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html).

### 2026-11-02 16:11:55 UTC — EXP-03 local image availability check

Inspected local Docker images and pinned artifact directories only. No project API
or Hybrid image is locally cached; no Linux wheel archive exists in the reviewed
uv cache or `.tools/semantic/wheels`. A local Docker daemon is reachable, but
building the documented image is blocked until the exact pinned wheel artifacts
are prepared. No build, download, network, inference or deployment was attempted.
The cache check does not prove artifacts are unavailable elsewhere.

### 2026-11-02 16:10:15 UTC — EXP-03 package-audit correction

Correction to the 16:05:45 entry: the current Hybrid Dockerfile copies only
`onnx/model.onnx` and `tokenizer.json` from the model context. Both local files
exist at the manifest sizes. The five other manifest files are not copied by
that Dockerfile, so their absence alone does not block the documented build.
The missing Linux wheel directory remains a known missing input; no build was
attempted. The earlier statement that all seven manifest files were required
was incorrect.

### 2026-11-02 16:07:32 UTC — EXP-03 route restriction and regression correction

Following user verification, restricted the local bridge to GET collection and
UUID-shaped detail paths, and added refusal checks for availability mutation,
images and owner-management reads. The first test run exposed a test case that
incorrectly classified the approved detail route as disallowed (17 passed, 1
failed); corrected the case and added an explicit positive detail-route check.
The rerun passed all 18 parser/bridge tests; Black and `git diff --check` passed.
This local path guard does not replace ALB listener review or authentication.
No live service or cloud request was made.

### 2026-11-02 16:05:45 UTC — EXP-03 local package-input audit

Inspected ignored local build-input names and byte counts against the committed
model manifest and Hybrid Dockerfile; no file contents, credentials, network,
build or inference were used. ONNX (90,405,214 bytes) and tokenizer (466,247
bytes) match manifest sizes. Python 3.13.12 directory is 98,143,362 bytes and
helper virtualenv 172,887,905 bytes. The Linux-wheel directory is absent; five
other manifest files are absent. This is insufficient for the documented
reproducible build. No Lambda image size, startup, memory fit or inference result
is claimed. Obtain the exact pinned wheel/model inputs through the established
semantic artifact workflow before attempting a local offline image build.

### 2026-11-02 16:03:47 UTC — EXP-03 Step 3 parser safety and API boundary

User verified the synthetic bridge and requested grouped progress. Tightened the
event parser to reject invalid header names and malformed empty query fields;
its representation no longer displays headers or cookies. Added a local test
passing a forged caller header through the bridge to the real API with Identity
unbound; the real Listings route rejected it with 401. This is not a real-session
test and does not prove trusted ingress or deployed authentication.

Fourteen focused parser/bridge tests passed, Black check passed for all four
files, and `git diff --check` passed. No provider, database, cloud, listener or
load test was used. Real Lambda handler, session integration, lifecycle,
packaging and independent review remain open.

### 2026-11-02 15:59:37 UTC — EXP-03 Step 3 in-process ASGI bridge draft

**Scope:** User verified the parsing increment. Added a standalone ALB-to-ASGI
bridge that calls an injected app, checks an explicitly supplied host, preserves
multi-value response headers and bounds response size. It handles synthetic
in-process requests only in tests. This is not an installed Lambda handler and
does not establish invocation-source trust, session authentication, app startup,
database lifecycle, security or deployment suitability. Its hard-coded HTTPS
scope is safe only after the future integration proves trusted ingress.

**Checks:** Nine synthetic parser/bridge tests passed; Black check passed for
both new bridge files and `git diff --check` passed. No listener, provider, live
request, cloud resource or measurement was used. Real app/auth integration,
event validation, routing, warm lifecycle and independent owner review remain.

### 2026-11-02 15:56:37 UTC — EXP-03 Step 3 ALB event parsing draft

**Scope:** Following user verification, added a standalone local parser for
synthetic ALB multi-value bodyless GET events and focused tests. It preserves
repeated query values and header values, bounds outputs and rejects malformed
requests without logging their values. It is not a Lambda handler, routing,
authentication, origin validation, application invocation or deployment. It is
not wired to an app; ALB event semantics and security require owner review.

**Checks:** `pytest -q apps/api/tests/test_alb_event.py`: 6 passed. Black
format/check passed when called once per file; an initial two-file Black call
failed because sandbox process creation was denied. `git diff --check` passed.
No network, cloud, database, provider or workload request was made. Exact adapter,
Identity integration, real model packaging and Lambda lifecycle remain open.

### 2026-11-02 15:40:50 UTC — EXP-03 ALB design draft

**Direction:** User asked to continue after confirming ALB availability. Drafted
the [Lambda design](exp-03-lambda-design.md) with same-origin A/B routing,
method-and-path restrictions, real Identity/Hybrid behavior, safe lifecycle,
database budgeting, rollback and review gates. Inspected existing app and
Identity startup and Terraform ownership; no code, cloud call or load run.

**Finding:** The current whole-app startup also opens a Conversations pool and
hosted Identity startup warms its email sender. A narrow Lambda cannot be assumed
to avoid those dependencies merely by routing reads. Exact adapter and trusted
ingress handling, Identity public integration, per-instance/aggregate connections,
model fit and infrastructure ownership need affected-owner review. The document
is a proposal, not proof of equivalent or deployable behavior.

**Check:** `git diff --check`; user verification and independent owner reviews
remain before dependent implementation.

### 2026-11-02 15:39:28 UTC — EXP-03 ALB availability reported

**Direction:** User confirmed that an Application Load Balancer can be created.
Use ALB routing as the working Lambda design. This is user-reported availability;
the earlier read-only checks did not independently establish create permission
or resolve the historical AWS rejection. No resource was created or changed.

**Remaining:** Specify and review exact listener rules, same-origin sessions,
trusted HTTPS and query handling, network and resource costs, database connection
limits, model packaging, and rollback. Separate exact cloud-plan approval remains
necessary before any provisioning or deployment.

### 2026-11-02 14:22:02 UTC — EXP-03 read-only load-balancer check

**Direction and target:** User requested a current check of whether a load
balancer can be created. Read-only AWS calls used the configured non-root
`clip-project` profile; STS identified the project account in `ap-south-1`.
No resource was created, modified or deleted.

**Evidence:** Service Quotas reported 50 Application Load Balancers per region
(`L-53DA6B97`); ELBv2 described zero existing Application Load Balancers in that
region. The caller was denied `iam:SimulatePrincipalPolicy`, so the create
permission could not be checked this way. Available quota is not proof that AWS
will permit creation: the previously observed account-wide service rejection
and other policy or account restrictions are not resolved by these reads. No
create attempt was made; current actual ability to create remains unverified.

### 2026-11-02 14:16:44 UTC — EXP-03 local feasibility findings

**Direction:** User approved the proposed investigation and recommendations,
conditional on feasibility and affected-owner review. Inspected repository
ingress, Hybrid image and model manifest locally; no cloud or network action,
build, inference, benchmark or deployed test was performed.

**Findings:** The retained hosted setup uses an EC2/Caddy HTTPS proxy to ECS,
not an existing Application Load Balancer. Historical deployment evidence says
AWS rejected load-balancer creation account-wide on 2026-10-26; current account
status is unknown. An ALB therefore cannot be assumed available. Routing from
the existing proxy through a Lambda HTTP ingress is an alternative to investigate;
its same-origin cookies, TLS trust, networking, permissions and cost are not yet
established. No new ingress choice is approved merely by approving investigation.

The tracked model manifest records a 90,405,214-byte ONNX file and a 466,247-byte
tokenizer; actual model files are not committed. The Hybrid Dockerfile requires
separate pinned Python, wheels and model build contexts and runs offline model
inference during its build. Those artifact contexts and Lambda-compatible image
have not been inspected or built here. No Lambda ASGI adapter dependency appeared
in the inspected root package lock. Real model fit, startup and parity remain
unproven. Existing Identity initialization may access secret storage and a DB;
it must not run in local checks and requires an approved runtime design.

**Next:** Resolve the ingress and trusted request representation with the
Identity/infrastructure owners, audit bounded per-instance connections and select
an adapter only after its lifecycle, security and packaging fit are established.
Deployment and performance execution remain outside this authorization.

### 2026-11-02 14:12:04 UTC — EXP-03 Step 2 initial design

**Scope:** User verified Step 1 and authorized the design step. Reviewed the
existing Identity middleware, app creation, Hybrid image and shared runtime
configuration; no code, image, deployment, workload or external call was made.

**Proposed design:** Package the existing Python app and real Hybrid helper/model
as a Lambda container image, with an HTTP-to-ASGI adapter and a warm-instance
lifecycle that retains initialized resources where safe. Route only the two
selected GET operations to the mixed path; leave writes and other routes on ECS.
Reuse Identity's actual session authentication and Listings behavior; never
trust a caller identity supplied by the client. Pass the request and response
semantics, including status, headers, query and pagination, unchanged. Use the
same private PostgreSQL and model/index revisions. Never log session values,
request bodies or private response data; return existing safe errors on failure.

**Unresolved feasibility and review:** The adapter/event type and ingress topology
are not selected: their trusted HTTPS/origin/host/client context, same-origin
session cookie forwarding, exact route matching and rollback need Security/Identity
and infrastructure review. The helper's real binaries and model must fit Lambda's
package, memory and startup/time budget; this has not been verified. The existing
Listings pool permits 10 connections and Hybrid pool two per instance, before
other Identity/Conversations connections, so the current settings cannot simply
be multiplied by the proposed 20-instance ceiling while assuming the database
budget is met. Pool and session-access limits require an audited design. No
adapter, ingress, package, security or performance feasibility is claimed.

**Next gate:** User and affected owners must review the proposed direction and
resolve these points before dependent implementation. Existing task limits are
proposals subject to the reviewed run plan; the user has made the 300-client
proposal non-binding. EXP-02 remains incomplete; no cloud action is authorized.

### 2026-11-02 14:09:40 UTC — EXP-03 Step 1 route and runtime inspection

**Direction and scope:** The user directed starting the Lambda path alongside
unfinished EXP-02 and verified the inspection step. Inspected local source at
`90523cf`; no deployment, API call, experiment or application change occurred.
The task index still records EXP-02 as an EXP-03 dependency; this overlap does
not establish EXP-02 completion or authorize cloud actions.

**Findings:** Browse and Hybrid search share `GET /listings`; listing detail is
`GET /listings/{listing_id}`. Both require Identity-established caller context;
client-supplied identity cannot substitute for session validation. Browse returns
private, non-cacheable results, while detail includes the owner's permitted
unavailable listings. Existing application startup opens a Listings database
pool of up to 10 connections; Hybrid startup separately opens a pool of up to
two and starts a model helper subprocess. Replicating that per Lambda execution
environment without a reviewed design could multiply database connections and
model startup costs. The real helper, model, permissions, failure semantics and
same database must be retained; no Lambda equivalent has yet been demonstrated.

**Checks and next gate:** Read the task definition, application lifespan,
Listings route implementations, caller dependency and Hybrid runtime; no tests
were appropriate for this read-only inspection. The adapter, trusted session
handling, helper packaging, database limits and routing remain design decisions
for Step 2 and affected-owner review. User verification of these findings is
pending; local inspection does not prove deployed parity.

### 2026-11-02 14:01:05 UTC — EXP-03 ownership and design inspection

**Direction:** User verified the previous checkpoint and assigned EXP-03 Lambda
work to themselves, Rahul (D). Updated the task registry and task owner; the
roster's default independent peer A and affected Search/infrastructure owners
remain review participants. Rahul is the writer for this bounded ownership and
design-record update. No code, cloud resource, workload or external service was
changed or contacted.

**Read-only findings:** The selected collection and detail operations are in the
Listings router. `require_caller` uses Identity-established ASGI context rather
than client-provided identity; the Lambda path must preserve it. The application
lifespan opens Listings/Search and Conversations database pools and starts the
configured search runtime; reuse and Lambda lifecycle/connection costs need
design and review. The task also requires the actual Hybrid model/helper, route
selection, parity, resource bounds and failure behavior. No implementation or
deployed equivalence is claimed.

**Gates:** EXP-03's recorded formal dependency is completed EXP-02, which remains
open. Exact task understanding, target/adapter decisions and independent owner
reviews remain before dependent implementation. Existing instruction excludes
cloud actions and experiments. The preliminary inspection is not task
acceptance; the user assignment does not imply deployment approval.

### 2026-11-02 13:57:21 UTC — Local parity workload and EXP-03 preliminary inspection

**Direction:** User requested finishing essential EXP-02 work and starting
EXP-03 preparation. Worked offline; no workload, deployment, cloud or external
request was performed. EXP-02 remains incomplete and EXP-03's formal start
dependency remains pending.

**EXP-02:** Added an explicit local-only parity-draft workload path. It validates
the ten supplied synthetic response pairs against the workload cases before
reading the local session, uses the draft search response checker, and keeps
the prior mode. Parity input errors are sanitized. Added both comparator modules
to the staged-module inventory and blank hash template. Synthetic tests cover
valid/mismatched/missing pairs and session-read ordering; `k6 inspect` verifies
draft and prior initialization without executing a workload.

**EXP-03 preliminary read-only inspection:** The selected Listings read is
`GET /listings` in `apps/api/app/domains/listings/browse_routes.py`; it uses the
shared caller dependency and configured Listings store. `apps/api/app/application.py`
composes these routers with shared startup/lifespan and Identity configuration.
No Lambda adapter was identified by the targeted local source search. EXP-03
still needs its owner B, task-understanding verification, accepted EXP-02 and
reviewed decisions on routing, auth, lifecycle, database connections and packaging
before dependent implementation; no infrastructure was changed.

**Checks and limitations:** Five selected staging/`k6 inspect` tests passed
before the final sanitized-error change; four `k6 inspect` tests passed afterwards.
Three synthetic Node test files, strict Mypy, Black and whitespace checks passed.
The supplied parity file is not proof of response origin, deployment, review or
freshness. Normal run preflight still rejects the draft, the target remains
loopback-only, and the timing and real-runner gates remain open. No experiment or
NFR pass is claimed. Result awaits user verification.

### 2026-11-02 13:45:38 UTC — Local workload session-read ordering

**Direction:** User verified continuing preparation. All checks used synthetic
inputs and local fakes or `k6 inspect`; no workload or external request ran.

**Change:** Moved local workload session-variable access after its load flag,
profile, case/path and selected schedule checks. A fake environment observes
that seven invalid setup paths stop before reading the synthetic session.
The guide distinguishes these local shape checks from full archive binding,
review, parity and authorization, which still belong to the future real runner.

**Checks and limits:** Three synthetic Node test files and three `k6 inspect`
checks passed; whitespace checks passed. The workload still accepts only local
targets and the old exact references. This change does not establish complete
corpus validation before a real session, authenticate a deployment or authorize
measurement. Result awaits user verification; no NFR pass is claimed.

### 2026-11-02 13:42:03 UTC — Offline combined parity command

**Direction:** User verified continuing the offline search-parity integration.
Only synthetic local inputs were used; no session, workload or external call.

**Change:** Added a command for the existing connected draft preflight and
ten-case comparator. It reads bounded local inputs and synthetic response pairs
from standard input, emits only hashes/counts/flags and exits nonzero for a
difference or invalid input. The guide specifies arguments and input. The
integration test exercises command success and mismatch, and checks query text
is absent from output.

**Checks and limits:** Two focused synthetic integration/profile tests, strict
Mypy, Black and whitespace checks passed. This command does not obtain responses,
authenticate either deployed path, establish relevance or authorize a run.
The actual runner, deployment parity, timing, account and affected-owner review
gates remain open. Result awaits user verification; no NFR pass is claimed.

### 2026-11-02 13:38:47 UTC — Offline draft input and parity preparation

**Direction:** User verified continuing. Connected draft-input checks and the
ten-case comparison with synthetic responses only; no session, workload, cloud
or external request occurred.

**Change:** Added a bounded offline Python helper that first validates the
archive-bound draft, paired plan and selected profile hash, then invokes the
fixed local Node comparator using standard input. It returns only corpus/profile
hashes and aggregate counts, with deployment, independent correctness and
measurement authorization false. Tests verify bad bindings stop before the
comparator, all ten fabricated matches pass, one mismatch is visible, and query
content is absent from the result. The guide records the interface and limits.

**Checks and limits:** Two focused integration tests, strict Mypy, Black and
whitespace checks passed. The helper is not a real runner or enforced gate; it
does not fetch responses, prove actual deployment or establish search relevance.
The normal run preflight remains closed to the draft. Protocol and owner review,
actual parity, account, timing and telemetry remain open. Result awaits user
verification; no experiment or NFR pass is claimed.

### 2026-11-02 13:34:00 UTC — Offline parity draft profiles

**Direction:** User verified continuing and requested grouped work. Prepared
profiles and checks offline; no workload, session, provider or network call.

**Change:** The existing profile builder accepts an explicit `--parity-draft`
mode, and the underlying preflight can explicitly check that draft against the
dataset-bound corpus and paired plan. It generates cycle-specific profile bytes
without inventing search rankings and always reports measurement unauthorized.
Normal preflight/staging callers retain the default refusal; the workload also
rejects null search expectations. The guide explains the separate draft path.

**Checks and limits:** Thirty-three selected focused tests passed before the
final CLI assertion and explicit draft-result flag; three relevant tests passed
again afterwards, including all three cycles, CLI use and default run refusal.
Strict Mypy, Black and whitespace checks passed. Actual target/account access,
response comparison enforcement, timing and affected-owner review remain open.
Result awaits user verification; no experiment or NFR pass is claimed.

### 2026-11-02 13:30:11 UTC — Offline comparison of all ten cases

**Direction:** User verified continuing the comparison preparation. No deployed
responses, sessions, workload or network calls were used.

**Change:** Extended the offline comparison to all five browse, three search
and two detail cases. It requires matching case IDs and request settings,
validates both responses and compares their complete contents, returning only
aggregate flags. The existing offline command accepts `--all`; search-only mode
remains available. Synthetic tests exercise matching responses, changed browse,
search and detail fields, invalid case mixes and command failure on mismatch.
The guide records the option and limits.

**Checks and limits:** Three Node test files and whitespace checks passed. This
does not authenticate the supplied corpus, independently establish correctness,
verify deployments or authorize runs. It does not replace the still-required
pre-run runner integration, owner review, or NFR-02/04 checks. Result awaits
user verification; no experiment or NFR pass is claimed.

### 2026-11-02 13:28:30 UTC — Proposed parity workload response checks

**Direction:** User verified continuing grouped preparation. No workload,
session, deployed response or network call was used.

**Change:** Added a pure draft-mode case checker: search requires the expected
page to be null and checks successful status, response shape, availability and
filters; browse and detail retain their exact expected responses. Synthetic tests
cover valid and malformed searches, failed status, changed browse/detail fields
and missing expected data. The guide explains its scope.

**Checks and limits:** Three Node test files and whitespace checks passed. The
helper does not verify relevance or pre-run A/B parity, and the actual workload
does not call it. The existing preflight and workload continue to enforce the
old reference until the complete replacement and owner review are ready. No
measurement or NFR pass is claimed. Result awaits user verification.

### 2026-11-02 13:22:34 UTC — Offline search parity command

**Direction:** User verified continuing and requested grouped work. Prepared an
offline comparator command, synthetic checks and documentation; no workload,
real response, session or external call occurred.

**Change:** The bounded Node command reads a supplied corpus and three A/B
response pairs on standard input, uses the existing comparison helper and prints
aggregate flags only. It exits nonzero on invalid inputs or any mismatch and
never obtains responses itself. Tests exercise matched/mismatched data, malformed
and oversized inputs and absence of query content in output. The guide describes
the strict format and limits. Existing run gates remain in force.

**Checks and limits:** Two Node test files and 21 Python parity/binding tests
passed; whitespace checks passed. Initial Node command tests timed out when a
synthetic input used a child-process pipe, and then exposed missing captured
output; using a local fixture file for test input and synchronous command output
resolved both, with the rerun passing. No actual deployment, dataset authenticity,
relevance or authorization is established; the real runner and pre-run parity
gate remain unimplemented. Result awaits user verification.

### 2026-11-02 13:20:23 UTC — Search parity corpus preparation command

**Direction:** User verified continuing the search-parity preparation. No
network, workload, cloud action or actual result collection occurred.

**Change:** Added an offline command to the corpus builder and a blank version-2
binding template. The command reads a bounded regular local binding, validates
the dataset/schema/contract/model and explicit revision, then exclusively
creates a separate non-executable corpus. It prints sanitized aggregate status
and cannot replace an existing output. The guide records the exact command.

**Checks and limits:** Twenty-one focused archive/synthetic tests and strict
Mypy passed; tests cover deterministic outputs, refusal to overwrite, bad input,
and sanitized errors. Black and whitespace checks passed. The corpus is a draft;
real-run preflight still refuses it, and the actual response comparison gate,
deployment, timing and affected-owner reviews remain open. Result awaits user
verification; no experiment or NFR pass is claimed.

### 2026-11-02 13:17:37 UTC — Synthetic parity draft integration check

**Direction:** User verified checking the draft-input preflight and three-search
comparison together offline. No session, workload or external request occurred.

**Change and checks:** An integration test builds the archive-bound draft,
validates its declared bindings, and passes its three cases and fabricated empty
pages to the existing JavaScript comparator via a local Node process. It checks
matching pages and a simulated failed response, verifies aggregate output does
not include query text and confirms deployment remains unverified. Twenty
focused synthetic/archive tests and whitespace checks passed.

**Limits:** This is a test of separate components, not a real runner or an
enforced pre-run gate. Empty matching pages are not relevance evidence; real
search responses, deployment identity, parity and affected-owner review remain
open. Combined run preflight continues to refuse the draft. Result awaits user
verification; no experiment or NFR pass is claimed.

### 2026-11-02 13:11:51 UTC — Offline parity draft binding check

**Direction:** User verified connecting the search case draft to offline
preflight while keeping the actual run gate closed. No request or workload ran.

**Change:** The existing binding checker can explicitly accept a version-2
parity draft, rebuild it from the archive and compare exact JSON contents and
declared hashes/revisions. Without the explicit offline-only option it refuses
the draft; combined run preflight still uses that default refusal. Captured-run
manifest use remains disallowed. The command retains its legacy positional
argument and adds `--parity-draft`; no run is authorized by it.

**Checks and limits:** Nineteen binding/corpus tests, strict Mypy, Black and
whitespace checks passed. Tests include altered requests and refusal through the
combined run preflight. This is input consistency, not A/B response comparison,
deployed identity, owner approval or execution readiness. Workload and actual
response parity gate remain unconnected. Result awaits user verification.

### 2026-11-02 12:59:58 UTC — Proposed parity corpus binding

**Direction:** User verified preparing dataset-bound search inputs without a
hand-written ranking; no workload, network or actual result collection occurred.

**Change:** Added a separate non-executable corpus builder. Its strict version-2
binding requires the retained dataset, schema, search contract, model and an
explicit matching full search implementation commit. It rebuilds the existing
ten archive-bound cases, preserves browse/detail expectations, leaves all three
search expected pages null and marks measurement disabled. No frozen manifest,
label or acceptance record was edited. The guide specifies the input fields.

**Checks and limitations:** Eight focused synthetic/archive tests, strict Mypy,
Black formatting and whitespace checks passed. The helper is not wired into the
existing preflight or workload, which still require ordered references; matching
input declarations do not prove review, deployed identity, search correctness or
parity. The protocol change and affected-owner review remain open. Result awaits
user verification; no experiment or NFR pass is claimed.

### 2026-11-02 12:57:43 UTC — Bind search parity inputs to corpus cases

**Direction:** User verified continuing preparation without a hand-written
search order. The work used synthetic responses only; no workload or network.

**Change:** The offline parity adapter now requires the supplied corpus, matches
each of its three search case IDs and exact request settings, and requires the
direct-word, related-word and meaning-based classes. Synthetic tests cover
changed requests, duplicate IDs and incorrect class sets. The adapter outputs
an explicit false corpus-authenticity flag; matching a supplied corpus does not
establish its fingerprint, review or deployment use.

**Checks and limits:** Both search-check Node test files and whitespace checks
passed. The legacy ordered-reference preflight and workload remain in force;
the new adapter is not yet a real-target gate and cannot verify relevance or
the corpus itself. Coordinated implementation and owner review remain open.
Result awaits user verification; no experiment or NFR pass is claimed.

### 2026-11-02 12:55:29 UTC — Offline three-search parity adapter

**Direction:** User verified continuing the search-check integration. No
workload, network call or deployed response was collected.

**Change:** Added a bounded offline adapter connecting the existing valid-page
and response-equality checks for three distinct search cases. It returns counts
only and marks independent correctness, deployment and authorization unverified.
Synthetic tests cover matching, failed, missing, duplicate and malformed inputs
and ensure query content is not returned. The guide documents the interface.

**Checks and limits:** Both synthetic Node test files and whitespace checks
passed. This function does not fetch or verify responses, bind the three query
classes, or judge relevance; two valid empty pages can match. It is not yet
connected to the real runner or parity gate. Existing ordered-reference preflight
and workload remain unchanged until a complete reviewed replacement exists.
Result awaits user verification; no experiment or NFR pass is claimed.

### 2026-11-02 12:50:53 UTC — Proposed comparison search parity checks

**Direction:** User verified the trace and requested repository search
requirements plus A/B equivalence. No live calls or measurements occurred.

**Change:** The experiment design now records a proposed search-row revision,
pending affected-owner review, that checks valid search responses and compares
the two paths before measurement without a human-authored exact ranking for
the three cases. Browse/detail references and separate NFR-02/04 requirements
are retained. Added local pure functions to validate search response shape and
filters and compare two valid pages exactly, including ordering and fields.
The Hybrid decision and calibration documents specify a UUID final tie-breaker.

**Checks and limits:** Synthetic Node checks cover matching and changed pages,
order, invalid filters and status; whitespace passed. A valid empty page is not
evidence of search relevance, and equal valid responses do not establish dataset
identity or usefulness. These new functions are not wired to staging or a real
runner. The existing binder, preflight and workload still require the old exact
reference; no existing gate was bypassed. Completing their coordinated update,
reviewing expected behavior for empty cases and affected-owner review remain
open. Result awaits user verification; no experiment or NFR pass is claimed.

### 2026-11-02 12:48:25 UTC — Comparison search requirement change trace

**Direction:** User requested using repository search requirements and checking
the two paths for equivalence for other response details. User verified tracing
the current requirements and affected tooling before implementing changes.

**Findings:** The comparison protocol's Hybrid row currently requires reviewed
exact IDs, order, page and fields; its dataset paragraph requires independently
reviewed expected outcomes. The separate SE-01 NFR-04 procedure requires a
human-reviewed labeled set and Success@5, and NFR-02 retains its own expected
result and issued-eligible denominator requirements. These are distinct gates.
`comparison_checks.js` currently requires full exact response equality for all
three classes. The ordered-result binder, binding preflight, profile builder,
paired preflight, parity validator, offline preparation and staging depend on
the ordered reference. The current parity validator compares declarations and
hashes, not A/B response contents. The preparation and workload guides describe
the old dependency.

**Next step and limits:** Change the comparison protocol and affected checks in
a reviewed, coordinated unit, retaining explicit search requirements and a
pre-run content-equivalence gate. Define how ties, malformed responses and
unexpected empty results are judged from existing contracts; do not infer
correctness merely from both paths agreeing. Preserve separate NFR-02/04 rules.
No script or frozen record changed in this trace. Affected-owner protocol review
and actual deployment verification remain open. Result awaits user verification.

### 2026-11-02 12:31:17 UTC — NFR-05 synthetic event collector

**Direction:** User verified local event-collector preparation with simulated
events. No browser, messaging, workload or external call occurred.

**Change:** Added an in-memory adapter for bounded, indexed submission and
explicit final display/failure/undisplayed events. It feeds the existing NFR-05
preview, retains unresolved submissions as missing, rejects server receipt as
display and rejects duplicates, out-of-order timestamps and extra fields. An
undisplayed terminal cannot precede the five-second deadline; because it is
final, a real observer must wait for its observation window to close. The
evaluation README documents the interface and limits.

**Checks and limits:** Synthetic adapter and preview tests, Mypy, formatting and
whitespace checks passed. This adapter neither captures UI events nor validates
the shared clock; browser driver selection, real two-client integration and all
measurement gates remain open. Result awaits user verification; no NFR pass.

### 2026-11-02 12:24:44 UTC — NFR-05 offline outcome preview

**Direction:** User verified preparing a local chat results checker while Mohit
and Adity handle their assigned inputs. No messages, browser or workload run.

**Change:** Added a bounded JSON preview tool for 60 indexed synthetic outcomes.
It includes failed and undisplayed messages in the denominator, includes the
five-second boundary, flags missing outcomes, rejects duplicate IDs, impossible
times and extra fields, and never claims an NFR pass or clock verification.
The evaluation README documents the strict format and remaining browser, clock,
background-load, privacy and review gates. Failures before submission may have
no submission timestamp; no message content is accepted.

**Checks:** Synthetic threshold, late/failed/undisplayed/missing and invalid
input tests, strict Mypy, Black and whitespace checks passed. Actual two-client
harness, approved profile and real integration remain CN-01 work; result awaits
user verification.

### 2026-11-02 12:20:07 UTC — EXP-02 offline control-flow simulation

**Direction:** User verified extending the local control flow with a fake
session and fake workload. No real session, process, request or experiment.

**Change:** The existing local preparation flow stages and checks inputs before
passing a hard-coded fake session through the handoff helper, clears its mapping,
and produces the previously labeled synthetic metric and report. It exposes a
fixed event sequence and has no launcher or network interface. Focused tests
observe that missing inputs or mismatched parity evidence stop before the fake
session helper; successful synthetic output contains no fake session. Two
synthetic tests, strict Mypy, Black formatting and whitespace checks passed.

**Limit:** This demonstrates local ordering with fixed doubles, not the actual
runner's security, target, deployment, timing, account access or readiness. The
future real runner and its owner-reviewed interfaces remain open. Result awaits
user verification.

### 2026-11-02 12:14:17 UTC — NFR preparation follow-up inventory

**Direction:** User verified an offline review across NFR-01–08. Reviewed the
canonical task procedures, measurement design, existing workload files and
evaluation scripts. This updates the 2026-11-01 inventory, not an NFR result.

**Findings and next work:**

- **NFR-01/02 (SE-01, C):** Dataset-bound case preparation, draft validators and
  synthetic denominator reporting exist. Draft profiles are not approved run
  profiles; final cases, reviewed timing and the real authorized runner remain.
  Browse uses successful requests as its denominator; search counts all issued
  eligible requests, including failures. Mohit is handling actual test cases.
- **NFR-03 (INT-01):** The documented integrated mix includes reads and a
  controlled write; the comparison read workload does not satisfy it. Its
  integrated runner, account/write reconciliation and approved profile remain
  task-owned prerequisites. No substitute workload is authorized here.
- **NFR-04 (SE-01, C):** `search.py` supplies format and Success@5 arithmetic;
  final dataset binding and real ranking retrieval remain SE-01 work. Retained
  records report DATA-READY accepted, but this review did not reverify it or
  establish that the deployed/evaluated ranking path matches those labels.
- **NFR-05 (CN-01, D):** The design calls for two real clients and measures
  submission to recipient display. A dedicated integrated harness, approved
  profile and real messaging/polling checks remain; the read timer is not it.
- **NFR-06/07 (INT-01):** The design calls for dedicated runtime-loss and
  isolated database-restore observers and approved plans. Those are separate
  integration tasks; no cloud or destructive action is authorized here.
- **NFR-08 (INT-01/CLOSE-00):** Comparison cost helpers cover only experiment
  arithmetic. Full-project actual spend, delayed costs, reserve and final budget
  reconciliation remain separate owner work after relevant spending.

**Checks and limits:** Repository/document inventory and whitespace check only;
no tests, workload, provider call or measurement. Exact later implementation
interfaces and human reviews remain with their owning tasks. This review awaits
user verification; no NFR is claimed to have passed.

### 2026-11-02 12:12:20 UTC — EXP-02 synthetic local preparation flow

**Direction:** User assigned actual test cases to Mohit and temporary-account
and related access setup to Adity, then verified a grouped local preparation
flow. No actual case review or account setup is claimed here.

**Change:** A local-only Python helper connects existing checked staging, the
report builder and evidence capture. It has no session, process or network
interface and emits one explicitly labeled fabricated dropped arrival and report.
The integration test checks missing-input refusal before folders are created,
and checks successful synthetic staging/capture without claiming authorization.
Separate stage and capture folders preserve existing exclusive-write behavior;
a stage folder may remain if later capture fails. The guide records the scope.

**Checks and limitations:** The focused synthetic integration check and strict
Mypy passed. Black's multi-file command could not create a sandboxed worker;
in-process Black formatting was used instead. These checks do not prove deployed
parity, real runner behavior, account access, request pairing or timing. No
experiment or NFR pass is claimed. Result awaits user verification.

### 2026-11-02 11:40:31 UTC — EXP-02 remaining runner work review

**Direction and review:** User verified a prioritized offline review. Compared
EXP-02 completion criteria, existing runner design, local preflight and session
handoff with EXP-03/04 dependencies. No code execution, workload or external
service call was needed. The [runner design](comparison-runner-design.md#prioritized-remaining-work)
now orders the remaining work and names responsible owners.

**Outcome:** Actual reviewed Hybrid rankings and a real-target runner are still
missing. Identity/security and affected owners must review the user's temporary
account proposal, session handoff, target and timing protocol before dependent
implementation. B owns downstream Lambda implementation; deployment, parity,
generator capacity and measurement require later gates and authorization.
Offline fixtures and file checks do not prove any of those gates. This review
awaits user verification; no experiment or NFR pass is claimed.

### 2026-11-02 11:38:03 UTC — EXP-02 timeout and incomplete-record checks

**Direction:** User verified checking timeouts and interruptions using synthetic
data. No workload, network request or real interruption was performed.

**Finding and checks:** A fake returned timeout is labeled timeout in both
elapsed and outcome records. A synthetic report containing one timeout and one
issued request without completion records counts the timeout and the unfinished
request separately, marks accounting incomplete and suppresses correct-latency
summary. The two Node test files and ten report tests passed, as did Black and
whitespace checks. This demonstrates handling of missing records, not how k6
behaves when an actual iteration is forcibly interrupted; real-runner and timing
review remain open. Result awaits user verification.

### 2026-11-02 11:35:09 UTC — EXP-02 request timing boundary

**Direction:** User verified moving the local request timing endpoint before
response checking. This is offline preparation, with no workload or external call.

**Change:** The scheduled workload now records the end time when the HTTP call
returns or throws, then classifies and checks the response. Outcome and elapsed
metrics still share the iteration's outcome. A Node test substitutes fake k6 APIs
and checks that a deliberately slow correctness check is excluded, thrown calls
are accounted for, and backward clock readings are flagged. The input guide was
updated. The real runner, individual-record verification and owner-reviewed timing
protocol remain open; Date.now is not a verified monotonic clock.

**Checks:** The fake-k6 Node tests and 53 synthetic report/preflight tests passed;
whitespace checks passed. Result awaits user verification.

### 2026-11-02 11:30:12 UTC — EXP-02 request and timing record review

**Direction and scope:** User verified an offline review of how outcomes and
timings are connected, with a synthetic check and no experiment or external call.

**Finding:** The local workload writes the outcome label on its elapsed sample
and then emits an outcome counter in the same iteration. The case index repeats,
and the records carry no unique request identifier for independent matching.
The timer also includes response parsing and correctness checks; it is not a
verified request-only boundary. Interrupted iterations and real-runner behavior
remain unverified. The existing timing-protocol review remains open.

**Check:** A synthetic test demonstrates that matching aggregate totals can
coexist with unverified individual pairing. All nine report tests, Black and
whitespace checks passed. The input guide records the finding. No real results
or NFR acceptance are claimed; this review awaits user verification.

### 2026-11-02 11:22:32 UTC — EXP-02 report outcome and route checks

**Direction:** User verified checking outcome labels and route tags in the local
report. Synthetic metric points only; no workload, real session, cloud, database
or external action occurred.

**Finding and change:** The report previously compared only total outcome and
latency counts; equal totals with different outcome labels could appear complete.
It now compares counts by outcome overall and by route, verifies route-level
issued/HTTP/outcome/latency totals, marks mismatches incomplete, and suppresses
affected correct-latency summaries. For selected-condition reports, tracked
request metrics without route tags fail; dropped arrivals are exempt because no
request was assigned. The report explicitly marks individual-request binding
unverified. Tests exercise matching data, swapped outcome labels, cross-route
mismatches, missing route tags and dropped-arrival handling.

**Checks and limits:** 53 synthetic report, evidence and cost tests and the
cross-component test passed; strict Mypy, in-process Black formatting and
whitespace checks passed. Aggregate label consistency does not prove that each
individual request was paired with its own latency. Timing protocol, actual
runner, account, deployment and owner review gates remain open; no results or
NFR acceptance are claimed. Result awaits user verification.


### 2026-11-02 11:19:10 UTC — EXP-02 offline component integration check

**Direction:** User verified a grouped local end-to-end preparation check.
Synthetic inputs and fabricated metric points only; no real session, k6 workload,
request, cloud, database or external service was used.

**Change and checks:** Added one focused synthetic integration test that builds
bound cases/plan, supplies declared parity evidence, confirms changed evidence
prevents staging, stages the planned run, checks the fake session handoff,
creates an incomplete synthetic report with a dropped arrival and captures
separate raw/report files. It verifies both output hashes and confirms the fake
session is absent from those artifacts. The report remains unaccepted and its
synthetic delivery is marked incomplete. The new test and 36 focused session,
report and capture tests passed; strict Mypy, in-process Black formatting and
whitespace checks passed. The guide and README describe scope and limitations.

**Limits:** The test calls helpers directly and does not exercise a real runner,
real sessions, actual parity observations, generator capacity or timing. The
synthetic metric points are fixtures, not performance results. Human review,
real-target integration, deployment and other run gates remain open. Result
awaits user verification.


### 2026-11-02 11:13:27 UTC — EXP-02 parity-gated staging

**Direction:** User verified connecting declared A/B parity and local evidence
checks to staging. Inputs and files were synthetic; no session, workload, cloud,
database, deployed API or external service was used.

**Change:** The stager now requires a pair-parity record and evidence root. It
reuses the full parity check and existing safe local file hashing, requires both
evidence hashes to match, and requires the record's cycle and condition to
match the selected planned run before making a staging folder. The staging
record includes the supplied parity-record hash and explicitly marks deployed
parity unverified. The CLI requires both new inputs. Tests cover missing and
altered evidence, missing record, wrong pair, valid staging and CLI use. The
guide and README describe the required inputs and remaining gates.

**Checks and limits:** 82 focused synthetic staging, parity and artifact tests,
strict Mypy, Black formatting and whitespace checks passed. File hashes and
matching declarations do not prove source, content, review, observation freshness
or actual deployed parity. The stager does not obtain a session, run k6, enforce
real target authorization or approve measurement. Real runner integration and
owner/deployment gates remain open. Result awaits user verification.


### 2026-11-02 11:06:55 UTC — EXP-02 per-condition workload correction

**Direction:** User verified fixing the mismatch between one-condition planned
runs and the script that scheduled all three conditions in every invocation.
Only synthetic inputs and `k6 inspect` were used; no workload, request, session,
cloud, database or external-service call was made.

**Finding and change:** The paired plan contains 18 run IDs, each for one
condition, but the workload previously constructed all six warm-up/measurement
scenarios in each invocation. Connecting those as-is could schedule three times
as many condition workloads. `comparison_schedule.js` now requires one selected
condition and returns exactly its warm-up and measurement scenarios; the load
script obtains it from `CLIP_COMPARISON_LOCAL_CONDITION`. Low and normal measured
arrivals start after the warm-up drain; burst begins its higher rate immediately.
Rates, mix, 60-second warm-up, 300-second measurement, five-second drain and
zero retries remain unchanged. The staging record derives the condition from the
planned run ID. The report CLI now requires a condition and rejects tracked
metrics with missing, conflicting or other-condition tags; it does not require
unrun conditions to have arrivals. Synthetic report and staging tests were
updated. Historical all-condition in-process report use remains available for
previous synthetic previews, not the per-run CLI.

**Checks:** 96 focused Python tests passed, plus a staging-specific rerun; four
Node test files passed, as did strict Mypy for the changed Python helpers,
in-process Black formatting and whitespace checks. k6
v2.3.0 `inspect` confirmed exactly two scenarios for each of low, normal and
burst and refusal when the condition is missing. An initial inspect assertion
expected `60s`/`65s`; k6 renders the same durations as `1m0s`/`1m5s`, so the
test was corrected and passed. Node was v26.8.2; project-pinned Node 24 remains
a separate check. No `k6 run` occurred.

**Limits:** Local staging and condition selection do not yet prove a future
real runner passes the staged condition or executes those bytes. The account,
timing, reviewed references, module-hash approval, deployed parity, telemetry,
run approval and owner review gates remain open. This change does not establish
measurement or NFR acceptance. Result awaits user verification.


### 2026-11-02 10:49:59 UTC — EXP-02 staged run files

**Direction:** User verified grouping local run-file staging and checks. Only
synthetic inputs and local files were used; no session, workload, cloud, database
or provider call occurred.

**Change:** Added a staging helper and blank six-module hash template. It reads
the preflight inputs once, reuses full corpus/reference/plan/profile validation,
checks the selected run, checks the exact main script and schedule against the
pair plan and all six fixed JavaScript files against a supplied hash map. It
creates a new private run directory only after validation, copies the profile,
schedule and modules, reads them back, and records file hashes separately. It
refuses missing/mismatched files and existing run folders; it does not run k6.
Synthetic tests cover missing or blank hashes, missing/changed modules, changed
schedule/profile, exclusive creation and sanitized CLI output.

**Checks and limits:** 87 synthetic staging, preflight, pair-plan and capture
tests passed, followed by a focused staging rerun after adding changed-file and
wrong-run checks. Strict Mypy, Black formatting and whitespace checks passed. The current
plan binds the main script and schedule, not the other five module hashes; the
supplied map requires independent review. The helper does not prove later file
integrity, actual runner use, dependency closure, k6 provenance or approval.
Current workload is still loopback-only and the real runner, owner review and
other deployment/run gates remain open. Result awaits user verification.


### 2026-11-02 10:41:42 UTC — EXP-02 parity evidence hash check

**Direction:** User verified checking referenced parity evidence files locally.
No cloud, database, provider, deployed API or workload was contacted.

**Change:** The declared-parity checker now optionally accepts an evidence root
and reuses the existing bounded, no-symlink artifact verifier for both supplied
references. It refuses missing files, unsafe paths and hash mismatches and only
reports aggregate flags. Omitting the root leaves both evidence-check flags
false. Synthetic tests exercise matching files, a modified file, missing file,
symlink, traversal and CLI behavior. The guide and README describe usage.

**Checks and limits:** 14 focused synthetic parity and artifact tests, strict Mypy,
in-process Black formatting and whitespace checks passed. Hash matching proves
only that supplied local bytes match declared hashes; it does not verify file
contents or provenance, deployed observations, timestamp freshness, human review,
or actual A/B parity. No real evidence or measurement is claimed. Result awaits
user verification.


### 2026-11-02 10:36:32 UTC — EXP-02 declared A/B parity preparation

**Direction:** User verified grouped offline parity preparation. Only synthetic
inputs were used; no cloud, database, deployed API or provider was contacted.

**Change:** Added a blank, non-authorizing pair-declaration template and an
offline checker. The checker reuses complete corpus/reference and pair-plan
validation, checks selected cycle/condition and run IDs, and compares both
supplied dataset fingerprint, schema, index fingerprint, DB-settings hash and
search contract, implementation and model revisions to the plan/reference. It
requires an observation time and safe evidence reference/hash for each side and
reports aggregate flags only. Tests cover incomplete templates, mismatches and
malformed references. Guide and README document the input format and limits.

**Checks and limits:** 65 focused synthetic tests, plus the new CLI check on a
focused rerun, strict Mypy, Black formatting and whitespace checks passed.
This compares declarations; it does not open evidence,
verify hashes, authenticate provenance, check freshness, observe deployments or
verify human review. Actual A/B dataset, index, DB settings, schema and model
parity must still be demonstrated before measurement. No run is authorized and
no DATA-READY or review claim is added. Result awaits user verification.


### 2026-11-02 10:32:45 UTC — EXP-02 capture privacy and read-back checks

**Direction:** User verified grouped preparation for privacy checks and saved-file
verification. All inputs were synthetic; no experiment, session, cloud, database
or external action occurred.

**Change:** The local capture helper parses raw JSONL and report JSON before
creating a run folder. It rejects malformed JSON, nonfinite values, known
sensitive field names and recognizable sensitive-value patterns, with sanitized
errors. It reads the written raw file, report and fingerprint record back through
no-follow descriptors and compares exact hashes before returning. Failures retain
partial files and do not authorize a run. The guide and README explain this
limited check and its input requirements.

**Checks and limits:** 38 synthetic capture, artifact and manifest tests, strict
Mypy, in-process Black formatting and whitespace checks passed. Fixtures include
escaped sensitive keys, cookies, bodies, embeddings, unsafe report fields,
synthetic k6 points/report compatibility and simulated corruption. Pattern checks cannot recognize every secret or private
value; independent privacy review remains necessary. A successful read-back does
not prevent later edits or establish provenance, review or run validity. No real
runner integration or real evidence is claimed. Result awaits user verification.


### 2026-11-02 10:29:13 UTC — EXP-02 local evidence capture preparation

**Direction:** User continued the proposed grouped capture step. Only synthetic
local bytes were used; no experiment, session, cloud, database or external action
occurred.

**Change:** Added an offline helper that validates bounded input sizes and safe
run IDs, creates a new private run directory exclusively, writes raw and derived
report bytes as distinct files, and writes a separate SHA-256 reference record
last. Existing run directories are refused. Interrupted writes retain partial
files without a successful return; a missing or partial fingerprint record is not
accepted as completed evidence. Existing artifact hash tooling can check the
recorded references. Synthetic tests cover hashes, distinct output, duplicate
runs, invalid IDs, symlinked roots and a simulated write failure. The guide and
README explain use and limitations.

**Checks and limits:** 25 focused synthetic capture, artifact and manifest tests,
strict Mypy, Black formatting and whitespace checks passed. The helper does not
inspect its supplied bytes for private data, validate source or run status, or
make files physically immutable. A future reviewed runner must enforce privacy,
protect raw files and validate fingerprints; this helper is not wired to it and
has not captured real results. Result awaits user verification.


### 2026-11-02 10:22:40 UTC — EXP-02 grouped mock session handoff

**Direction:** User verified integrating fake session handoff with the actual
offline preflight and asked to group related work. No real session, credentials,
network request, cloud action or workload was used.

**Change:** The mock runner now invokes local preparation before reading its
caller-supplied session mapping, invokes the environment handoff helper only on
success, accepts only a fixed fake session for simulation, and clears the
in-memory handoff mapping. Missing, malformed or non-fixture sessions stop before
the simulated workload marker; returned events never include the session. Added
synthetic tests for correct order, inaccessible session before preflight, wrong
session, changed profile and no session disclosure; updated the guide and README.

**Checks and limits:** 47 synthetic session and preflight tests passed on rerun,
plus strict Mypy, Black formatting and whitespace checks. One initial assertion
failed because its fake value was the word `invalid`, also present in a normal
status key; a unique fake value corrected the test. This is still an in-memory
simulation, not a real runner or a security review. The real-target path,
account-class decision, environment isolation, session lifetime, owner approval,
timing, capacity and deployment/parity remain open. No measurement authorized.
Result awaits user verification.


### 2026-11-02 10:07:16 UTC — EXP-02 session environment handoff preparation

**Direction:** User chose an environment variable for the future test session
and verified preparing the handoff with fake values. User suggested a temporary
account, which remains a proposed change to the approved regular-account plan
and needs Identity and experiment owner review. No real session, credentials,
request, k6 workload, cloud, database or external service was used.

**Change:** Added an in-memory handoff helper with proposed variable
`CLIP_COMPARISON_SESSION_COOKIE` for the complete host-session cookie header.
It refuses to read its input mapping until supplied local preflight status is
true, validates bounded cookie shape, copies only that variable, and gives
sanitized error messages. It does not read the process environment, launch a
child, contact a service or authorize a run. Tests use fake values and verify
that a failed preflight cannot read the session and malformed values are not
included in exceptions. Updated preparation guide, runner draft and README.

**Checks and limits:** 47 focused synthetic tests, strict Mypy, in-process Black
formatting and whitespace checks passed. The helper trusts the status provided
by its caller: a future runner must call preflight itself and enforce all other
gates. It cannot validate session expiry, account type or target. Environment
visibility, process isolation, secure transfer and cleanup need security/owner
review before real use; the existing workload does not read this variable.
Result awaits user verification.


### 2026-11-02 09:56:27 UTC — EXP-02 real-runner design review

**Direction:** User verified reviewing authentication, runner and evidence
contracts and documenting unresolved decisions. No credentials, live requests,
workload, database, cloud or provider action occurred.

**Evidence and output:** Reviewed the approved comparison plan, local smoke
runner, scheduled workload, Identity HTTP composition and evidence verifier.
The local runner uses the isolated inspection login and loopback cookie; neither
is an approved real test access path. The product Identity code exposes regular
Microsoft exchange and separate temporary-account sessions; the plan calls for
an authorized regular synthetic account. The scheduled workload remains
loopback-only and uses unverified `Date.now` timing. Added
[runner design](comparison-runner-design.md) with a proposed preflight, approval,
session, checked-byte, capture and failure sequence, plus explicit owner inputs.
The design does not select an authentication handoff, authorize a run, verify
actual synthetic account access or change an approved protocol.

**Checks and limitations:** Reviewed source and documentation and ran
`git diff --check`; no executable code or frozen artifacts changed. Asked the
user about the synthetic regular-account session and any existing secure handoff.
Target authorization, profile-to-execution binding, safe evidence capture,
timing, capacity and owner review remain open. This is a design draft, not an
implemented real runner. Result awaits user verification.


### 2026-11-02 09:53:25 UTC — EXP-02 mock runner ordering

**Direction:** User verified the offline preparation stage and the grouped mock
runner step. Only deterministic synthetic files were used. No session, k6
workload, request, cloud, database or provider call occurred.

**Change:** Added a simulation that calls the existing local preflight first.
Missing or mismatched inputs yield a refusal event before any simulated session
or workload events. Passing synthetic inputs produce fixed in-memory event
labels in that order. The simulation accepts no target, credential callback,
real transport or workload callback; it never authorizes a measurement. Added
local tests for missing inputs, matching synthetic inputs and altered profile
bytes; updated the guide and k6 README with the exact scope and limits.

**Checks:** 64 focused preflight and paired-plan tests, strict Mypy, in-process
Black formatting and whitespace checks passed. The worktree has no measurement
results. This simulation demonstrates only its own ordering: it is not the real
runner, does not establish that other gates are satisfied, and cannot prove
future runner safety. Real runner implementation, reviewed references, timing,
capacity, deployment/parity, authorization and owner reviews remain open.
Result awaits user verification.


### 2026-11-02 09:43:48 UTC — EXP-02 offline runner preparation

**Direction:** User verified grouped offline runner preparation and asked to
complete EXP-02 as efficiently as its remaining gates allow. No credentials,
workload, cloud, database or external-service call was made.

**Change:** Added a non-executing local preparation stage for one planned run.
It lists missing and individually unreadable/invalid inputs without echoing
content, reuses the existing full corpus/reference/plan/profile preflight,
checks exact profile bytes against the supplied hash, and confirms the selected
run ID belongs to the selected cycle. Inputs are bounded local regular files;
the final path component cannot be a symlink. It always reports that measurement
is unauthorized and lists remaining gates. The tool does not invoke k6, obtain
a session, accept a target or send requests. Guide and README describe inputs,
exit codes and limits.

**Checks:** 74 focused synthetic preflight, binding and pair-plan tests, strict
Mypy, in-process Black formatting and whitespace checks passed. Tests exercise
missing files, mismatched profiles, incorrect planned run,
non-followed final symlinks and sanitized CLI output. No actual experiment
reference or accepted real-run input is claimed.

**Limits:** Hash matching does not establish review or protect files after the
check. Run identity is a declared plan match, not deployed routing. Owner review,
actual reference and seed, capacity, timing, authentication, real runner,
deployed parity, approval, telemetry, costs and cleanup remain open. This stage
cannot authorize a run; result awaits user verification.


### 2026-11-02 09:30:00 UTC — EXP-02 three-run cost median

**Direction:** User verified the cost binding check and the next offline
three-run median step. Synthetic inputs only; no experiment or external call.

**Change:** Added a local Python preview that reuses the cost binding and
per-run calculation for three captured manifest/report/input sets. It requires
a common configuration and condition, unique run IDs and repetitions 1–3,
and a defined unit cost for each. It reports each value and their median;
normal is identified as a candidate score input, not an accepted score. It
creates a new output file and never overwrites an existing one. Guide and README
explain inputs and remaining checks.

**Checks:** 28 focused cost, manifest and artifact tests passed, strict Mypy,
in-process Black verification and `git diff --check` passed. An initial test
failed because its synthetic fixture attempted to modify a tuple; it was fixed
and the focused suite passed on rerun.

**Limits:** Matching metadata and report hashes do not verify actual cost
allocation, common price basis, provenance, run validity or eligibility. No
weighted score, final comparison, budget or NFR acceptance is claimed. Owner
review and real evidence remain open. Result awaits user verification.


### 2026-11-02 09:14:13 UTC — EXP-02 cost input binding

**Direction:** User verified offline cost arithmetic and the next matching step.
Only local synthetic files were used; no request, workload, billing, database or
external service was contacted.

**Change:** Added an offline checker for the cost input, captured run manifest,
and derived comparison report. It validates the captured manifest, matches run
ID and condition, hashes the supplied report bytes against the manifest and
compares the declared correct count with the selected measured cohort. Existing
reports have no run ID; their recorded digest supplies the association. It fails
on missing or mismatched inputs and prints only aggregate flags. Added local
synthetic tests for valid and mismatched inputs and CLI refusal.

**Checks:** 27 cost, manifest and artifact tests passed, strict Mypy on the new
checker, in-process Black formatting and `git diff --check` passed. The guide
and k6 README record the command and limitations.

**Limits:** Matching hashes do not establish report provenance or correctness.
The cost interval in the manifest may cover the whole run, so this check cannot
prove the supplied amount is allocated to the measured interval or that all
shared costs were included. It does not accept a run, measurement or NFR. Human
review of cost allocation, report accuracy, timing and other run gates remains.
The result awaits user verification.


### 2026-11-02 09:08:29 UTC — EXP-02 offline cost arithmetic

**Direction:** User verified preparing a local cost calculator and asked to set
the custom timer aside. This step uses only synthetic fixtures and local files;
no experiment, provider, billing, database or external call was made.

**Design and change:** EXP-01 calls for each measured low, normal or burst
interval's pre-credit whole-system cost divided by its correct operations,
multiplied by 1,000; normal-run values contribute to the score after review.
No existing cost calculator was found. Added a bounded local Python calculator
that accepts one declared run, decimal USD amount, estimated/billing label and
correct count, and writes a separate new report. It reports an unavailable unit
cost for zero correct operations and refuses invalid inputs or existing outputs.
The guide defines its exact input format and records the requirement for a common
allocation and price basis, retained ECS and shared services, and cost evidence.

**Checks:** 25 synthetic calculator, manifest and artifact tests passed; strict
Mypy, in-process Black formatting and `git diff --check` passed. No run results
or actual prices were generated.

**Limits and next action:** The calculator cannot verify cost attribution,
source authenticity, allocation completeness, correctness counts, billing delay,
run validity or budget; `billing` is a supplied label. It does not calculate
whole-experiment cost, select a price model, score A/B or approve an NFR. Real
cost sources, reviewed allocation, owner review and run evidence remain open.
This step awaits user verification.


### 2026-11-02 09:03:54 UTC — EXP-02 timer prototype recheck

**Direction:** User asked to check the custom timer. This was an offline check;
no workload, request, cloud or external-service call was made.

**Evidence:** With public-module downloads and checksum lookups disabled,
`GOPROXY=off GOSUMDB=off GOPATH=/tmp/clip-timer-gopath
GOCACHE=/tmp/clip-timer-gocache go test ./...` passed from the monotonic module
(the result was cached). The existing temporary custom binary ran `k6 inspect`
on `monotonic/inspect_bridge.js` and printed `clock_bridge_check_passed` during
initialization. This checks import, nonnegative elapsed output and invalid call
ordering. The inspection script throws if executed as a workload. Inspection of
`comparison_load.js` confirms that it still uses `Date.now` and does not import
the extension.

**Limits:** These checks do not establish elapsed-time accuracy around an HTTP
request, concurrent VU operation in the k6 runtime, timeout or exception
coverage, reproducible binary provenance, or integration with report accounting.
The timing decision and applicable owner review remain open. The custom prototype
is not ready to support experiment results.


### 2026-11-02 09:00:13 UTC — EXP-02 timing guidance correction

**Direction:** User verified the profile preflight step and asked to align
current timing guidance with the simpler built-in k6 approach. No measurement,
credentials, workload or external action was performed.

**Correction:** The user's preference is to use k6 phase metrics without
requiring a custom Go extension. The preparation guide now states that preference
and identifies the remaining review. The approved comparison design still
requires a verified monotonic clock; this documentation change does not amend
that design or record affected-owner approval. The built-in phase proposal uses
per-response blocked plus duration for successful, independently correct
responses, with separate failure accounting and phase diagnostics. It has clock
and failed-connection limitations; the preview is not a run-ready implementation.
NFR-01 and NFR-02 require their own reviewed timing decisions, and NFR-05 has a
different sender-to-display boundary. Historical entries remain unchanged.

**Checks and next action:** Reviewed the existing approved design, timing
proposal and current guidance; `git diff --check` passed. Affected owners must
review the protocol revision and the actual generator timing procedure before
measurement. Result awaits user verification.


### 2026-11-02 08:48:38 UTC — EXP-02 profile preflight checks

**Direction and scope:** User verified the previous generated-profile evidence
binding and the next offline preflight step. No real workload, credentials,
cloud or external service was used. The earlier proposed 300-request ceiling
remains non-binding.

**Change:** The combined input checker requires the profile's exact shape,
five-second timeout, and positive JavaScript-representable integer worker
settings with pre-allocation no greater than the maximum. It checks selected
cycle starts and cases as before. When profile bytes and a lowercase SHA-256 are
supplied, it compares the exact bytes and confirms they decode to the checked
profile. Its CLI requires profile, cycle and expected hash together; it reports
whether a hash was checked. The builder reuses the same capacity validation;
its internal pre-output check cannot check a file hash. Synthetic tests include
301 as a format example, not an operational recommendation.

**Checks:** 125 comparison-focused synthetic/local tests passed, plus a fresh
focused preflight test run after test cleanup, strict Mypy, in-process Black
formatting and `git diff --check`. Black's normal multi-file CLI could not start
its sandboxed worker process; in-process formatting and verification succeeded.

**Limits and next action:** A matching caller-supplied hash proves consistency,
not review, approved capacity, actual runner use, or protection from later file
changes. The real runner must enforce both checks before credentials. Actual
seed, capacity, reviewed ordered reference, timing and other real-run gates
remain open, including shared command-registry coordination. This is not a
measurement or run authorization; result awaits user verification.


### 2026-11-02 08:37:36 UTC — EXP-02 generated-profile evidence binding

**Direction:** User verified recording each generated profile's file reference
and hash, checking local file bytes, and comparing A/B records per cycle. This
is offline preparation; no credentials, workload or external action was allowed.

**Change:** The editable run-manifest template is now schema version 3, with
separate `execution_profile_reference` and `execution_profile_sha256` fields;
the existing `profile_sha256` still identifies the checked-in schedule. The
manifest validator requires these fields and a valid hash in completed records.
The artifact verifier hashes the referenced local profile with its existing
bounded, no-symlink evidence checks. The paired-plan checker requires all six
captured records within each cycle to declare the same profile hash; different
cycles may have different hashes. The guides describe the format and limits.
Older run-manifest shapes are rejected; no frozen or actual record was edited.

**Limits:** Matching recorded hashes prove only that supplied local bytes match
the records and that records agree. They do not establish profile approval,
content validity, deployed identity, or that a future runner used those bytes.
The runner must enforce all reviewed inputs before credentials and requests.
The actual seed, worker limits, reviewed ordered results, timing protocol and
other real-measurement gates remain pending. Shared command-registry coordination
also remains pending under the no-external-calls scope.

**Checks:** One hundred fifteen focused rotation, manifest, paired-plan,
preflight, artifact, telemetry, binding and ordered-reference tests passed with
warnings as errors. Synthetic tests cover matching and mismatched cycle hashes,
different hashes across cycles, missing/modified/symlinked/traversal profile
files, missing fields and malformed hashes. Strict Mypy, Black in-process
formatting and `git diff --check` passed. No k6 run, performance test, cloud,
database, credential or external-service call occurred. Result awaits user
verification.

### 2026-11-02 07:18:42 UTC — EXP-02 cycle profile preparation

**Direction:** User verified preparing deterministic workload profiles from
the bound case corpus and paired plan, with explicit worker values and one new
output file per cycle. Preparation remains offline; actual seed and worker
limits are not selected or approved by this step.

**Change:** Added `comparison_profile_builder.py`. For a selected cycle it
checks the complete plan, source/data/corpus and ordered-reference binding,
derives the three planned case starts, uses supplied per-scenario worker values
and the approved five-second timeout, and reuses the profile preflight before
exclusively creating a new file. It prints only the cycle, file hash and
non-authorization status. Repeated identical inputs produce identical bytes;
the same cycle profile can be used for A and B. The builder never opens a
session or sends a request. The preparation guide and k6 README explain usage.

**Correctness repair:** The existing corpus binder compared Python objects,
where `True == 1`. It now compares type-sensitive canonical JSON, so a boolean
cannot replace a numeric expected field even when the supplied hash is updated.
The focused regression test exercises that case.

**Limits and follow-up:** Positive JavaScript-representable worker counts are
only shape checks, not approved or safe generator limits; burst scenarios may
overlap. No 300-request cap is encoded. The run manifest currently records the
checked-in schedule hash rather than the generated profile's hash, so recording
and binding the exact generated profile remains a pre-measurement evidence gap.
Real reviewed ordered references, the actual seed and worker settings, owner
review, target/auth/timing gates and future runner enforcement remain pending.
Both new offline commands await coordinated shared command-registry registration;
current remote-work inspection is outside the no-external-calls scope.

**Checks:** One hundred twelve focused Python tests passed with warnings as
errors, including deterministic generation, all three cycle mappings,
incomplete/mismatched inputs, invalid capacities, existing file and symlink
refusal, and type-sensitive case comparison. Strict Mypy, Black in-process
formatting and `git diff --check` passed. Initialization-only `k6 inspect`
accepted all three generated synthetic profiles. No k6 run, performance test,
cloud, database, credential or external-service call occurred. Result awaits
user verification.

### 2026-11-02 07:11:21 UTC — EXP-02 approved seeded rotation

**Direction:** User approved generating the nine pair starts from a supplied
integer seed 0–9, advancing one place per pair and wrapping after 9. Both A and
B use the same start within a pair. The actual experiment seed remains blank.

**Change:** Added the offline `comparison_rotation.py` generator and shared
rule `increment-one-per-pair-v1`. The editable paired-plan and run-manifest
templates now record the rule and an unfilled rotation seed, separately from
the dataset seed; their schema versions are 2 because their shapes changed.
The paired-plan validator checks every pair start against its seed and checks
captured seeds against the plan. The per-run manifest validator checks the seed,
rule and start against that run's cycle and condition. Version-1 record shapes
are rejected. The synthetic fixture tests and preparation/k6 guides were
updated. No frozen dataset or acceptance record was edited.

**Checks:** One hundred focused rotation, plan, manifest, preflight, artifact,
telemetry, binding and ordered-reference tests passed with warnings as errors.
They cover the seed-3 wrap, invalid seeds/rules/starts, mismatched captured
seeds and version-1 refusal. Strict Mypy, Black in-process formatting and
`git diff --check` passed. The generator printed the expected nine starts for
synthetic seed 3; both blank version-2 templates validated without authorizing
a measurement. No workload, cloud, database, credential or external-service
call occurred.

**Remaining:** The actual seed must be selected and reviewed in the future run
plan. The new offline command is documented in the EXP-02 preparation and k6
guides; registration in the shared command registry awaits its coordinated
writer reservation and current remote-work inspection, which this no-external-
calls preparation scope does not permit. Owner review, future runner enforcement
and all real measurement gates remain open. Result awaits user verification.

### 2026-11-02 07:05:05 UTC — EXP-02 per-condition case rotations

**Direction:** User verified correcting the mismatch between the paired plan,
which may give each traffic condition a different case start, and the local k6
workload, which previously accepted only one start for all three. Work is offline
preparation only; the seed and the rule for choosing starts remain open.

**Change:** `comparison_schedule.js` validates exactly three integer indices
in a profile's `sequence_starts` object and selects the relevant index for each
condition's warm-up and measured scenarios. `comparison_load.js` uses that
index when selecting and tagging the case. The combined Python preflight can
optionally take `--workload-profile` and `--cycle` together, check the profile's
cases against the bound corpus and compare all three indices to that cycle's
paired plan. Its output explicitly says whether that profile was checked. A
single legacy `sequence_start` no longer initializes the local workload. The
preparation guide and k6 README document the profile shape and options.

**Limits:** This does not choose a seed or prove that a deployment used the
profile. The profile check does not verify capacity, target, timing, credentials
or authorization and remains optional in this offline tool; the future
real-target runner must enforce it along with all other gates before a session
or request. No cap or approved rate changed. Synthetic case orders are fixtures,
not independently reviewed results.

**Checks:** Forty-three focused Python tests, four Node test files under the
available Node 26.8.2, strict Mypy, Black in-process formatting verification and
`git diff --check` passed. Node 24 remains the project-pinned toolchain check.
An initialization-only `k6 inspect` accepted a synthetic complete profile and
rejected an incomplete start map. No k6 run, performance test, cloud, database,
credential or external-service call occurred. Result awaits user verification.

### 2026-11-02 06:53:29 UTC — EXP-02 recorded run-order check

**Direction:** User verified adding a check of completed manifests' recorded
start/end times against the approved configuration and traffic order. This is
offline preparation; no workload, credentials, cloud or external action was
authorized or performed.

**Finding and change:** The prior paired-plan validator checked the declared
plan and each manifest's labels, but not the order of recorded times; its
synthetic fixtures even gave all runs the same times. The validator now derives
the approved configuration-first sequence: low, normal, burst for each
configuration, with A/B, B/A, A/B across the three cycles. After validating all
18 captures, it rejects recorded intervals that are reversed or overlap; an
interval may start exactly when its predecessor ends. Input file order is not
significant. The guide states the check and its limits.

**Limits:** This compares supplied UTC values; it does not prove their clocks
were accurate or comparable, confirm which runtime served requests, validate
raw evidence, or authorize a measurement. No actual run or manifest was created.
Historical synthetic tests did not establish recorded chronological order.

**Checks:** Thirty-four focused paired-plan, binding and combined-preflight
tests passed with warnings as errors. Synthetic cases covered the approved
sequence, reversed configuration order in each cycle, reversed condition order,
overlap, touching boundaries and shuffled input files. Strict Mypy, Black
in-process formatting verification and `git diff --check` passed. Result awaits
user verification.

### 2026-11-01 21:32:23 UTC — EXP-02 combined pre-request input preflight

**Direction:** User verified one offline gate that composes the existing
ordered-reference/corpus binding and paired-plan checks. Preparation only; no
session, request, experiment, cloud, database or provider call was authorized.

**Change:** Added `comparison_run_preflight.py`. It reuses the binding checker
to rebuild the complete corpus from the frozen archive and supplied ordered
reference, then reuses the paired-plan checker to require a complete 9-pair/18
run plan. It rejects plans whose dataset fingerprint or exact corpus file hash
differs between the two inputs. The CLI accepts four bounded local JSON files
and prints aggregate status only. The preparation guide and k6 README document
the command and its future runner boundary.

**Limits:** The gate is offline and always reports `measurement_authorized: false`.
It does not verify human review, deployed identity, target/auth, timing, caps or
database equivalence. It is not yet wired into a real-target runner; that runner
must enforce it and all other reviewed gates before credentials or requests.
Synthetic ordered results and run IDs are test fixtures only. No concurrency
ceiling is encoded.

**Checks:** Twenty-eight focused binding, paired-plan and composite-gate tests
passed with warnings as errors, including aligned bindings, dataset/corpus
mismatch, blank plan refusal, aggregate-only CLI output and sanitized failure.
Strict Mypy, Black in-process formatting verification and `git diff --check`
passed. Result awaits user verification.

### 2026-11-01 21:27:51 UTC — EXP-02 paired captured-manifest cross-check

**Direction:** User verified extending the paired-plan checker to compare all
completed run manifests with the plan. Work remains offline preparation only.

**Change:** `comparison_pair_plan.py` now optionally accepts all 18 captured
manifests. It validates each with the existing manifest validator, then matches
run ID, configuration, condition, repetition/cycle, sequence start and the
planned dataset/index/database and workload fingerprints and generator version.
It rejects missing, duplicate, unexpected, template or mismatched captures. The
CLI still prints only aggregate check status and never authorizes a run. The
preparation guide documents the later check.

**Limits:** The checker verifies recorded values only. It does not prove that
the deployed service used those values, inspect raw outputs, validate artifact
hashes, or approve a measurement. Synthetic captures are test fixtures, not
experiment evidence. The 300-request proposal remains non-binding.

**Checks:** Thirteen focused tests passed with warnings as errors, covering
valid synthetic captures and mismatched fields/sets. Strict Mypy and Black
formatting verification passed. No k6 workload, experiment, cloud, database or
external service call occurred. Result awaits user verification.

### 2026-11-01 21:15:42 UTC — EXP-02 offline paired-run plan

**Direction:** User verified preparation of a checker for the approved
three-cycle comparison order. The 300 concurrent-request proposal remains
non-binding and was excluded from the checker.

**Change:** Added `comparison_pair_plan.py` and a blank paired-plan template.
The checker validates A/B, B/A, A/B cycle order; low/normal/burst condition
order; nine matched pairs; eighteen unique planned run IDs; shared dataset,
database and workload fingerprints; and a supplied case sequence start for each
pair. The pair has one shared sequence-start field, so A and B cannot silently
use different case rotations. It accepts no target or credentials and always
reports `measurement_authorized: false`.

**Limits:** It validates declared plan shape and bindings only. It does not
compare actual captured run manifests, prove that a deployment used these
inputs, select the case rotation, establish generator capacity, or authorize
execution. The actual generator/client concurrency cap remains open.

**Checks:** Eight synthetic tests passed with warnings as errors. Strict Mypy
passed for the checker and its tests; Black in-process formatting verification
passed. No k6 workload, experiment, cloud, database or external service call
occurred. Result awaits user verification.

### 2026-11-01 21:08:01 UTC — concurrency proposal clarified

**Direction:** User clarified that the experiment design's proposed limit of
300 concurrent client requests is not binding. It is not a PRD requirement and
must not be treated as a settled cap or enforced in code.

**Record:** Marked that figure non-binding in the experiment design. The actual
generator/client concurrency cap remains an open pre-run input and must be
resolved in the reviewed run plan. The burst's overlapping k6 scenarios remain
a capacity consideration, but do not establish a numerical cap by themselves.

**Limits:** No replacement cap was selected. No code guard, workload, cloud
action or measurement was performed. EXP-02 still requires current generator
capacity, rate delivery and saturation evidence before any run.

### 2026-11-01 20:57:31 UTC — EXP-02 raw and derived evidence checks

**Direction:** User verified the offline raw-output and report verification
step. The work remains preparation only; no run or external action was allowed.

**Change:** Extended `comparison_artifacts.py` to hash the captured manifest's
raw k6 output and derived report alongside the four telemetry artifacts and
cost source. It rejects a digest mismatch and rejects raw/report references
that are different paths to the same underlying file. The checker reads the
artifacts without modifying them or printing their paths or contents. Updated
the preparation guide to describe its seven-file coverage and limits.

**Limits:** A matching hash proves only equality with the digest written in the
manifest. It cannot prove that bytes remained unchanged before that digest was
recorded, that evidence is authentic or complete, or that its contents are safe.
No actual run outputs exist; all validation uses synthetic local files.

**Checks:** Eight focused tests passed with warnings treated as errors,
including unchanged-file checks, raw/report mismatches, and hard-link
distinctness refusal. Black formatting verification passed through Black's
in-process formatter (the normal command could not spawn its worker in this
restricted environment); strict Mypy passed for the verifier module. No k6
workload, experiment, cloud, database or external service call occurred.
Result awaits user verification.

### 2026-11-01 20:52:28 UTC — EXP-02 offline evidence artifact checks

**Direction:** User verified grouped offline telemetry and cost file checks.
No run, cloud/provider call, credential access or database action was allowed.

**Change:** `comparison_artifacts.py` first reuses the captured manifest and
telemetry validators, including run binding, generator-limit declarations and
telemetry window coverage. It also checks that the declared cost interval covers
the run, then hashes four telemetry files and the cost source under an explicit
local evidence root. It refuses traversal, symlinked roots/components, missing
or non-regular files, changing files, over-100-MB artifacts and mismatched hashes;
metadata inputs have a 2-MB limit. Descriptor-relative no-follow opens keep file
access inside the selected directory. It never modifies or prints file content,
paths or raw errors. Its result surfaces supplied generator-limit flags but
always marks content, clock and measurement approval unverified.

**Limits:** This hashes bytes; it does not attest provider provenance, scan for
secrets, validate telemetry data or cost values, independently verify clocks or
approve generator limits. Raw results and derived reports are not checked by
this tool. Operators must supply sanitized evidence; a matching hash alone is
not a valid result or NFR pass. The separate metadata validator retains its
honest statement that it does not inspect artifacts.

**Checks:** 22 focused Python tests passed with warnings as errors, including
synthetic captured metadata, valid/missing/modified files, file/root/directory
symlinks, traversal, limits, telemetry/cost windows, generator-limit flags and
sanitized CLI failure. Strict Mypy and per-file Black passed; no k6 run,
experiment, cloud, database or external service call occurred. Result awaits
user verification.

### 2026-11-01 20:43:12 UTC — EXP-02 planned case/manifest binding checks

**Direction:** User verified grouped offline case, dataset and revision
cross-checks. The existing `comparison_manifest.py` validates a post-run capture
and requires actual end time, cost and evidence; it cannot be completed before
credential acquisition. It was preserved unchanged rather than misrepresenting
its capture schema as a pre-run approval.

**Preparation:** Added a separate incomplete binding-plan template and
`comparison_binding_preflight.py`. The operator supplies the intended full
application source revision, frozen dataset fingerprint and SHA-256 of the
exact complete comparison corpus, together with the ordered-reference file.
The offline check validates those fields, hashes the file, invokes the existing
ordered-reference binder (including archive/data/model/contract/source checks),
and compares the entire reconstructed corpus. A missing, malformed, mismatched
or altered input fails without a session, request or output artifact. Its exact
revision match is conservative: source equivalence across different commits is
not inferred. Passing never attests human review, deployment or authorization.

An optional `--captured-manifest` uses the existing validator on an actual
completed capture, then compares its application revision, dataset fingerprint
and corpus hash with the plan. The blank template is not treated as a captured
run. This optional comparison is post-run evidence consistency, not a pre-run
gate. The separate NFR case bundle is not accepted as an EXP-02 comparison
corpus. The existing real-target runner has not been implemented; it must invoke
or enforce all required checks before it obtains credentials or sends requests.

**Checks:** 37 focused Python tests passed, including synthetic reference orders,
bad revisions/fingerprints/hashes, altered corpus with recomputed hash, optional
captured-manifest mismatches, blank capture and explicit null refusal. Mocked manifest tests
check cross-binding logic; the separate manifest suite covers actual capture
validation. Strict Mypy, per-file Black and template JSON checks passed. No k6
run, experiment, cloud, database or external-service call occurred. Actual
reviewed ordered results, deployment/source equivalence, data parity, timing,
all other manifest and approval gates remain pending. Result awaits verification.

### 2026-11-01 20:40:42 UTC — NFR dataset-bound case draft preparation

**Direction:** User verified grouped offline NFR-01/02 case preparation. The
existing EXP-02 generator verifies the frozen archive hashes, A/B equality,
counts, schema and dataset fingerprint; its five browse pages cover first,
later and category-filter cases. Its three explicit Hybrid cases cover the
direct, related and meaning-based query classes, but their ordered answers are
not supplied. No deployment, experiment, live API or cloud call was authorized.

**Changes:** `prepare_nfr_cases.py` selects these cases into a new non-executable
bundle, adds the expected HTTP status, and preserves dataset and review metadata.
Without ordered references the Hybrid expectations remain null. If a reference
and source commit are both supplied, the existing ordered-results binder is
used; mismatched or incomplete pairs fail and no existing output is replaced.
`nfr_cases_check.js` and its offline CLI check distinct case counts/coverage,
explicit Hybrid requests and existing response validator rules for status,
page, availability, filters and required fields. Ordered response comparison
reuses `correctResponse`; reversing a synthetic expected page fails. The checks
always state execution and NFR acceptance are false.

**Limits:** Browse expectations are archive-derived and still require SE-01
owner review. Synthetic test rankings are used only as test fixtures, never as
actual results. The checker does not attest provenance/review of an arbitrary
bundle or inspect a deployment; correct response shape is not proof of ranking
review. Its existing response validator uses the current clock for availability.
Actual ordered Hybrid answers, final source/deployment binding, complete NFR
profiles, zero-retry/cap/session gates and a real runner remain pending.

**Checks:** 28 focused Python tests and three Node test files passed; strict
Mypy, per-file Black and whitespace checks passed. A local generated draft passed NFR-01 case-shape checks and NFR-02
refused its missing rankings, without any request. Synthetic tests cover
determinism, refusal and existing-output protection, reference-binder reuse,
status/page/filter/availability/fields and reversed ordered results. No k6
workload, experiment, database, cloud or external service call occurred. Result
awaits user verification.

### 2026-11-01 20:38:08 UTC — NFR draft preflight preparation

**Direction:** User verified a grouped offline validator/test/documentation step.
The existing browse and Hybrid drafts were left unchanged. The NFR design's
rates and 60/300/5-second warm-up/measurement/timeout values are checked rather
than silently replacing draft fields or changing the approved design.

**Preparation:** Added `nfr_profile_preflight.js`, which reuses the existing
draft query validator and comparison route rules, checks the NFR-specific rate,
fixed time values, bounded case list and capacity, explicit Hybrid selection,
and supplied ordered UUID arrays. It allows an explicitly empty page but does
not claim that it is representative. `nfr_profile_preflight.mjs` is a bounded
local-file CLI with sanitized errors and no networking or session code. A
passing result always states execution is not permitted and no NFR is accepted.
The existing loopback runner already rejects `nfr-draft`; the preflight is not
wired into a real-target runner, which does not yet exist.

**Remaining:** This check does not attest human review, final dataset, code or
model binding, case coverage, expected field/page/filter correctness, maximum
approved VUs, zero retries, clock or target/session controls. The future runner
must enforce the complete corpus and manifest before credentials or requests.
The SE-01 owner must complete and review NFR-specific profiles; this check is
not a replacement for that ownership. Timing protocol remains open.

**Checks:** Existing drafts refused; synthetic test cases cover rates, fixed
timing, missing and invalid IDs, duplicates, malformed queries and required
Hybrid mode. Three Node test files and 18 focused Python tests passed; direct CLI
refused the stale browse draft. An initial Node test expected captured child
stderr, but the local environment returned an empty captured stream despite the
CLI directly printing the sanitized error; the test now checks refusal by exit
status and the direct CLI output was checked separately. No k6 run, experiment,
cloud, database or external-service call occurred. Result awaits verification.

### 2026-11-01 20:33:11 UTC — NFR-01/02 local denominator preparation

**Direction:** User verified the grouped synthetic NFR-01/02 reporting step
and requested multiple tasks per checkpoint. Inspection found the existing
`scripts/evaluation/k6/runner.py` local cohort reporter, which already counts
issued work, drops, missing outcomes, failures and the issued denominator. It
remains a bounded loopback pilot and is not a real-target or measurement runner.

**Change:** Extended that reporter instead of duplicating it: each cohort now
reports both the fraction of correctly completed requests within 1,000 ms and
the fraction of issued requests that are correct within 1,000 ms. The boundary
is inclusive. This local pilot assumes every issued request is eligible; actual
NFR-02 eligibility must be established by its real runner. A cohort with no
correct results has no correct-denominator fraction. Drops and missing outcomes
remain visible and invalidate the pilot; the existing `valid` condition also
requires every result correct and is stricter than either NFR's acceptance
formula. Reports explicitly mark latency timing unverified and NFR acceptance
false. This is arithmetic preparation, not an NFR pass.

**Checks and gates:** 27 focused Python tests passed. Per-file Black and
`git diff --check` passed after formatting the changed test file. Synthetic tests exercise different browse/search
denominators, inclusive one-second boundary, timeout, no successes, dropped
arrivals and missing outcomes. Existing NFR profiles are still stale drafts;
final dataset cases, timing design, real-target runner, owner review and live
measurement remain open. No k6 workload, cloud, database or external service
call occurred. This checkpoint awaits user verification.

### 2026-11-01 20:23:45 UTC — EXP-02 ordered reference source binding

**Direction:** User verified upstream integration and said the latest search
implementation will be used in production. That is future intent, not proof of
a current deployment. Latest merged main at reconciliation was `1f11065`;
the exact final production/source revision must be checked before a run.

**Change:** The ordered-reference template now requires an explicit full search
implementation commit, left null until supplied. The offline binder requires a
separately supplied intended full 40-character lowercase Git commit and refuses
invalid or mismatched revisions before constructing the corpus; it records the
matching revision in the derived corpus alongside contract and model bindings.
The supplied command argument and reference are operator assertions: matching
strings do not prove deployment, code identity or independent review. The real
ordered answers were not available and no production data or results were
invented. Reviewed rankings, final revision mapping to deployed artifacts and
run gates remain pending. The corpus remains non-authorizing.

**Checks:** 23 focused synthetic ordered-reference/corpus/manifest tests passed;
strict Mypy, per-file Black, template JSON parsing and whitespace checks passed.
Tests include malformed/missing/mismatched source
revisions, refusal before corpus loading, no output on mismatch and immutable
existing output. No k6 run, experiment, cloud, database or external-service
call occurred. Result awaits user verification.

### 2026-11-01 20:18:19 UTC — EXP-02 upstream category-search reconciliation

**Direction:** User requested checking the remote and then incorporating its
new main commit. Fetched `origin/main` at `1f110650d056f800e0179aec06f9b8747ad377ef`
(PR #25) and merged locally; the only conflict was the shared work log. Both
branches' dated entries were retained in UTC order. Frozen manifests and dataset
contents were not edited.

**Dataset evidence:** The upstream work log records Aditya's confirmation of
DATA-READY and reports Suraj's review, against PR #24's accepted dataset with
5,000 users, 1,000 listings, 1,000 verified images, 22 reviewed queries and
logical fingerprint `7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98`.
This is a recorded human acceptance, not independent verification by this agent;
the immutable release retains `data_ready: false` from capture time. Actual A/B
deployment/data/configuration parity and ordered-result review remain separate.

**Search impact:** PR #25 incorporates current category labels in lexical
matching used by Hybrid; semantic embedding input and stored fingerprints are
unchanged. Changed candidate membership/order and a supplemental label scan can
affect correctness and latency. Existing comparison case query texts remain
drafts; obtain and independently review exact ordered results against the final
search implementation before binding. The existing ordered-reference binder
checks search-contract and model revisions, but does not bind an explicit
search implementation revision. That missing binding is an open preparation
gap; source/image revision in the run manifest alone does not make the reference
review itself apply to that implementation. No ranking or new label is invented.

**Checks:** 104 focused Python tests passed, including corpus, manifest,
reporting and affected non-database Listings search tests; five JavaScript test
files passed. Contract generation check passed for all eight artifacts using a
previously available temporary Node 24.22.0. Merge whitespace checks passed.
No experiment, workload, cloud, database or external-service call was performed.
Search NFRs, actual deployed revisions, NFR ownership and independent timing
protocol review remain open. Result awaits user verification.

### 2026-11-01 20:11:52 UTC — NFR preparation and ownership inventory

**Direction and scope:** User verified a read-only inventory of NFR preparation,
ownership and local gaps. Reviewed `nfr/measurement-design.md`, the domain task
list and status rows, workload drafts, evaluation scripts and evidence homes.
No experiment, k6 workload, cloud, database or external-service call occurred.
The repository's current formal DATA-READY and reviewed-result gates are not
claimed satisfied; the user's preparation-only assumption remains an assumption.

| NFR | Owner and approved workload | Existing preparation | Remaining work and gates |
|---|---|---|---|
| 01 Browse | SE-01 (C); 20 requests/s, 60 s warm-up and 300 s measured; at least 95% of correctly completed requests within 1 s; image bodies excluded. | Draft profile and manifest; shared local k6 correctness and comparison tooling. | Dataset-bound reviewed browse cases, approved profile, real-target authenticated runner, telemetry and timing decision; deployed evidence and owner acceptance. |
| 02 Search | SE-01 (C); 10 requests/s, same windows; 95% of all issued eligible requests correct within 1 s, including failures in denominator. | Draft Hybrid profile/manifest; shared local tools and three Hybrid query bindings. | Approved independent search cases and real runner, query/DB signals, timing decision and deployed evidence; ordered comparison references alone do not complete this distinct NFR. |
| 03 Peak | INT-01 (A coordinator); 50 operations/s mixed read/write workload, not the read-only comparison burst. | Design defines deterministic 100-operation mix and expected accounting. | Owner-built profile, controlled writes/CSRF checks, operation-ID reconciliation, cap and cleanup plan, real integrated path and evidence. |
| 04 Usefulness | SE-01 (C); at least 20 included reviewed queries, Success@5 at least 80%, failed retrievals included. | `search.py` validates label structure/binding and provides synthetic arithmetic; reference-label tools exist. | Final independently reviewed labels and binding, actual retrieval adapter and real scoring integration; preview does not attest review or accept the NFR. |
| 05 Chat | CN-01 (D); two clients, 60 messages at 5 s intervals over 300 s with approved background load; at least 57 visible by deadline. | Design defines sender-submit-to-recipient-display timing and privacy constraints. | Owner-built two-client harness/profile, actual display observation, authenticated encrypted integrated path, notification handling, approved browser driver and real evidence. |
| 06 Recovery | INT-01 (A); approved loss of one ECS task, restored configured healthy capacity within 240 s. | Detailed observer inputs, timing and stop rules are designed. | Owner-built observer, reviewed exact task/fault plan and local doubles; actual authorized infrastructure and recovery evidence. |
| 07 Restore | INT-01 (A); latest managed backup to an isolated target, usable with integrity/smoke within 30 min. | Detailed restore and safety requirements are designed. | Owner-built observer and local doubles, identified backup/isolated target, caps and cleanup plan, separate cloud approval and real evidence. |
| 08 Budget | INT-01 (A) and CLOSE-00; project total under USD 200, shared costs not double-counted. | Evidence requirements and per-run cap guidance are documented. | Owner-led cap/ledger and actual billing/usage reconciliation, delayed charges and final closeout after all spending. |

**Stale draft conflict:** `browse-nfr-draft-v1.json` and
`hybrid-nfr-draft-v1.json` still specify 30 s warm-up and 3 s timeout, while the
current NFR design specifies 60 s and 5 s; both also have null expected IDs.
They are drafts, not approved runnable profiles. Do not quietly use or update
them as a final decision. The older keyword draft is not an instruction to add a
second search call; product NFR-02 uses explicitly selected Hybrid behavior.

**Independent preparation candidates:** Within EXP-02 ownership, prepare shared
offline input/manifest validation and reporting contracts that preserve distinct
NFR-01/02 denominators, use synthetic fixtures, and refuse incomplete final
cases before any session. Confirm actual SE-01 ownership and reviewed contracts
before implementing NFR-specific profiles or real-target paths. CN-01 belongs
to D but its two-client harness is a separate task/step with a browser-driver
choice; INT-01 and SE-01 owner work must not be silently taken over. Real
retrieval, human review, deployed authentication, fault injection, restore,
budget data and all cloud actions remain outside this inventory. The proposed
comparison clock/phase change remains unapproved and does not alter other NFRs.

**Checks:** Read-only repository inspection and `git diff --check`; no test
or measurement run. Inventory awaits user verification.

### 2026-11-01 20:03:45 UTC — EXP-02 offline phase-report preparation

**Direction:** User verified preparing the candidate timing report with
synthetic inputs; approved timing and NFR rules remain unchanged. The JavaScript
preview can now select blocked, duration, connecting and TLS from one supplied
synthetic response without retaining its body; failed outcomes carry no inferred
timings. The new offline Python report accepts bounded JSON records, calculates
per-response blocked-plus-duration percentiles and separate per-phase summaries,
and reports failure counts. It suppresses all candidate percentiles when any
correct sample has missing, invalid or over-five-second phases: none is silently
removed. The timeout check is only a warning, not proof of an impossible span.

**Safety and scope:** Output is created exclusively at a new path; existing raw
or report files are not overwritten. The report does not obtain correctness,
sessions, live data or provider telemetry, and always marks timing unverified
and NFR acceptance false. Neither collector nor report is wired to the actual
workload or scoring. Successful, failure and interruption behavior in real k6,
clock observation and the protocol revision remain pending owner review.

**Checks:** Twelve focused Python tests and three Node test files passed;
per-file Black and `git diff --check` passed. Synthetic tests cover opposite phase distributions (showing
why per-request pairing matters), failure accounting, invalid/missing phases,
over-timeout suppression, immutable input and refusal to replace output. Node
tests cover selecting fields without retaining bodies. No k6 run, network
request, experiment, cloud or database action occurred. Result awaits user
verification.

### 2026-11-01 19:54:53 UTC — EXP-02 connection timing clarification

User verified the proposed protocol documentation and requested removing the
double-count warning wording from the preparation guide, while asking for an
explanation in conversation. The guide retains the factual relationship that
successful TCP and TLS setup falls within blocked time. Historical timing
findings remain preserved here. No protocol approval, workload or live action
occurred; affected-owner review and the scoring decision remain pending.

### 2026-11-01 19:50:33 UTC — EXP-02 proposed timing protocol revision

**Direction:** User asked to retain the connection-timing explanation and
continue the built-in timing evaluation. The preparation guide now explains
TCP, TLS, blocked, duration, connection reuse, overlap, per-response sums and
failed connection limitations. This is an exact proposal for review; it does
not itself amend the approved EXP-01 protocol or accept an NFR.

**Proposed comparison rule:** Use the same pinned, provenance-verified k6
version and telemetry setup for both paths. For every issued request preserve
the outcome, raw phase data and case/phase binding without secrets. For each
independently verified correct response calculate `blocked + duration` from
that same response, and calculate p50/p95/p99 over those per-response sums.
Use the measured-phase correct-response p95 of that approximation for the
comparison score, subject to all existing eligibility, success, load, parity
and run-validity gates. Report `duration` percentiles and blocked, connecting
and TLS diagnostics separately. Never add percentiles or add connecting/TLS
again to blocked. Describe the approximation's clock and boundary limitations.

Count every incorrect response, timeout, throttle, other failure, interrupted
request and dropped arrival in the existing accounting; do not call a failed
acquisition's zero blocked time a complete elapsed measurement. Retain raw
outcomes even when an interval cannot be timed. Flag missing, nonfinite,
negative or suspicious phase values for review; do not silently drop them to
improve a percentile. The five-second timeout is a warning boundary, not proof
that a longer observed sum is impossible. A material clock adjustment or other
unresolved timing anomaly invalidates the affected paired evidence; stable
looking numbers alone cannot prove that no clock adjustment occurred. Define
clock observation, anomaly criteria and paired-run handling before the run.

**Scope and gates:** This proposal would relax the comparison's verified
monotonic/full-call requirement; the source owner and affected experiment/NFR
owners must review the final wording and user must verify it before the change
is treated as approved. NFR-01 and NFR-02 have different workloads and
denominators; any use there requires their own reviewed timing decision.
NFR-05 remains sender-to-recipient display timing, not this HTTP metric. A
plausible phase sum does not establish PRD end-to-end coverage for every path.
The custom timer remains a disconnected prototype; no deletion or selection is
implied. No experiment, workload, cloud or database call occurred. This
documentation checkpoint awaits user verification.

### 2026-11-01 19:44:42 UTC — EXP-02 built-in phase timing evaluation

**Direction:** User accepted evaluating the simpler built-in timing proposal.
The current approved monotonic requirement is not changed by this local
evaluation; the timer extension remains disconnected and no measurement ran.

**Finding:** In pinned upstream k6 v2.3.0, for successful acquisition `blocked`
spans acquisition and includes connection and TLS intervals; adding those
subphases again double counts. `blocked + duration`, calculated from the same
response, is a candidate approximation for correct responses, not verified
full JavaScript-call duration or a monotonic measurement. Failed acquisition can
leave blocked at zero; other failed and interrupted paths also need separate
accounting. The tracer uses Unix timestamps and checks can miss plausible clock
errors. Equal tools do not guarantee equal error between runs. A clock adjustment,
late completion or runtime overhead can affect a value without a negative number.

**Preparation:** Added disconnected `comparison_phase_preview.js` and synthetic
tests. It produces per-response `duration` and `blocked + duration` only when
the caller identifies the response as correct; it flags missing, nonfinite or
negative phases and sums above the configured comparison's five-second timeout.
The cap is a conservative flag, not proof a longer value is impossible. It does
not infer correctness, accept an NFR, change the runner, replace raw data, or
compute a percentile by adding separate phase percentiles. A zero phase is not
proof that acquisition was measured; synthetic values cannot verify live k6
timing semantics or independent oracle results.

**Checks and gates:** Three Node test files and five Python report tests passed;
`git diff --check` passed. No k6 run, request, cloud or database call occurred.
Before adopting this for scoring, review version/source provenance, successful
and failure boundaries, result association, clock risk and measurement overhead;
then explicitly revise the approved comparison protocol and its specific NFR
procedures. Browse and search denominators differ; chat timing remains separate.
This evaluation awaits user verification.

### 2026-11-01 19:25:44 UTC — EXP-02 timer extension bridge inspection

**Direction:** User verified a temporary custom k6 build and initialization-only
bridge check. The checkout started clean at `2defe37`. A temporary Go main
imports the prototype and `go.k6.io/k6/v2/cmd`, with upstream k6 v2.3.0 and a
local replacement for the extension. Public dependencies were fetched into
`/tmp/clip-timer-gopath` under the user's internet authorization. The temporary
binary was built with Go 1.27.1 using `GOPROXY=off`, `-trimpath` and
`-buildvcs=false`; its SHA-256 is
`d66a62b633cb49b3d028072661d4869a7fc8d1d3d965de45d593e05dab6d224f`.
Its version output identifies the local extension as `(devel)`; this hash
identifies the temporary file, not an independently reproduced or approved build.

**Check:** Added `monotonic/inspect_bridge.js`. A custom-binary `k6 inspect`
successfully imported the extension, observed errors on stop-before-start,
double-start and double-stop, and checked a finite nonnegative elapsed value.
The default function throws if executed. `k6 inspect` only evaluated script
initialization and sent no request. The first build attempt failed automatic VCS
stamping outside a Git checkout; the documented retry disabled that stamping.
An initial offline dependency resolution also failed on uncached modules before
the approved download. Both failures were resolved locally.

**Limits:** This is one initialization context, not a multiple-VU or request
timing test. It establishes neither clock accuracy nor exception/timeout
boundaries. The temporary build inputs and binary are not a reproducible release;
source review, build provenance, independent verification and actual run gates
remain open. The workload still does not import the extension. No k6 run,
benchmark, live API, cloud or database action occurred. Result awaits user
verification.

### 2026-11-01 19:11:27 UTC — EXP-02 monotonic timer prototype

**Direction:** User verified a local, disconnected per-VU timer prototype.
The new Go module pins upstream `go.k6.io/k6/v2` v2.3.0 and records transitive
module checksums; the installed development k6 binary is not assumed to match.
Go 1.27.1 compiled the module, whose dependencies require Go 1.26 or later.
`module.go` creates an independent timer for each VU. `timer.go` keeps Go's
monotonic `time.Time` in memory, rejects repeated starts and stop without start,
returns elapsed milliseconds, clears state, and rejects a backwards test clock.
It exposes no absolute time, data, network operation or remote execution.

**Checks:** `gofmt` and `go test ./...` passed with the pinned modules; injected
clock tests exercise ordering, reset, backwards time, duration and per-instance
isolation. The initial public-module fetch failed because the sandbox blocked
DNS; the user had allowed internet, and the approved network-enabled retry
downloaded dependencies to `/tmp/clip-timer-gopath`. Subsequent tests used
`GOPROXY=off`. No k6 workload or live-system action occurred.

**Limitations:** No custom k6 binary was built, the JavaScript/Go bridge has
not been tested in a k6 runtime, and request, exception and timeout boundaries
are not verified. The extension is not imported by the workload, and reports
still mark latency unverified. Independent review, reproducible binary/provenance,
safe runtime checks and the actual run gates remain open. Result awaits user
verification.

### 2026-11-01 19:08:52 UTC — EXP-02 timeout accounting and timer contract

**Direction:** User verified the official-source findings and authorized the
timeout correction and monotonic-timing preparation. No k6 workload, benchmark,
live API, cloud, database or secret access was authorized or performed.

**Change:** `comparison_outcomes.js` classifies the upstream request timeout
1050 and TCP dial timeout 1211 as timeout, and distinguishes refused connections,
authorization failures, throttles and other errors. `comparison_load.js` uses
it before the existing independent response correctness check; HTTP 200 remains
insufficient for success. `comparison_outcomes.test.mjs` covers those cases with
synthetic response objects. This fixes the identified code path, not every
possible timeout mapping; the installed development binary remains unbound to
the upstream source reviewed earlier.

**Timing preparation:** The official k6 JavaScript extension documentation
supports a per-VU module instance. The input guide now outlines a bounded
start/stop monotonic timer contract and the source pinning, build provenance,
synthetic tests and independent runtime verification needed. It remains an
unselected proposal: no extension, custom binary or verified clock exists.

**Checks:** Four Node test files passed, including eight synthetic outcome
assertions; eight focused Python runner/report tests passed. `git diff --check`
passed. Reports remain preview-only and the result awaits user verification.

### 2026-11-01 19:07:32 UTC — EXP-02 official k6 timing source review

**Direction:** The user allowed internet access, retaining the prohibition on
workloads, live APIs and cloud or database actions. Reviewed the official
[k6 v2.3.0 tracer](https://github.com/grafana/k6/blob/v2.3.0/lib/netext/httpext/tracer.go),
[transport](https://github.com/grafana/k6/blob/v2.3.0/lib/netext/httpext/transport.go),
[error codes](https://github.com/grafana/k6/blob/v2.3.0/lib/netext/httpext/error_codes.go),
and [Go monotonic clock documentation](https://pkg.go.dev/time#hdr-Monotonic_Clocks).
This is tagged upstream source, not proven identical to the installed development
binary, whose source revision is unknown.

**Finding:** The upstream tracer converts event times to `UnixNano` integers;
that discards Go's monotonic clock reading. It calculates blocked time between
connection acquisition events, while connecting and TLS intervals fall within
that span for successful new connections, so blindly adding all three can double
count. If connection acquisition never succeeds, blocked is not populated by
that calculation. Phase summation therefore does not establish the approved
monotonic full-operation boundary, particularly for failed connection attempts.
The source handles reused connections and records metrics after the body is read,
but the start of the full JavaScript call and all failure paths still need a
separate supported timing method. No timing implementation was changed.

**Additional defect found:** Upstream maps request timeout to 1050 and TCP dial
timeout to 1211. `comparison_load.js` currently classifies only 1050 as a
timeout; a 1211 response is instead counted as a transport error. This must be
corrected and covered by synthetic tests before measurement. Other timeout
sources and installed-version behavior need review; no complete timeout
classification is claimed.

**Next:** Prepare and test a bounded monotonic timer extension or another
supported approach, pinning and verifying the binary/source relationship; fix
the identified timeout accounting in a verified implementation step. No k6
run, benchmark, deployed API, cloud, database or secret access occurred. This
source-review result awaits user verification.

### 2026-11-01 18:54:10 UTC — EXP-02 exact k6 source availability

**Direction and checks:** User verified an offline check of the installed k6
implementation and the extension alternative. The worktree started clean at
`7eb9dc9`. `go version -m /usr/bin/k6` identifies module `go.k6.io/k6/v2` as
`(devel)`, built for linux/amd64 with Go `go1.27.1-X:nodwarf5` and trimpath;
the binary SHA-256 is
`603b32fb28e5802a4a64bd053c0f2ec0d27146dfef8d803bd429abea37236960`.
The command reports no exact k6 source revision. The local Go module/download
caches searched contain k6-related dependencies but not the k6 module source;
the installed documentation contains only a general README. Thus the installed
implementation's request-phase boundaries, monotonic behavior and failed or
timed-out request coverage could not be traced or verified locally. The binary
hash identifies this file but does not establish its source revision.

**Candidate, not a decision:** A narrowly scoped extension could retain a Go
monotonic start instant per virtual user and expose elapsed duration after the
synchronous HTTP call, while keeping outcome classification separate. It would
need a pinned k6 source revision, compatible extension build tools and Go
version, a reproducible binary and digest, confirmation that start/end brackets
the approved full-response boundary, and owner review. Tests would need to cover
per-VU isolation, invalid or missing starts, timeout/exception paths and overflow,
using injected clocks and local doubles; later runtime checks remain gated.
It must not expose absolute timestamps, secrets or a general remote capability.
No extension was built, selected or validated; the built-in metrics might still
suffice if exact source and all boundary cases substantiate them.

**Outcome and next gate:** Obtain an identified, reviewable source revision and
authoritative timing semantics through an allowed channel, or select a pinned
version after the required review. Independently establish failure, timeout and
connection-reuse behavior before changing workload timing. No k6 run, network,
cloud, database or external-service call took place. The existing timing remains
preview-only. Result awaits user verification.

### 2026-11-01 18:51:31 UTC — EXP-02 monotonic timing investigation

**Direction:** User verified the proposed local timing investigation. No
workload or external-service call was authorized. On the installed Linux k6
v2.3.0, an initialization-only `k6 inspect` probe with a temporary empty config
reported `performance`, `performance.now`, `Temporal` and `process` undefined;
`k6/timers` exposed `setTimeout`, `clearTimeout`, `setInterval` and
`clearInterval`, rather than an observed elapsed-time clock. The first inspect
attempt used `/dev/null` as a config and failed JSON parsing; retrying with an
empty JSON object succeeded. Neither invocation sent requests.

**Finding:** The approved boundary is request start through full response,
including connection setup when incurred, using a verified monotonic client
clock. The locally available k6 README does not establish that a combination of
HTTP phase metrics covers that boundary for connection reuse, failures and
timeouts, or prove its clock behavior. In particular, adding connection and TLS
submetrics without proving their relationship to blocked time could double count.
No replacement was implemented or approved; Date.now remains preview-only.

**Next:** Examine authoritative source or documentation for the exact installed
version and independently verify successful, reused-connection, failed and
timed-out timing boundaries before selecting an approach. If built-in phases
cannot meet the protocol, evaluate a bounded k6 extension providing a monotonic
clock and its toolchain implications, then seek the required design review.
Any future runtime verification and deployed testing remain separately gated.
No measurement or NFR acceptance is claimed. Result awaits user verification.

### 2026-11-01 18:48:42 UTC — EXP-02 local safety and reporting audit

**Direction:** The user verified the preceding grouped result and approved a
local timing, runner-safety and report audit. The checkout was clean at the
start, at `422a45a`; no live requests or workload runs were authorized.

**Timing:** The approved boundary includes connection setup and requires a
verified monotonic clock. The installed Linux k6 v2.3.0 previously lacked
`performance.now` in an inspect-only probe. `Date.now` can change with wall time,
and built-in `http_req_duration` omits connection setup, so neither resolves the
approved boundary. No supported replacement has been verified. The report now
states `latency_timing_verified: false` and explains that matched accounting and
no detected backward jumps do not establish valid timing. Latency figures remain
preview values; a clock solution and verification remain open.

**Runner and evidence:** The existing bounded local smoke runner permits only
documented loopback ports and validates the entire supplied case batch through
`k6 inspect` with a placeholder before synthetic login. It is not a real-target
runner; real-target credential and request gates remain to be implemented. The
report opens raw data read-only and creates a separate report exclusively; tests
cover unchanged raw hashes and refusal to overwrite existing analysis. It
reports counts, throughput, errors, timeouts, throttles and drops, and explicitly
marks infrastructure telemetry uncollected. Artifact contents, real metrics,
and provider claims are not verified by these local tools.

**Checks:** 35 focused Python tests and three Node test files passed. The system
Python lacked pytest and Black; the repository virtual environment supplied them.
Black's multi-file invocation failed because its worker socket was denied by the
sandbox; both individual file checks and `git diff --check` passed. No k6 run, experiment,
cloud, database or external-service call occurred. This result awaits user
verification.

### 2026-11-01 18:23:04 UTC — EXP-02 ordered references, timing and telemetry preparation

**Direction and scope:** The user verified a grouped Steps 4, 6 and 7 local
preparation checkpoint and requested detailed experiment logs. For preparation
only, treat DATA-READY and ordered Hybrid results as assumed available; neither
is recorded as actually accepted. No workload, API, cloud or provider call was
authorized or performed. Existing modifications and untracked work were retained.

**Step 4:** Added `comparison_ordered_results.py` and an incomplete ordered
reference template. The adapter checks frozen archive/data/schema/model/search
contract bindings, the three exact query IDs/texts, supplied order, eligibility,
duplicates and page shape, then reconstructs expected public listing fields from
the synthetic archive. It records a canonical reference hash and a review-record
pointer, without claiming the referenced review occurred. Output is created only
at a new path and remains non-authorizing. The actual ordered results were not
present in the repository and were not invented; tests use explicitly synthetic
orderings. The initial corpus remains a draft until actual references are supplied.

**Step 6 timing correction:** Inspection found that `comparison_schedule.js`
placed a five-second gap between the burst warm-up and measured arrivals, despite
the approved immediate 10-to-50 requests/s transition. The previous Step 5 log's
claim of an immediate transition was therefore incorrect; no workload was run
under that schedule. Corrected the boundary and its test. Warm-up requests may
finish draining during the first five seconds of measured arrivals and retain
their warm-up scenario tags. k6's VU cap is per scenario, so the two burst
cohorts can jointly use up to twice the supplied cap during that overlap; a
future plan must budget and verify the combined generator limit.

**Steps 6–7 telemetry:** Added `comparison_telemetry.py` and an incomplete local
metadata template. Given a captured manifest, the validator checks the run ID,
clock declaration, operator-supplied generator CPU/RSS/VU limits and drops, and
ECS/Lambda/PostgreSQL/generator artifact references, hashes and UTC coverage.
It reports supplied-limit/headroom flags without reading artifact contents,
attesting hash values or limits, proving monotonic timing, or authorizing a run.
The corresponding preparation guide and command index describe input formats,
limitations and no-request commands.

**Checks:** 33 focused Python tests passed with warnings as errors, covering the
new binders and prior corpus/manifest/report checks; three additional mocked
runner tests passed. Four Node test files passed, including the mocked k6 adapter.
Black formatted each changed Python file individually; template JSON parsing and
`git diff --check` passed. `k6 inspect` accepted a test-only synthetic corpus and
showed burst warm-up at 12m20s and 50/s measured arrivals at 13m20s. A separate
inspect probe found `performance.now` unavailable in installed Linux k6 v2.3.0;
the existing `Date.now` code is not a verified monotonic method. Inspect sent no
requests. No experiment, real telemetry, measured result or NFR pass is claimed.

**Follow-up checks at 2026-11-01 18:27:13 UTC:** Strict Mypy initially found a
duplicate module path, then identified missing typing in the telemetry/manifest
boundary. Added type annotations and explicit validated-object narrowing without
changing manifest validation behavior. Mypy with `--explicit-package-bases` now
passes for the manifest, ordered-reference and telemetry scripts; the 16 affected
manifest/telemetry tests pass with warnings as errors. Contract freshness check
could not complete: the available Node is 26.8.2 and project-local Node 24 is
absent. The generator requires Node 24 and reported its standard toolchain error.
No dependencies were installed or downloaded. Full aggregate/contract checks
remain pending on the pinned toolchain.

**Next gates:** Obtain and bind actual reviewed search references; verify a
supported monotonic end-to-end clock and combined generator caps; validate real
telemetry artifacts/approval against actual run inputs; finish real-target/auth
tooling and the separate deployment, data, review and action gates. This grouped
local result awaits user verification.

### 2026-11-01 17:51:15 UTC — EXP-02 dataset-bound case corpus draft

**Purpose and evidence:** Continued the verified Step 3–4 corpus preparation
using the retained NEXT-06 archive, frozen-dataset manifest and reviewed
`query-labels.json`. The archive SHA-256 and logical fingerprint match the
frozen manifest; its A/B listing and image-plan records match. The final dataset
is still marked `data_ready: false` and its retained native-rebuild receipt says
SQL is not loaded.

**Result:** Added `prepare_comparison_corpus.py` and the generated
`ecs-lambda-case-corpus-v1.json`. The draft contains the approved 5/3/2 mix:
five browse cases (first/later pages, with/without category filters), three
explicit Hybrid cases using reviewed direct-word, related-word and meaning-based
queries, and two available-listing details. Browse/detail expectations are
derived from frozen rows and the public response contract. The three search cases
retain Mohit's reviewed relevant-ID sets but have null ordered responses. The
NEXT-06 Step 4 result contains six different diagnostic query phrases; its
ranking samples are not reviewed case references and cannot supply order for
these approved query texts. Canonical reference-data guidance prohibits
manufacturing rankings from relevance labels or measured top results.

**Checks:** The generator verifies the archive hash, frozen fingerprint/schema/
seed, A/B listing/image-plan equality and available-listing count. One focused
Python test passed. Black checks passed for each changed Python file. A
regenerated draft compared byte-for-byte with the retained output. k6 schedule
validation accepted the ten-case mix, and the existing response checker accepted
all seven dataset-derived expected responses. `k6 inspect` refused the full draft
with `invalid_expected_case` because Hybrid order is unset; it sent no requests.
`git diff --check` passed. No API, cloud, deployed path, performance workload or
measurement was run.

**Remaining:** The case file is deliberately not executable. Ordered Hybrid
responses need final DATA-READY search results for these exact queries and
independent Search-owner review. Browse/detail expectations also await the same
case review. Availability is frozen only through 2026-12-01; run timing must
remain within that window or the dataset/cases must be revalidated. See the
[case draft](../../data/evaluation/workloads/ecs-lambda-case-corpus-v1.json)
and [generator](../../scripts/evaluation/k6/prepare_comparison_corpus.py).

### 2026-11-01 16:11:38 UTC — EXP-02 Step 8 immutable raw and versioned analysis

**Direction:** User verified the Step 8 understanding. Reopened the EXP-02 task
and evidence rules. Existing `comparison_report.py` already reads the raw k6
file without writes and uses exclusive creation for its separate report path.

**Implementation:** `comparison_manifest.py` now rejects a captured record when
its raw-output and derived-report references are identical. The k6 guide says to
preserve earlier reports and write corrected calculations to a new versioned
path. `test_comparison_manifest.py` covers a reference collision;
`test_comparison_report.py` exercises the CLI, verifies the raw file's SHA-256
is unchanged, and confirms a repeated report command refuses to replace the
existing report. The report generator itself needed no behavior change.

**Checks:** Nine focused Python tests passed. Black check-only passed for each
changed Python file; the run-manifest template validator returned `valid: true`,
`state: template`, `measurement_authorized: false`; `git diff --check` passed.
An initial multi-file Black invocation failed to start worker processes in the
sandbox, and a second multi-file invocation stalled; formatting and check-only
were then run per file and passed. No k6 workload, cloud call, or measurement ran.

**Remaining:** Step 8 is verified. The tool proves local no-write and
no-overwrite behavior, but there are no actual captured run files or hashes yet.
All deployment/parity, case-review, capacity, run-approval, telemetry, cost,
and cleanup gates remain open.

### 2026-11-01 16:06:30 UTC — EXP-02 Step 7 evidence manifest preparation

**Direction:** User verified the Step 7 understanding. Reopened the experiment
and evidence-home instructions: every run needs identifiable revisions, target,
data/workload, timing, telemetry, cost, raw/derived outputs and cleanup evidence;
the record excludes secrets and personal/private content.

**Implementation:** Added
`ecs-lambda-run-manifest.template.json` with placeholders for configuration A/B,
condition/repetition, owner role, planned/actual UTC times, target account/role/
region/resource IDs, app/image/frontend/migration/API revisions, dataset seed/
counts/fingerprints, workload/case/script hashes and command reference, per-system
telemetry artifact paths and hashes, cost source/interval/amount/billing delay,
raw/derived evidence hashes, and approval/cleanup references. The approved mix,
timing and retry policy are repeated as immutable constants. `comparison_manifest.py`
validates exact fields and those constants, checks captured records are complete,
checks count/fingerprint/UTC fields, screens common credential/PII/signed-URL
patterns, and always reports that validation grants no measurement authorization.
`test_comparison_manifest.py` covers untouched templates, missing/extra data,
unsafe values, schedule drift, complete capture records and undersized datasets.
The workloads README, k6 guide, evaluation index and environment command registry
document where per-run copies belong and how to validate them.

**Checks:** Four focused Python tests passed; the template parsed and the validator
returned `valid: true`, `state: template`, `measurement_authorized: false`. Black
reported both changed Python files unchanged; JSON parsing and `git diff --check`
passed. No run values were filled and no cloud/load action occurred.

**Remaining:** The exact run command, target/resource identifiers, deployed
revisions and migration head, accepted dataset and paired-case fingerprints,
telemetry/cost records, approval reference and cleanup evidence are not available
until the real deployment and run gates. Copy and populate a manifest only for an
actual authorized run; do not treat this template or validation as authorization.

### 2026-11-01 15:56:58 UTC — EXP-02 Step 6 request accounting

**Direction:** User verified the Step 6 scope. The plan requires request outcomes,
latencies, timeout/throttle/failure counts, offered and successful throughput,
and relevant runtime/database metrics, with authentication outside measured
traffic.

**Implementation:** `comparison_load.js` now keeps the full cohort tag, marks
HTTP 429 as throttling, and records wall-clock anomalies instead of silently
clamping them away. `comparison_report.py` reads immutable k6 JSON points and
produces separate per-cohort and per-route accounting, R7 p50/p95/p99 latency,
scheduled/issued/HTTP/dropped/completed/failed counts, offered and correct
throughput, and accounting/delivery validity flags. Dropped iterations count as
offered but never delivered. The derived report explicitly marks AWS/PostgreSQL
telemetry as not collected. `test_comparison_report.py` covers complete output,
throttle/timeout classification, dropped delivery, missing outcomes/latencies,
clock anomalies and malformed counter values. The k6 README documents how to
create a new report without changing raw results.

**Checks:** Four focused Python tests passed; three focused Node test files passed;
k6 v2.3.0 `inspect` parsed the six-cohort script; `git diff --check` passed.
Black initially reported the test file needed formatting; it was formatted, and
per-file Black checks then passed for both changed Python files. The combined
Black process had hung during shutdown. Initial unit-test failures exposed an
incomplete phase tag and mismatched synthetic case expectations; both were
corrected before the passing run. No HTTP workload or infrastructure metrics
were collected.

**Remaining:** Validate the report against actual k6 JSON from a bounded local
request run, exercise local timeout/throttle/dropped-work faults through k6,
and attach real ECS/Lambda/PostgreSQL telemetry only when deployed-path gates
and separate run approvals permit. The final cases, seed, capacity/session caps,
cloud run manifest and cleanup remain open. Step 6 is partial; no NFR or A/B
claim is made.

### 2026-11-01 14:22:56 UTC — EXP-02 Step 5 scheduled workload configuration

**Direction:** User verified the Step 5 understanding. Reopened the approved
comparison plan. Its mixed request schedule is 50% browse, 30% Hybrid search,
20% detail; the low/normal/burst rates are 0.2/10/50 requests per second; each
cohort has 60 seconds warm-up and 300 seconds measured, with up to five seconds
for drain. Burst warms at 10 requests/s then transitions to 50.

**Implementation:** `comparison_schedule.js` builds six sequential k6
constant-arrival-rate cohorts, including low-rate `1 per 5s`, and validates a
ten-case 5/3/2 mix with a paired-run rotation input. `comparison_load.js` uses
one checked HTTP read per iteration, the supplied synthetic cookie, no retries
or redirects, exact response checks and loopback-only target validation.
`comparison_schedule.test.mjs` checks cohort rates/order/drains, capacity input,
mix and stable rotation. `ecs-lambda-comparison-schedule-v1.json` records the
approved values and names remaining run inputs. The k6 README describes how
these pieces relate to the existing bounded local runner.

**Checks:** Three focused Node test files passed (3 test files); k6 v2.3.0
`inspect` parsed the prepared schedule and displayed all six executor cohorts.
JSON parsing and `git diff --check` passed. No load scenario was run. The first
test command used a missing repository-local Node path; rerunning with available
system Node 26.8.2 passed. k6 inspect used a synthetic input profile under
`/tmp`; it contains no credentials or repository dataset values.

**Open inputs and limits:** No independently reviewed final ten-case dataset
corpus or seed/rotation manifest exists yet. EXP-01 Step 7 capacity limits,
actual session concurrency/rate limits, real ECS/Lambda parity, final target,
telemetry, run/spend caps, cleanup and run authorization remain pending. The
schedule is not an executable or approved deployed run manifest and provides no
performance/NFR evidence. Step 6 outcome/latency/drop accounting remains ahead.

### 2026-11-01 14:18:17 UTC — EXP-02 Step 4 local response checks

**Direction:** User verified the Step 4 understanding. Reviewed cases contain
separate `request` and complete `expected` objects; expected values must be
prepared independently, not copied from the measured response. Final corpus
reference cases and their review remain pending.

**Implementation:** `comparison_checks.js` validates page/detail shapes,
listing fields, available-time window, categories/conditions/price filters,
pagination, uniqueness and exact ordered response equality. `comparison_smoke.js`
requires a valid expected object, checks HTTP 200 plus response content in memory,
and emits `correct`, `incorrect` or `transport_error` by case index without
retaining response content. `comparison_runner.py` pairs exactly one request and
outcome per case index, rejects missing/duplicate outcomes and returns exit 1 for
incorrect content, 2 for invalid preparation. The case input format changed;
the k6 README and command index describe it. This remains loopback-only and is
not an NFR or performance measurement.

**Checks:** Three checker tests exercise correct results, changed IDs/fields,
unavailable or wrongly filtered rows, pagination, duplicates, malformed content,
non-200, detail identity and reversed result order. Three focused JS test files
passed on Node 26.8.2; three Python runner tests passed with warnings as errors;
Black formatted both changed Python files. Real k6 against a temporary synthetic
loopback server returned `correct`/exit 0 for the expected body and `incorrect`/
exit 1 when the server returned a wrong title with HTTP 200. Server and temporary
metrics were removed. `git diff --check` passed. No real dataset oracle, real
provider, deployed A/B or cloud measurement was used; Node 24 remains pending.

**Remaining:** Independently prepare/review actual dataset-bound expected cases,
test the checks against those and both real deployed paths, and preserve final
Step 2/3 integration obligations. Step 4 local checkpoint awaits verification.

### 2026-11-01 14:14:45 UTC — EXP-02 Step 3 revised runner integrated smoke

**Direction:** User requested continuation after confirming that product search
uses Hybrid and the frontend sends a single listing-search call.

**Check:** Restarted the documented disposable synthetic inspection app on
127.0.0.1:5175; its startup action sweep passed. Invoked the registered Python
runner with browse and explicitly Hybrid search cases. Its actual k6 preflight,
synthetic buyer login and k6 run completed; it reported one HTTP 200 for each
case, with correctness unchecked and measurement false. The app was stopped
and exited 0. No response oracle, cloud, real provider, or performance run.
`git diff --check` passed. Node 24 and final k6 provenance remain pending.

**Next:** User verification of the revised runner; real deployment/session and
Step 2 A/B parity remain pending. Step 4 is the separately verified correctness
work; Step 5 sets the scheduled load profile.

### 2026-11-01 14:09:02 UTC — EXP-02 Step 3 Hybrid mode and preflight

**Finding and correction:** The generated API contract and Listings store use
Keyword when `search_mode` is omitted. Earlier local helper tests permitted a
search case without a mode, which could have exercised the wrong behavior. The
case builder now requires `search_mode: "hybrid"` explicitly and refuses absent
or Keyword modes. Prior integrated smoke cases explicitly selected Hybrid; they
remain valid for their recorded route/status scope.

**Runner behavior:** Before requesting the synthetic inspection login, the Python
runner invokes `k6 inspect` with a non-secret placeholder session. k6 initializes
and validates the entire case list without sending requests. Invalid cases are
refused before session creation. The real cookie is obtained only after preflight
and kept in the child environment for the local run.

**Checks:** Three Python tests passed (`pytest tests/evaluation/test_comparison_runner.py
-q -W error`), including refusal before login. Eleven focused JS tests passed with
approved loopback socket access. Actual k6 inspect accepted an explicit-Hybrid
case and rejected a missing-mode case; the runner returned exit 2 for the latter
while no inspection app was running. Black formatted the two changed Python files;
`git diff --check` passed. Node was 26.8.2; pinned Node 24 remains pending. No
cloud, live app, performance run or new integrated-session claim occurred.

**Next:** Recheck the modified runner with the integrated synthetic app; response
content, final workload and real deployed/session paths remain pending. User
verification of this checkpoint is pending.

### 2026-11-01 14:04:51 UTC — EXP-02 Step 3 Python local runner

**Direction and change:** User verified the previous checkpoint. Added
`scripts/evaluation/k6/comparison_runner.py`, a bounded Python orchestrator for
the existing k6 scenario. It accepts case JSON on stdin, permits only the three
documented loopback inspection ports, obtains a synthetic buyer session from the
inspection app in memory, runs the explicit k6 binary in a minimal environment,
and prints only route kinds and statuses marked `correctness: unchecked` and
`measurement: false`. It caps input, subprocess duration and temporary metrics;
it neither accepts real credentials nor runs cloud traffic. Updated the k6 guide
and command index with the local invocation.

**Checks:** `tests/evaluation/test_comparison_runner.py` passed 2 tests covering
session non-disclosure and refusal before login for invalid targets/counts/tools.
Black passed both Python files after sandbox multiprocessing stalled and an
approved escalated rerun. Against the disposable inspection app, the actual
Python runner invoked installed k6 for browse and Hybrid search: two HTTP 200
statuses, explicitly unchecked. The app was stopped, temporary metrics removed,
and no cookie or raw output retained. No cloud or performance run occurred.

**Remaining:** Detail has previously passed in the same k6 scenario; this new
runner still needs the full real-session and deployment path. Step 4 owns
response correctness and Step 5 scheduled arrivals. Node 24, final k6 provenance,
real A/B parity and approved measurement gates remain pending. Checkpoint awaits
user verification.

### 2026-11-01 14:02:36 UTC — EXP-02 Step 3 k6 local multi-case scenario

**Change:** `comparison_smoke.js` accepts one to ten cases via
`CLIP_COMPARISON_LOCAL_CASES`, validates all paths before sending, and executes
one sequential k6 iteration per case. The target remains loopback-only; the
session is supplied in memory, response bodies are discarded, and results are
not classified as correct. `comparison_smoke.test.mjs` covers three-case order,
invalid later cases and the case-count limit. This replaces the earlier singular
`CLIP_COMPARISON_LOCAL_CASE` input for this smoke scenario.

**Checks:** Four adapter tests passed with Node 26.8.2. With the disposable
synthetic inspection app and an ephemeral synthetic buyer session, a single
actual k6 invocation sent browse, Hybrid search and listing detail in that order;
all three returned HTTP 200. A browse preflight selected a valid synthetic listing
ID. Temporary k6 metrics were removed and the app stopped with exit 0.
`git diff --check` passed. No real provider, cloud or performance run occurred.

**Remaining:** This bounded scenario does not implement response correctness,
scheduled arrival profiles, dropped-work handling, real target/session handling,
or final evidence collection. Step 2 deployed parity and Node 24/toolchain
provenance remain pending. The checkpoint awaits human verification.

### 2026-11-01 14:00:23 UTC — EXP-02 Step 3 three-route local smoke

**Direction and target:** User verified the previous checkpoint. Restarted the
documented synthetic inspection app on 127.0.0.1:5175 with a disposable local
database, synthetic provider signing and the real local Hybrid model. This is
not the frozen reference corpus or a real-provider deployment.

**Method and result:** Obtained an ephemeral synthetic buyer session through the
local inspection login; one authenticated browse preflight supplied a valid
synthetic listing ID. Ran `/usr/bin/k6 run --quiet --out json=<temporary-file>
scripts/evaluation/k6/comparison_smoke.js` separately for browse, Hybrid search
and listing detail. Each k6 process exited 0 and recorded exactly one HTTP 200.
The cookie remained in process memory; temporary metric files were removed and
the app was stopped cleanly. No code changes or cloud calls occurred.

**Limits and next step:** The smoke verifies routing and status for three local
cases, not response meaning, scheduled mix, real provider identity or performance.
User verification is pending. The reviewed reference cases and their correctness
checks remain EXP-02 Step 4; rates and dropped-work handling remain Step 5. Step 2
real A/B dataset parity and Step 3 real-deployment session checks remain pending.

### 2026-11-01 13:58:35 UTC — EXP-02 Step 3 integrated local smoke

**Setup:** User verified the previous checkpoint. Installed verified uv 0.10.7
in temporary local storage and CPython 3.13.12 in `.tools/semantic/python`, then
synced the 24 hash-pinned Linux helper packages into `.tools/semantic/venv`.
Downloaded only the pinned ONNX model and tokenizer into `.tools/semantic/model`;
both matched the checked-in size and SHA-256 manifest. Initial sandbox DNS
failures were followed by approved network escalation. No global tools changed.

**Inference:** A first helper startup failed because the test resolved the venv
Python symlink to its base interpreter, bypassing venv packages. Retrying with
the actual venv path passed and returned a 384-dimensional synthetic query vector.

**Integrated smoke:** Started the documented synthetic inspection app on local
port 5175 using its disposable Docker/PostgreSQL database, actual app routes,
local Hybrid helper and synthetic signing/mail/images. Its startup action sweep
completed, including Hybrid queries. A Python harness obtained a buyer session
through the local synthetic-signing login and passed the cookie in memory to
`/usr/bin/k6 run --quiet --out json=<temporary-file> scripts/evaluation/k6/comparison_smoke.js`.
k6 exited 0; its temporary metrics recorded exactly one Hybrid search request and
HTTP 200. Metrics temporary directory was removed and the app stopped via Ctrl+C;
the launcher exited 0. No cookie was retained in the log.

**Limits:** Synthetic Identity/provider and disposable data are not deployed
real-provider evidence. The smoke checks route/session/status only: response
correctness, real accounts, final A/B workload and measurements remain pending.
No cloud action or NFR/architecture run occurred. `git diff --check` passed.
Node 24 and final k6 provenance remain pending.

### 2026-11-01 13:49:47 UTC — EXP-02 Step 3 integrated route preparation

**Finding:** The integrated app mounts its public API under `/api`, while the
generated OpenAPI contract describes `/listings` paths without that prefix.
The earlier local helper accepted only the contract-root form and would miss
the website-served integrated route.

**Change:** `comparison_cases.js` now validates only two explicit loopback
target shapes: a bare origin or its `/api` mount. Both `comparison_local.js`
and `comparison_smoke.js` use this shared guard. Their tests exercise `/api`
alongside remote/invalid-target refusal; no arbitrary URL path is accepted.

**Checks:** The three comparison test files passed 10 tests under Node 26.8.2
with approved loopback socket access. `git diff --check` passed. Docker engine
29.8.1 responds outside the sandbox after the sandbox denied its socket. The
integrated inspection launcher requires `.tools/semantic/venv/bin/python` and
`.tools/semantic/model`, neither of which is present on this machine. Therefore
no integrated-app/session smoke was started or claimed; the Node 24 and real
k6 integrated-path checks remain pending. No cloud or measurement run occurred.

**Next:** Prepare the project's supported pinned local Hybrid interpreter/model
and associated prerequisites, then run the bounded synthetic inspection and k6
smoke under the documented local procedure. Preserve real-provider/deployment
and dataset acceptance as separate gates.

### 2026-11-01 13:46:42 UTC — EXP-02 Step 3 installed k6 smoke

**User direction and environment:** User reports compiling and installing k6.
`/usr/bin/k6 version` reports `k6 v2.3.0 (commit/devel, go1.27.1-X:nodwarf5,
linux/amd64)`; binary SHA-256 is
`603b32fb28e5802a4a64bd053c0f2ec0d27146dfef8d803bd429abea37236960`.
This identifies the installed binary; it does not establish official release
provenance or approve the final measurement toolchain.

**Actual k6 check:** A short Python harness started a temporary loopback HTTP
server and invoked `/usr/bin/k6 run --quiet scripts/evaluation/k6/comparison_smoke.js`
with an in-memory synthetic cookie and a Hybrid search case. k6 exited 0; the
server observed exactly one expected `/listings?q=desk&search_mode=hybrid` GET
and the synthetic cookie. The server stopped after the check. The first sandbox
socket probe failed `EPERM`; the actual local test passed with approved escalation.
No real app, authorized real account, response correctness, cloud, timing claim,
or NFR/architecture measurement was involved. `git diff --check` passed.

**Remaining:** Check/record final toolchain provenance, Node 24 and a real
integrated-app session; complete the multi-case workload, correctness, arrival
profiles, telemetry and run manifests in their assigned steps. Step 3 remains
partial and requires verification.

### 2026-11-01 13:29:30 UTC — EXP-02 Step 3 k6 adapter preparation

**Direction:** User requested continuation and the existing k6/JavaScript plus
Python orchestration split. Base `f816f66`; `task/exp-02-workload`.

**Change:** `comparison_smoke.js` is a single-iteration k6 scenario using the
contract path builder, a loopback-only target and an out-of-band in-memory
session cookie. It does not follow redirects or declare HTTP status to be correct.
It records only a preparation response classification; it is not the measured
workload. `comparison_smoke.test.mjs` substitutes k6 APIs to check single request,
session forwarding and refusal of non-loopback targets and unsafe inputs.

**Checks:** `node --test scripts/evaluation/k6/comparison_cases.test.mjs
scripts/evaluation/k6/comparison_smoke.test.mjs` passed both files with Node
26.8.2; `git diff --check` passed. The adapter tests use mocked k6 APIs; no actual
k6 process, HTTP, real session, cloud call or measurement ran. No k6 binary is
on PATH; the existing pinned installer supports macOS ARM64, not this Linux
x86_64 environment. Node 24 and actual k6 runtime verification remain pending.

**Remaining:** Register and validate a supported local k6 toolchain and safe
session/run entry point; exercise the real app and complete response correctness,
scheduled load, telemetry and final cloud gates in their assigned steps.
EXP-02 Step 3 remains partial, pending user verification.

### 2026-11-01 13:27:01 UTC — EXP-02 Step 3 bounded local batch

**Direction:** The user verified the preceding partial checkpoint and directed
continuation. Base revision `f816f66`; branch `task/exp-02-workload`.

**Change:** `comparison_local.js` now provides `runLocalPreparation`, which
validates a whole batch before sending, permits one to ten sequential loopback
requests, stops on a transport error and records only route kind, HTTP status and
`correctness: unchecked`. Its result explicitly marks `measurement: false`.
Sessions and response bodies are not returned in the result. The existing
single-request helper carries the in-memory cookie and rejects remote targets.

**Test:** `node --test scripts/evaluation/k6/comparison_cases.test.mjs
scripts/evaluation/k6/comparison_local.test.mjs` passed six tests under Node
26.8.2. A synthetic loopback HTTP server verified browse/search paths, session
forwarding, a 401 outcome and server shutdown. Invalid later cases and batches
over ten were refused before requests. The first sandboxed attempt failed with
`listen EPERM` on 127.0.0.1; the same test passed with approved escalation.
`git diff --check` passed. No real app session, cloud call or performance run.

**Remaining:** This is a bounded preparation batch, not the scheduled k6
workload or a correctness oracle. Actual integrated app/session execution,
response checks, project-pinned Node 24, real deployment, and A/B checks remain
pending. Step 3 awaits verification before continuing.

### 2026-11-01 13:25:12 UTC — EXP-02 Step 3 local transport preparation

**Purpose and scope:** Prepare a single local read using a supplied session,
without enabling remote or cloud execution. This is partial EXP-02 Step 3.

**Changes:** `scripts/evaluation/k6/comparison_local.js` combines a reviewed
case path with an in-memory session cookie and an injected transport. It accepts
only `http://127.0.0.1:<port>`, rejects line breaks in the session, refuses
redirects and returns the transport response without marking it successful.
`comparison_local.test.mjs` exercises one search request and checks that unsafe
targets and headers fail before the transport runs. The existing case builder is
in `comparison_cases.js`; no session value is stored by this adapter.

**Checks and environment:**
`node --test scripts/evaluation/k6/comparison_cases.test.mjs scripts/evaluation/k6/comparison_local.test.mjs`
passed both test files using Node 26.8.2 on Linux x86_64. `git diff --check`
passed. The transport was simulated: no HTTP request, real session, k6 run or
cloud call was made. Project-pinned Node 24 verification remains pending.

**Checkpoint:** Partial result reported to the user; Step 3 remains open. The
complete k6 scenario, authorized real session, response correctness checks and
deployed/cloud integration are pending. Next, verify this partial result and
finish the actual local workload in the current step.

### 2026-11-01 13:14:04 UTC — EXP-02 preparation

**Direction:** The user directed Rahul to proceed, relayed Mohit's confirmation
that the dataset exists, and accepted the explanation of the two deployment
configurations. A is ECS-only; B routes selected reads through Lambda.

**Dataset evidence:** The frozen manifest and retained cloud-load receipt agree on
seed 42, 5,000 users, 1,000 listings, and logical fingerprint
`sha256:7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98`.
The frozen manifest's SHA-256 was
`fcb86edb0412f39cda77cf65be87a2e963783f95842f5080ec0456c0b64f21b4`,
matching the recorded release hash. The receipt reports 1,000 images and 800
available listings. See [frozen release](domain/next-06/frozen-dataset.json),
[cloud load](domain/next-06/transfer/cloud-load-20261031/result.json), and
[cloud/native snapshot](domain/next-06/transfer/dataset-snapshot-20261031/result.json).
This was a local evidence check, not a fresh cloud inspection or DATA-READY
acceptance. The deployed A/B database, indexes, settings and model still require
verification once both paths exist.

**Implementation and checks:** Added `scripts/evaluation/k6/comparison_cases.js`
to build contract-shaped browse, Hybrid search and listing-detail paths, and
`comparison_cases.test.mjs` to check the generated API operation names and
rejection cases. `node --test scripts/evaluation/k6/comparison_cases.test.mjs`
passed with Node 26.8.2; rerun using project-pinned Node 24. The code does not
send requests or handle sessions. No cloud action or performance measurement ran.
See the [EXP-02 work-log entry](../status/work-log.md) for the checkpoint and
pending integration.
