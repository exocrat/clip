# EXP-02 real-runner preparation design

Status: design draft for owner review. This describes remaining implementation;
it does not authorize a session, cloud action, deployment or experiment.
The approved [comparison protocol](ecs-only-vs-ecs-lambda-task-list.md) and
[preparation guide](comparison-preparation-inputs.md) remain controlling.

## Existing contracts and gaps

- `scripts/evaluation/k6/comparison_runner.py` is a bounded **local inspection**
  smoke runner. Its `/__inspection/login/buyer` helper and `clip_session_dev`
  cookie are local-only. They are not a production or comparison login method.
- The current scheduled `comparison_load.js` accepts only loopback targets,
  reads an explicitly supplied profile and uses one checked HTTP read per
  iteration with no redirects and a five-second timeout. Each invocation needs
  one selected `low`, `normal` or `burst` condition and schedules only that
  condition. It currently uses
  `Date.now()` and is not a final timing implementation or real-target runner.
- Identity's `apps/api/app/domains/identity/http.py` defines regular Microsoft
  login attempts and session exchange, and a distinct temporary-account
  password session route. In non-development mode the session cookie is
  `__Host-clip_session`. These routes establish interface facts, not an approved
  means to create or use a synthetic regular account for a test.
- The comparison protocol initially calls for one existing authorized regular
  synthetic account, session setup outside measured windows, and checks of
  temporary and denied callers separately. It prohibits using the isolated demo
  identity or disabling protections. Session concurrency and limits need review.
- The combined offline preparation validates a corpus, reference, planned run
  and profile hash, but does not verify review, deployed parity or later use.
  The mock runner only records synthetic events and cannot execute traffic.

## Proposed sequence for a future implementation

1. Read a bounded, reviewed run plan. Validate the complete input corpus,
   independent ordered-reference binding, pair plan, selected run and exact
   profile hash using the existing offline preparation. Stop on any failure
   before requesting a session or sending a request.
2. Verify the approved target, revisions, authentication method, run limits,
   timing protocol and all remaining action gates. The mechanism and evidence
   for deployed verification still require owner review; a local matching hash
   is not proof of target or dataset parity. Do not infer approval from a file.
3. Obtain the authorized synthetic session through the separately reviewed
   access path. Keep setup and functional authorization checks outside measured
   traffic. Keep credentials, cookies and identity claims out of arguments,
   logs, manifests, raw results and reports. Expired or unavailable sessions
   must fail closed; do not replace them with demo identity or real-user data.
4. Use the exact profile and workload bytes checked for the selected run, with
   an implementation that addresses file replacement between validation and
   use, and bind the staged run condition to both workload and report. Preserve
   the approved schedule, one request per iteration, zero retries
   and five-second timeout. A profile hash in a manifest alone is not proof
   that those bytes were used. The workload's current loopback restriction must
   remain until a separate, specifically reviewed target design is implemented.
5. Capture raw metrics into a new run-specific location. Preserve raw output;
   write derived reports or corrections as separate new files. Record sanitized
   run ID, configuration, revisions, migration head, dataset/profile hashes,
   timing, telemetry and cost references in the capture manifest. Avoid response
   bodies, embeddings, provider error bodies, request secrets and private data.
   Existing artifact validation checks hashes, not authenticity or privacy.
6. Record failures and incomplete runs rather than silently retrying or treating
   them as valid. Compare results only after correctness, delivery, timing,
   resource, parity, telemetry, cost and owner-review gates are met.

Implementation requires synthetic fixtures and local doubles for refusal before
session/workload, wrong target, changed files, expired session, errors, timeouts,
shortfalls, immutable output and privacy. Those checks do not establish actual
running capacity, provider behavior, timing validity or permission to measure.

## Open decisions and owner inputs

1. **Synthetic regular-account access:** Identity owner and experiment owner
   must confirm how an authorized synthetic regular account and session can be
   established without real users, the isolated demo identity or bypassing
   Identity protections. The presence of synthetic dataset rows does not prove
   they have login identities or usable credentials. Temporary-account login is
   a different path and is not silently substituted for the regular account.
2. **Session handoff:** The user selected an environment variable for the test
   session. `CLIP_COMPARISON_SESSION_COOKIE` is the proposed future runner
   variable; the local helper checks its shape only after local preflight. The
   real runner is not wired to it. Identity/security and runner owners must
   review process isolation, environment exposure, expiry, rotation and cleanup
   before use. Keep the session out of CLI flags, files, logs and reports; the
   local smoke runner's separate variable is not a production access method.
3. **Target and authorization:** Infrastructure/experiment owners must define
   the exact allowed target identity, TLS/routing verification, authorization
   artifact and fail-closed checks. Account, region and deployed revision must
   come from the later reviewed run plan, not guessed endpoints.
4. **Checked-byte handoff and output:** Runner and experiment owners must choose
   how to bind the checked profile and executable bytes to actual use, and how
   to protect per-run evidence location and raw-file immutability. Decide how to
   reconcile partial output and preserve failed runs without retaining secrets.
5. **Timing and capacity:** The user prefers built-in k6 phases; the existing
   design's monotonic requirement remains pending affected-owner review. Select
   the timing protocol and generator/session limits before a real run. No 300
   concurrent-request proposal is binding.

These are pre-implementation or pre-run gates as applicable. Identity owner A,
EXP-02 owner D, Search reviewer C and infrastructure owner B coordinate their
respective areas;
independent human review remains required. No owner approval is recorded here.
