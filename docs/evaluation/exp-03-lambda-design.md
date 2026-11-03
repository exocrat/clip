# EXP-03 Lambda path: proposed local design

Status: working proposal for owner and affected-domain review. It does not
authorize provisioning, deployment, traffic or measurement.

**Latest user direction:** Route selected reads directly through the ALB. In A,
all requests go to ECS. In B, an ALB listener rule matches only the selected
Listing GET routes and forwards them between ECS and a Lambda target group at
the configured fixed weight. Other routes remain on ECS. The pilot tests
Lambda/ECS weights 100/0, 75/25, 50/50 and 25/75 before choosing the main-run
weight. Weighted forwarding is not capacity-aware: a request sent to a throttled
or unhealthy Lambda target is not automatically retried on ECS. Record the
result as a Lambda failure. The prior ECS-hosted Lambda router and fallback
implementation are superseded and must not be enabled or deployed.

The direct path uses an ALB Lambda target group registered to the restricted
read-only function. Terraform grants `elasticloadbalancing.amazonaws.com`
permission scoped to that exact target group and enables multi-value headers.
The ECS task has no Lambda invocation permission or router settings. The HTTPS
listener defaults to ECS; only the selected method/path rule uses the weighted
Lambda/ECS action. Target-group stickiness is disabled so the pilot can measure
the configured request mix for the single synthetic account. Preserve per-target
outcomes, throttles, latency and whole-system costs. Actual ALB invocation,
session behavior, shared-data parity, safe database capacity, deployed weights,
and independent review remain unverified.

**Ingress compatibility gap:** The local builder can now remove incoming
forwarding claims, check an already-resolved HTTPS scheme and exact project
host, and add a fresh HTTPS claim. This helper does **not** authenticate the
source of the resolved scheme: deployment must prove Uvicorn trusts only the
actual load balancer and that an unauthorized Lambda invoker cannot spoof the
event. Identity requires HTTPS, while the synthetic bridge hardcodes it. A
network-isolated check of the cached real Lambda Web Adapter confirmed that a
synthetic event's HTTPS header, host, cookie and repeated filters reach a
synthetic HTTP server. A follow-up isolated check ran the cached real adapter,
Uvicorn and Identity middleware with synthetic session bindings: HTTPS reached
the handler and HTTP was denied. Actual ALB/IAM, current image, real session
and trusted-source checks remain open and block deployment. The local helper
is not itself proof of an ingress security boundary.

## Local package-input audit

At the local audit, the ignored `.tools/semantic/model` directory contains the
90,405,214-byte ONNX model and 466,247-byte tokenizer, matching manifest sizes.
The Linux AMD64 Python 3.13.12 runtime directory is 98,143,362 bytes, and the
helper environment is 172,887,905 bytes. The Linux wheel artifact directory was
absent at that audit; the subsequent approved pip-only download supplied all 24
hash-matching archives (51,910,303 bytes). Independent hash/ZIP checks and a clean
offline pip install plus dependency check passed; see the experiment log and
updated deployment handoff. The current Hybrid Dockerfile copies only the ONNX model
and tokenizer from the model context; the other manifest metadata files are not
copied by that Dockerfile and their absence is not itself a build blocker. These
files are local build inputs. On 2026-11-02 the API, Hybrid and Lambda images
were built locally for Linux AMD64 at source commit `8a60f83`. Model and tokenizer
hashes matched the pinned pipeline; the Hybrid build's one offline synthetic
inference returned the expected 384 dimensions. The Lambda image's local size
was 896,353,157 bytes. A network-disabled, credential-free container check
started the app with Hybrid disabled, verified the restricted routes and health,
and observed a 401 for a missing session. It did not exercise Lambda Web Adapter
invocation, Hybrid/Identity startup, SQL, or real authentication. Actual memory
fit, cold startup and deployed behavior remain unknown. Image IDs, commands,
failure/retry and retention are in the experiment log.

## Request path

Use one HTTPS origin and an Application Load Balancer (ALB). Configuration A's
default action sends all traffic to ECS. In B, a higher-priority listener rule
matches only `GET /api/listings` and a single-UUID
`GET /api/listings/{listing_id}`, and sends those requests to the Lambda and ECS
target groups using the fixed pilot-selected weights. All other methods and
paths use the ECS default action. The matched rule has no automatic retry or
same-request fallback. Switching configuration and weight must be explicit and
reversible, with the value and revisions captured before each run. Preserve the
existing ECS service in both configurations. Exact origin, certificate,
listener, network and target-group ownership remain subject to infrastructure
review. The user assigned Terraform ownership to Rahul; independent and
affected-domain review still apply.

