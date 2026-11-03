# EXP-03 Lambda path: proposed local design

Status: working proposal for owner and affected-domain review. It does not
authorize provisioning, deployment, traffic or measurement.

**2026-11-03 user direction:** Configuration B should send selected reads to
Lambda first and route overflow to ECS when Lambda capacity is unavailable.
The direct-ALB routing below is the previous draft, not an implementation of
that direction. B is blocked in Terraform until overflow has been designed,
implemented and reviewed. Capacity definition, coordination, safe fallback,
route attribution, deployment cost and experiment interpretation are open.
The existing A/B design and evidence tooling must be revised and reviewed;
neither a fixed-weight split nor an ALB target-health check implements this
per-request capacity-aware behavior.

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

Use one HTTPS origin and an Application Load Balancer (ALB) with ECS and Lambda
targets. Configuration A sends all application requests to ECS. Configuration B
sends only the selected listing reads to Lambda; all other requests use ECS.
Switching between configurations must be explicit and reversible, with the
selected listener rules and revisions captured before a run. Preserve the
existing ECS service in both configurations. Exact origin, certificate,
listener priorities, network and target group ownership remain subject to the
infrastructure owner's review. The user assigned Terraform ownership to Rahul;
independent and affected-domain review still apply.

The candidates are GET `/api/listings` for browse and Hybrid search, and GET
`/api/listings/{listing_id}` for detail. The final listener rule must match the
HTTP method as well as the exact intended path shape, and tests must prove that
write, chat, offer, image and other routes continue to ECS. Repeated query
parameters, cookies, host, status, response headers and error behavior must be
preserved. Concrete rule proposal: configuration B has a GET rule for exact path
`/api/listings` and a GET rule for `/api/listings/*`, followed by the existing
ECS default. The detail rule can also match extra path segments, but the API
must return its normal not-found response for those; no non-GET operation may
reach Lambda. Configuration A sends both paths to ECS. Target groups must
enable multi-value headers so repeated filter values and cookies are retained.

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
defaults. `app.lambda_main` stays unauthorized by default. The existing explicit
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

The current pool code is not compatible with the 20/60 proposals as written.
Listings configures a maximum of 10 connections and inherits psycopg's default
minimum of 4; Hybrid allows 2; the separate Conversations pool allows 1. Thus a
full app environment can retain up to 13 pooled connections (with up to 12 in
Listings/Hybrid alone), or 260 across 20 Lambda environments. Two retained ECS
tasks could add up to another 26. Identity uses fresh direct connections outside
those pools, so these figures undercount peak usage. At the proposed 60 total DB
connections, even 20 Lambda instances with one connection in each persistent
pool would leave no safe space for ECS, Identity, workers or administration.
The narrow lifecycle and one-connection pool maximums are now implemented
locally. Resolve the aggregate budget before setting concurrency: account for
direct Identity connections, retained ECS, administration and other services;
then choose and validate a safe concurrency/request rate or evaluate a reviewed
connection-proxy/DB-limit change. Do not assert that the default
20-concurrency proposal fits.

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
