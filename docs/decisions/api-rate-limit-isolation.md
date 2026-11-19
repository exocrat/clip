# DEC-RT-65 — Account and anonymous request budgets

**Date:** 2026-11-17

**Origin:** Suraj-authorized API rate-limit correction and project-scope
clarification. This record contains policy and verification requirements, not
private security-report reproduction details.

## Question

How should request limits isolate signed-in accounts from anonymous traffic on
a shared campus/proxy address, and what abuse protection does the project claim?

## Options considered

- Keep an outer peer budget shared by anonymous and authenticated requests.
- Apply request budgets after trusted session classification, separating each
  account from the anonymous transport-peer budget.
- Integrate managed bot screening or CAPTCHA challenges for wider abuse control.

## Selected choice

Use one process-local request-budget policy after session verification. A current
verified account selects its account budget. Missing, forged, revoked or expired
sessions select the anonymous transport-peer budget, including requests that
Identity rejects before calling a route. Rejected transport/origin requests are
charged anonymously before rejection and do not trigger session lookups. Browser
headers and the mere presence of a cookie cannot select an account budget.

The full API and session-only Listings composition use the same policy. Apps
without an Identity runtime retain standalone request-limit middleware. Existing
read/write defaults, rolling windows, bounded counters, Retry-After responses,
body limits and authorization remain; the outer shared-peer ceiling is removed.
The original #52/#65 change left OTP policies unchanged; [the #78/#79 correction](otp-and-conversation-recovery-isolation.md) adds OTP recovery and purpose isolation. The combined #52/#65 correction retains credential
source/target counters but allows one exceptional sign-in attempt after server-side
Turnstile verification and atomic local proof consumption. Cookie clearing does
not reset those histories. Normal password/Microsoft verification remains required.

**Comprehensive bot protection is outside the project's scope.** The project
does not promise immunity to sustained automated abuse or volumetric
denial-of-service attacks, and site-wide managed bot protection is not a project deliverable. The targeted
Turnstile sign-in recovery challenge is included in this correction. Existing authentication, authorization and specified
normal/reference-workload FR/NFR targets remain required. This clarification
records Suraj's direction; it does not alter the submitted PRD artifact or turn
an observed application defect into a passing check.

## Rationale

The service already verifies sessions. It can assign the existing account budget
without classifying whether the caller is human or automated. Keeping anonymous
requests in their own peer budget prevents them from spending a verified
account's allowance merely by sharing an address.

## Implications and verification

Session validation occurs before the account-versus-anonymous budget decision;
the request budget is therefore not a bound on all authentication lookup work.
Origin/transport checks still reject before session lookup. No session caching,
shared counter service, database migration or cloud resource is introduced.
The exceptional sign-in path adds Cloudflare Turnstile as an external dependency;
normal below-threshold sign-in does not contact it. Exceptional provider work
is capped at four concurrent requests per API middleware instance so it cannot
fill the normal worker pool. Provider failures deny the
challenged operation safely, with no provider/credential data exposed. Counters
remain per process and reset on restart; this is not a
distributed rate-limiting or comprehensive abuse-protection system.

Local checks must demonstrate anonymous exhaustion without blocking a verified
account on the same address, independent account/read/write limits, anonymous
charging for rejected cookies and early authentication/CSRF responses, rejection
of forged identity/forwarding claims, and equivalent session-only behavior.
Real SQL/cookie checks supplement the small controlled-core tests. Local passing
checks do not establish a deployed fix, NFR acceptance or reporting-team retest.

## Approver

Suraj explicitly authorized the isolated implementation branch and project-wide
scope statement on 2026-11-17. Independent peer/affected Identity owner review,
commit, merge and deployment approvals remain separate gates.

## Supersedes

The outer shared-peer request ceiling described in the 2026-11-06 per-client
API rate-limit checkpoint in the [work log](../status/work-log.md). Historical
records retain their original implementation/evidence context.

## Combined authentication correction

Suraj explicitly expanded the branch to #52 and both #65 paths. The three public
sign-in POST operations advertise a challenge only on a refused 429. After user
completion the client may replay that confirmed-refused request once; it never
retries a potentially successful/uncertain write. The backend validates hostname,
action and token, and serializes a digest reservation in existing auth events
before admitting the operation. Target/source/API limits are bypassed for that
one operation only; browser cookies alone provide no exception. Unknown accounts,
wrong passwords, revoked/expired accounts, invalid assertions and reused nonces
remain denied. Credential failure counts saturate at the existing schema cap.

Both backend keys must be configured for this recovery path to exist. Tests use
a controlled provider boundary and real SQL/session/credential logic. Deployment
must supply the secret privately, verify real widget behavior and both sign-in
methods, and obtain reporting-team retest. No commit/push/deploy is authorized
by local test success; the latest human direction explicitly stops before commit.

The OTP expansion and independent conversation-control retry semantics are recorded in [OTP and conversation recovery isolation](otp-and-conversation-recovery-isolation.md).