The candidates are GET `/api/listings` for browse and Hybrid search, and GET
`/api/listings/{listing_id}` for detail. The ALB rule matches the method and
exact intended path shape; tests must prove that write, chat, offer, image and
other routes continue directly through ECS. Repeated query parameters, cookies,
host, status, response headers and error behavior must be preserved. Extra path
segments must retain the API's normal not-found response. The ALB sends its
request event directly to the Lambda Web Adapter. The function resource policy
grants invocation only to the ALB for the exact Lambda target group; the ECS
task role is not involved in Lambda access.

## Application and authentication

Package the existing Python application, actual search helper, pinned interpreter,
wheels and model as a Lambda-compatible container. Prefer the AWS Lambda Web
Adapter extension to a custom Python event bridge: it supports ALB and OCI images,
converts ALB events to local HTTP, and can run alongside the existing Uvicorn
server without a new Python package. `apps/api/Dockerfile.lambda` adds the
versioned extension image while requiring its immutable SHA-256 digest as a
build argument. The Lambda image extends the Hybrid API image and does not change
the ECS image. Enable ALB multi-value headers so repeated filters and cookies
survive; test exact event/request/response behavior locally. ALB's Lambda response
JSON has a 1 MB limit, which must be checked against the real response sizes.

The local `alb_event.py` and `alb_asgi.py` files are synthetic feasibility
probes, not the recommended production adapter. Do not wire them into app startup
or deploy them. Remove or retain them as test-only contract probes after the
AWS adapter's behavior is verified. The AWS extension digest was recorded from
the public registry as `sha256:17cfd08eff1dfea3f6a9a1e9c65fdac80aa4919b6085e746615530f43f57d2f1`;
independent artifact review is pending and builds fail if the digest is absent. Configure
its local HTTP port as
`8000`, matching the existing Uvicorn image, and readiness path as `/health`.
That liveness endpoint is not application or dependency parity evidence. The Lambda image disables Uvicorn access
logs so raw request paths and search queries are not emitted by that logger.

Reuse the domain's real routes and search logic; do not replace Hybrid with a
keyword or synthetic implementation. Explicitly test startup, warm reuse,
interrupted invocation and failure recovery. A local proof does not establish
cloud startup time or memory requirements.

Use the actual Identity session validation and eligibility checks, forwarding
the cookie without logging it. The adapter must construct the HTTPS scheme and
host only from the reviewed trusted ingress, not arbitrary client headers.
Unknown or missing trust information fails closed. The user assigned the
session-only Identity composition slice to Rahul. `IdentityReadDependencies`
and `install_identity_reads` reuse the existing Identity browser/session
middleware without installing Identity routes. Full ECS Identity composition
still uses its existing initializer and sender; the separate Lambda initializer
does not load the email route, warm a sender or prepare Microsoft metadata.

The local app composition now mounts only GET `/api/listings` and
`/api/listings/{listing_id}` for the Lambda target. It opens a Listings pool with
maximum size 1 and a Hybrid pool with maximum size 1, disables the Hybrid worker,
and skips the Conversations pool, notification lifecycle, wanted/saved stores,
and S3 image storage. The regular ECS app retains its existing routers and pool
defaults. In A and B the ECS test app still uses its existing full Identity
initializer: it reads the fixed email-delivery setting and warms the controlled
test email route, but sends no message during startup. Its application lifecycle
also creates the separate Conversations pool when a database DSN is present
(minimum 0, maximum 1), and initializes the configured S3 storage client. The
ECS Listings pool starts at 1 and can grow to 10; Hybrid allows 2. These are
shared A/B conditions, but they still belong in startup and whole-system resource
budgets. `app.lambda_main` stays unauthorized by default. The existing explicit
hosted test opt-in (`CLIP_IDENTITY_RUNTIME_ENABLED`, with all its existing Settings
guards) calls `prepare_hosted_test_identity_reads`. That initializer reads only
the fixed authentication-key and Identity database SecureStrings, performs the
existing role/key audit, and constructs the existing `IdentitySessions`. This
retains its current role privileges and local dummy-password hashing at startup;
it is not a new least-privilege DB role or a measured startup optimization.
Authentication uses fresh real session/account checks and retains the existing
last-seen update; a read-only endpoint surface does not mean read-only SQL.
The Lambda entry point also supports explicit hosted-test
`CLIP_LAMBDA_DATABASE_PARAMETER_ENABLED=true` to read the fixed existing
`/clip/test/listings-database-url` SecureString into an in-memory `SecretStr`
before the ordinary settings and Identity reads. It requires an actual Lambda
runtime marker, test mode, Identity opt-in, no conflicting database environment
value and otherwise valid settings before any parameter read. The explicitly opted-in Lambda read-only settings require email and recipients
to be disabled, and also reject web, notification and Hybrid worker startup.
The ordinary ECS Identity settings retain their existing recipient controls. It never accepts a
caller-selected parameter name or stores its value in Terraform/environment.
The IAM design must explicitly permit this one additional parameter; actual
secret access, database connectivity and owner review remain pending.
The browser policy still requires trusted HTTPS and accepted Origins when an
Origin is supplied. Ingress scheme/host handling remains an unverified gate.
Offline tests exercise middleware and public eligibility dispatch with mocked
session/SQL boundaries. Real expiry/revocation SQL, concurrent access, startup
and shared-session behavior between ECS and Lambda remain unverified. The built
image has not been demonstrated to serve an authenticated request.
The focused Hybrid runtime test confirms that the code accepts a one-connection
pool and suppresses the worker when overridden; it does not prove real database
or model startup at that cap.

