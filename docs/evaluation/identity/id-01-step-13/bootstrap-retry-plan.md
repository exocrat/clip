# ID-01 Step13 — corrected bootstrap retry candidate

The first approved attempt stopped at `actual_login_before` with OperationalError;
bootstrap/reset was never called. No database record/schema/grant/credential changed.
[Safe execution receipt](bootstrap-attempt-result.json). No automatic retry ran.

A disposable real PostgreSQL login reproduces a defect in the private caller:
application roles cannot set log_statement at connection startup. Correct only
those two login calls: omit privileged logging overrides, then verify inherited
privacy settings after TLS login. Keep the administrator connection and every
reset/source/count/version/grant gate unchanged. The original live failure was
sanitized to class only, so this is a confirmed defect, not proof of sole cause.

Proposed fresh retry uses the same exact account/profile/Mumbai RDS/one private
Micro, reset closure, unchanged23SQL, pinned migration image, grant allowlist,
preservation and failure/cleanup behavior in [the reviewed plan](bootstrap-live-review.md).
Start only from verified stopped/zero state with a fresh60minute/$1 window,
20minute startup limit,40minute stop-new-work boundary and owned timed fallback.
Read each of the same three fixed SSM references once, memory only; preserve
versions1. API/proxy remain off; no provider/auth-key/SSM/password/S3 changes.
Before reset require both existing-role TLS logins and exact prior catalog/count/
version fingerprints. After reset/migration/grants require unchanged-role logins
and allow/deny checks. No retry after any failure; preserve committed state and
clean up. This candidate is not execution approval.

The corrected private caller is retained with the first attempt; its source hash
will bind the fresh approved snapshot. The shared coordinator, runner and SQL do
not change. `tests/test_identity_bootstrap.py` now covers real restricted-role
startup rejection plus successful inherited privacy defaults for both roles.
Full local13-case rehearsal result is recorded after completion in the work log.

Pending: human verification of failure/correction and explicit fresh retry-window
approval. Required review confirmation for the unchanged reset/grant package is
retained; no independent reviewer identity has been invented.

Corrected private caller SHA256: `f64294a21c3810449ae4c399a340a7be38b6399a50096288b0d30d3d1ed4c06a`.
Known connection failures get a fixed safe category; raw server errors and
credential values remain unpersisted. Local complete rehearsal:13passed.
