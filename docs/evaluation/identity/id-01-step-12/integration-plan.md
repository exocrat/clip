# ID-01 Step12 — current-main reconciliation and runtime integration plan

Prepared2026-10-24 13:36:09 UTC by Aditya(A)'s execution agent on
`task/id-01-identity`, source `29ab71a`. Aditya verified the Step12 understanding.
This is a concrete integration proposal; neither a merge nor live enablement has run.

## Audit and dependencies

No material omission in canonical ID-01 Steps1–15 or the ID-READY boundary was
found. Steps1/3 and local implementations4–11 are human-verified. Step2's SES
production-access/configuration transition remains pending; existing sandbox
inbox/task-role evidence does not establish general production delivery.
The stub guide permits isolated Steps1–11 but requires real configuration/safety
and usable actual interfaces for Step12. Keep ID-01/ID-READY incomplete.

At this checkpoint GitHub API confirmed current main
`defec38f59d4acb683f7b51950860f458aacfdd1`; PR10 is MERGED, merge time
2026-10-23T10:55:14Z, reviewed-source head
`23028365c2a981d8cc2656ce97d237553b325e0d`. Existing local origin/main matches.
Shared ancestor is `44cd8ffbf5b518520824d88ee0c812568fe9ef01`.
The ordinary SSH query failed on local system SSH-config permissions; sandboxed
GitHub API initially had no network access. Approved read-only API execution
succeeded. No SSH configuration or remote state was changed.

The branch's normal `app.main` is health-only. Actual Identity HTTP/session/SQL
services are explicitly composable, but only the synthetic loopback runner
assembles them today. Normal web mode lacks Identity API proxy wiring.
Production settings explicitly reject Microsoft and SES. Current main already
contains Listings lifespan/pool/router/storage, an isolated fixed caller, optional
same-origin hosted SPA and `/api` proxy behavior. Reconcile these first, preserving
its accepted behavior and ensuring isolated callers can never authorize real
Identity sessions. Replacing main with an Identity-only app would lose Listings.

No standalone profile editor is required by approved Step11/P11: own display-name
updates are an existing API output; the approved page is the contact editor.
Actual CN-02 participant/confirmed-field/encryption checks remain with CN-02.
Step14 full consumer matrix is outside this ID-READY scope.

## Local merge proposal — requires separate approval

Target: merge the exact main revision above into `task/id-01-identity` with
`git merge --no-commit --no-ff <revision>`, retaining an inspectable result before
any merge commit. This neither merges a PR to main nor publishes anything.
Aditya is proposed current writer for bounded shared reconciliation; affected
owners retain independent review. Recheck remote main immediately before action;
if it changes, report the new target rather than silently widening approval.

Read-only traditional merge-tree found textual conflicts in these13paths:

| Paths | Resolution intent and required evidence |
| --- | --- |
| `apps/api/app/core/config.py` | Combine accepted Listings database/S3/isolated controls with Identity selectors and sandbox safety. Retain production fake rejection and Identity real-provider refusal until reviewed runtime wiring. Test both domains' accepted configuration matrices. |
| `apps/web/vite.config.ts` | Preserve normal Listings `/api` proxy/rewrite and loopback/strict ports; preserve synthetic Identity preview's fixed routes and build refusal. Do not expose the synthetic mailbox in normal mode. |
| `pyproject.toml`, `uv.lock` | Keep both domains' direct pinned dependencies and test configuration; regenerate the lock with the pinned resolver, inspect changed existing versions and require justified changes. |
| `scripts/check_database.py`, `database/tests/native-checks.sh` | Preserve both complete migration histories and both domains' checks; test clean/repeat and actual forward/rollback/reapply from accepted main and prior Identity heads, plus failure atomicity. Native source/syntax is not a native runtime pass. |
| `tests/contracts/test_generation.py` | Keep Identity's reviewed runtime-dispatch metadata tests and Listings source changes. Regenerate artifacts from combined canonical editable sources; never choose an old generated side wholesale. |
| `apps/api/README.md`, `apps/web/README.md`, `database/README.md`, `docs/architecture/mvp-database-schema.md`, `docs/environment/commands.md` | Combine actual commands, schema, security and isolated/live distinctions; remove conflicting current-state claims while preserving meaningful historical evidence. |
| `docs/status/work-log.md` | Preserve other owners' statuses and append-only substantive history; retain ID-01 actual pending gates and exact timestamps. |

The first merge-tree inspection failed decoding an upstream binary image as UTF-8;
rerun treated binary bytes safely and completed. No index/worktree merge occurred.
Textual conflict detection does not prove semantic compatibility. Audit all merged
contracts/generated outputs, API main/lifespan, UI shared composition, Docker build,
boundary rules, dependency manifests and migration triggers even where Git reports
no textual conflict. Do not alter Listings private business behavior to make an
Identity test pass; coordinate any such finding with Suraj(B).