## Database and resource limits

Use the same authoritative private PostgreSQL database as ECS. Do not blindly
reuse per-process defaults: Listings currently permits ten pooled connections,
Hybrid two, and the full app also opens a separate Conversations pool; Identity
uses its own connections. Target one Listings and one Hybrid connection per
Lambda instance as a starting proposal, subject to compatibility tests and an
aggregate budget that includes Identity, retained ECS, administration and other
work. An invocation or startup must fail safely when capacity is unavailable.
Reuse only supported session and pool lifecycles and test stale connections.

The experiment document proposes at most 2 GiB memory, reserved concurrency 20,
no provisioned concurrency and timeout at most five seconds. These are design
limits for review, not evidence that the model fits or that the database can
support 20 environments. The user explicitly rejected the proposed 300-client
ceiling as binding. Record the eventual approved settings and cost estimate.

The ECS full app explicitly sets its Listings pool to min 1/max 10 and Hybrid to
min 1/max 2. Its separate Conversations pool is min 0/max 1, so it can grow on
demand but does not open an idle connection by default. That is up to 13 pooled
connections per fully busy ECS process, plus Identity's direct session/database
connections. By contrast, the Lambda read-only app sets Listings and Hybrid to
min 1/max 1 each and skips the Conversations pool, so its pooled maximum is 2
per Lambda environment, plus direct Identity connections. At reserved concurrency
20 this permits up to 40 Lambda pool connections; two fully busy ECS processes
could add up to 26, for 66 before direct Identity, workers, administration and
other services. Actual use depends on request behavior, but a 60-connection DB
limit does not prove this ceiling is safe. Resolve the aggregate budget before
setting concurrency: include direct Identity connections, retained ECS,
administration and other services; then choose and validate a safe concurrency
and request rate or evaluate a reviewed connection-proxy/DB-limit change. Do
not assert that the 20-concurrency proposal fits.

## Verification and outstanding decisions

- Review the ingress target, listener patterns, TLS and header trust with the
  infrastructure and Identity owners; verify exact request and response parity.
- Pin and locally inspect the AWS Lambda Web Adapter artifact; verify ALB
  multi-value headers, trusted scheme/host handling, errors, body/response limits
  and its interaction with Uvicorn and the app lifecycle.
- Confirm the pinned model artifacts, Lambda image architecture, size, memory and
  startup feasibility. No model artifact is inferred from a manifest alone.
- Audit Identity connections and supported read-only initialization; determine
  pool caps and total database headroom with the database owner.
- Review the new session-only Identity composition and exercise it with real
  session/account storage, expiry/revocation and both account classes. Do not
  treat mocked sessions, health or route mounting as real authentication proof.
- Keep integration and deployed A/B checks open until both actual configurations
  run with the same data, schema, settings, indexes and search revision.
- The opt-in [shared-root Terraform draft](exp-03-terraform-preparation.md)
  prepares ingress, routing, role and Lambda resources. It requires a reviewed
  plan and unresolved host rollout, dataset, trust, budget and cleanup gates;
  cloud changes and experiments require separate explicit approval.

The user's report that an ALB can be created is not independent evidence from a
successful create operation. No load balancer has been created by this task.