## Runtime work after reconciliation

1. Refactor shared composition only as needed to retain one app/lifespan, Listings
   routers and Identity middleware/routes. Derive callers from actual sessions;
   preserve no-store, exact Origin/CSRF, expiry/revocation and request-scoped public
   dispatch. Unconfigured startup remains safe; incomplete enabled configuration
   fails startup with bounded redacted errors, with no fake fallback.
2. Supply three independent persistent256-bit TemporaryKeys with an explicit stable
   version. Never regenerate on startup: lookup/enrollment/request commitments must
   survive restarts. Use reviewed SSM SecureString references and scoped execution
   permissions through existing project mechanisms, not chat/repo/plaintext secrets.
   Exact new paths/permissions are a further reviewable proposal before provisioning.
3. Use an explicitly approved application DB login with reviewed Identity-table
   grants and TLS. Existing foundation `clip_test_probe` is CONNECT-only and cannot
   serve auth queries; do not use the master role as an application shortcut.
   Prove grants/rejections against disposable SQL before any separately approved
   shared role/schema application. Do not start/stop/change Suraj's database.
4. Resolve TLS and trusted proxy/source handling before a hosted flow. Identity
   currently rejects non-HTTPS outside explicit loopback and uses transport peer IP,
   deliberately ignoring forwarded headers. Do not trust arbitrary X-Forwarded-For
   or scheme headers, or collapse all source throttling onto an ALB peer. Review the
   actual proxy chain, network boundary, hop count/address parsing and spoof tests.
5. Align browser Identity paths with accepted same-origin hosting without rewriting
   the SPA `/auth/callback` into an API request. Keep normal and synthetic modes
   distinct. Retain registered localhost/site callbacks and default-disabled MSAL.
6. Test actual Microsoft start/redirect/PKCE/state/nonce/cookie/session, denial and
   replay behavior on a separately approved real provider path. Inspect actual SDK
   consent and cache artifacts/cleanup. Controlled SDK tests establish no live pass.
   Test temporary registration/resend/login/reset/logout/contact flows with a
   separately approved controlled SES recipient; redact values and never auto-retry
   an uncertain send except for the subsequently approved one-attempt alternate
   provider described below. Active Resend readiness may proceed after real setup;
   general SES use remains behind its Step2 production transition.
7. Record actual desktop/phone observations. Keep missing real-device checks pending.
   No new page/route is implied by this wiring plan.

## Checks, handoff and gates

Run locked setup and the combined full local gate after the merge/runtime changes:
Black; all unit/integration/UI/boundary/contract checks; generation freshness;
actual disposable migration clean/repeat/upgrade/down/reapply; type/build;
configuration/fake-activation/provider failure/privacy/source spoofing tests; secret
scan and local links/whitespace. Current-branch checks cannot establish the combined
main chain. Record failures and exact source revisions; no test-only mailbox in
production image/bundle. Keep native/device claims distinct from local ARM64 tests.

Then prepare an ID-READY PR only when its required actual checks pass. Arrange
independent Rahul(D)/affected-owner review with the
[peer-review prompt](../../../prompts/peer-review-prompt.md). Hosted CI must cover
the current head/base. Peer approval, push, exact-revision merge, cloud/provider
verification, deployment, live sends and cleanup each retain their own gates.
Step13 requires its exact account/region/source/identity/time/spend/rollback plan.
No Step14/FR03/full ID-01 acceptance is inferred.

## Baseline result — 2026-10-24 13:38:19 UTC

`make check` on `29ab71a` exited0; all11gates passed:771 Python tests
(159.82seconds),63data tests,92web tests, Black118files, boundaries, generated
contract freshness/types, web lint/type/build,35wrapper safety cases, actual
PostgreSQL18.6 migrations/five smokes/Identity upgrade atomicity and preserving
upgrade/down/reapply, and Gitleaks8.30.1 source snapshot. Raw local output:
`/tmp/clip-id12-audit-check.log`. This is the pre-reconciliation Identity branch,
not evidence of combined-main or real-provider readiness. No code/configuration,
shared database, cloud, provider, push or merge action was performed.

Immediate gate: Aditya verifies this audit and separately authorizes the exact
local merge proposal above, without a commit. Preserve this uncommitted plan/log
before starting the merge; do not discard or autostash other owners' work. A later
commit requires its own explicit approval after the resolved diff/checks.

## Subsequent approved email preparation

Aditya selected Resend initially and SES later, with14400second runtime refresh
and one alternate-provider attempt even on timeout. See the [canonical decision](../../../decisions/identity-email-routing.md).
Private local adapter/router/SSM-loader implementation may proceed without changing
shared main/config/Vite composition or performing the pending merge. It preserves
existing SES sandbox guards. Both-provider general runtime wiring/live checks
remain pending after reconciliation and exact setup approvals.
