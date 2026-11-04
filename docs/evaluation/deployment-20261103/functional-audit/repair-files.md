# Repair file guide

This guide names changed code/configuration files and their purpose. See local-validation.json for results.

- `apps/api/app/application.py` — Compose bounded pools, use null pools on Lambda, and close Identity after requests/workers finish.
- `apps/api/app/contracts/domain_types.py` — Re-export the generated batch request/response models for domain routes; no handwritten contract copy.
- `apps/api/app/core/database.py` — Bound Conversations to two connections/task and32queued borrowers.
- `apps/api/app/domains/conversations/notifications/runtime.py` — Enable intended eligible-recipient delivery in the explicit hosted real app; preserve notification policy.
- `apps/api/app/domains/identity/capabilities.py` — Accept an exclusive pooled connection lease for current-account capability queries; authorization SQL is unchanged.
- `apps/api/app/domains/identity/cleanup.py` — Accept the same connection context interface for bounded cleanup transactions; retirement rules are unchanged.
- `apps/api/app/domains/identity/contacts.py` — Use the connection-lease type for private contacts and notification destination access; ownership and encryption remain.
- `apps/api/app/domains/identity/email.py` — Permit canonical general recipients in the explicit hosted Identity runtime while preserving standalone test restrictions and bounded sends.
- `apps/api/app/domains/identity/email_configuration.py` — Pass the hosted recipient policy consistently to the existing primary/fallback providers.
- `apps/api/app/domains/identity/http.py` — Expose an optional owned-pool close hook on Identity dependencies for application shutdown.
- `apps/api/app/domains/identity/resend_email.py` — Match SES recipient policy in the existing Resend fallback while preserving validation and send bounds.
- `apps/api/app/domains/identity/runtime_configuration.py` — Keep real startup validation, then share a four-connection ECS Identity pool or one-connection Lambda null pool; wire closure and hosted mail policy.
- `apps/api/app/domains/identity/runtime_database.py` — Implement bounded Identity leases, finite waiting/timeouts and explicit shutdown using the existing role/TLS/target guard.
- `apps/api/app/domains/identity/sessions.py` — Change the connection type to accept exclusive leases; session authentication, renewal, expiry and revocation SQL are unchanged.
- `apps/api/app/domains/identity/temporary_accounts.py` — Accept pooled leases for temporary-account lifecycle transactions without changing activation or expiry rules.
- `apps/api/app/domains/identity/temporary_challenges.py` — Accept pooled leases for challenge transactions without changing OTP verification, limits or key handling.
- `apps/api/app/domains/listings/postgres_store.py` — Bounded batch photo route/service and one-snapshot SQL lookup; Hybrid read pool lifecycle; generated public imports.
- `apps/api/app/domains/listings/public.py` — Bounded batch photo route/service and one-snapshot SQL lookup; Hybrid read pool lifecycle; generated public imports.
- `apps/api/app/domains/listings/routes.py` — Bounded batch photo route/service and one-snapshot SQL lookup; Hybrid read pool lifecycle; generated public imports.
- `apps/api/app/domains/listings/search_runtime.py` — Bounded batch photo route/service and one-snapshot SQL lookup; Hybrid read pool lifecycle; generated public imports.
- `apps/api/app/domains/listings/service.py` — Bounded batch photo route/service and one-snapshot SQL lookup; Hybrid read pool lifecycle; generated public imports.
- `apps/api/app/domains/search/public.py` — Private batch saved-state route/service/SQL without loading the whole Saved collection; generated public imports.
- `apps/api/app/domains/search/saved.py` — Private batch saved-state route/service/SQL without loading the whole Saved collection; generated public imports.
- `apps/api/app/domains/search/saved_routes.py` — Private batch saved-state route/service/SQL without loading the whole Saved collection; generated public imports.
- `apps/api/app/domains/search/saved_store.py` — Private batch saved-state route/service/SQL without loading the whole Saved collection; generated public imports.
- `apps/api/tests/domains/identity/test_email.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/api/tests/domains/identity/test_runtime_configuration.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/api/tests/domains/listings/test_postgres_store.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/api/tests/domains/search/test_saved.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/api/tests/domains/search/test_saved_postgres.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/api/tests/test_database_lifespan.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/api/tests/test_lambda_identity.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/api/tests/test_lambda_read_app.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/web/src/features/listings/ListingImagePreview.tsx` — Coalesce page requests, validate responses and cancellation, and bound photo-link refresh; no cross-navigation private cache.
- `apps/web/src/features/listings/listingsApi.ts` — Coalesce page requests, validate responses and cancellation, and bound photo-link refresh; no cross-navigation private cache.
- `apps/web/src/features/search/wantedApi.ts` — Coalesce page requests, validate responses and cancellation, and bound photo-link refresh; no cross-navigation private cache.
- `apps/web/tests/saved-membership.test.ts` — Focused regressions and updated explicit pool/endpoint expectations.
- `contracts/generated/openapi.json` — Canonical additive batch models/operations and generated TypeScript/OpenAPI; existing listing payloads retained.
- `contracts/generated/types.gen.ts` — Canonical additive batch models/operations and generated TypeScript/OpenAPI; existing listing payloads retained.
- `contracts/source/listings.py` — Canonical additive batch models/operations and generated TypeScript/OpenAPI; existing listing payloads retained.
- `contracts/source/search.py` — Canonical additive batch models/operations and generated TypeScript/OpenAPI; existing listing payloads retained.
- `contracts/source/types.py` — Canonical additive batch models/operations and generated TypeScript/OpenAPI; existing listing payloads retained.
- `tests/contracts/test_domain_declarations.py` — Verification or contract-inventory expectations.
- `tests/contracts/test_generation.py` — Verification or contract-inventory expectations.
- `apps/api/tests/domains/listings/test_image_delivery_batch.py` — Focused regressions and updated explicit pool/endpoint expectations.
- `apps/web/src/shared/http/batchedRead.ts` — Coalesce page requests, validate responses and cancellation, and bound photo-link refresh; no cross-navigation private cache.
- `apps/web/tests/image-delivery-batch.test.ts` — Focused regressions and updated explicit pool/endpoint expectations.

Follow-up files:

- `apps/api/tests/domains/listings/test_embedding_worker_postgres.py` — Reproduce missing worker rights with a real restricted role in the guarded disposable database, then verify claim/publication with the proposed columns. It refuses retained/remote targets.
- `database/roles/marketplace-embedding-worker.sql.proposed` — Canonical proposed narrow worker grants, byte-identical to the separately gated deployment SQL; nothing applies this automatically.
- `scripts/evaluation/build_lambda_image.sh` — Disable provenance/SBOM attestations for the runnable single-platform Lambda image root; retain cached inputs, source labels and no-network build.
- `tests/evaluation/test_lambda_image_builder.py` — Check those build flags with the existing fake Docker harness.
- `scripts/marketplace_inspection.py` — Extend the integrated disposable-app inspection to both new HTTP/SQL batches, missing/removed image isolation, actual image bytes and no-store policy.
- `apps/web/src/features/listings/listingsApi.ts` — Follow-up permits same-origin HTTP only on a loopback HTTP preview page; public hosted links still require HTTPS.
- `apps/web/tests/image-delivery-batch.test.ts` — Verify the loopback exception and rejection of public HTTP links alongside existing batching/expiry tests.

`docs/decisions/identity-email-routing.md`, `docs/decisions/notification-delivery-policy.md`
and `docs/environment/identity-provider-setup.md` link the superseding explicit
hosted mail policy so old staged test restrictions are not presented as current.

The final `listingsApi.ts` follow-up observes the same-origin response Date header
for link-expiry checks, avoiding failures caused by a fast/slow client clock while
retaining URL/expiry validation. `image-delivery-batch.test.ts` reproduces both
clock directions and restores the clock mock after each test. API payloads and
monotonic experiment timing are unaffected.

## Lunch batch: search and experiment alignment

- `pyproject.toml`, `uv.lock` — Pin NumPy2.5.4 in the API environment. The separate pinned model interpreter remains unchanged.
- `apps/api/Dockerfile` — Keep numerical-library threads at one per process, so application concurrency does not multiply hidden CPU threads.
- `apps/api/app/domains/listings/hybrid_read.py` — Keep the validated source/filter/coverage SQL, exact inline SQL diagnostic scorer, one query norm and page-aware lexical-tier pruning; model encoding can precede the DB lease.
- `apps/api/app/domains/listings/hybrid_snapshot.py` — Read fresh candidates plus missing binary vectors, bound an immutable generation cache, precompute stored norms, score with ordered double arithmetic and retain original ordering/pagination.
- `apps/api/app/domains/listings/postgres_store.py` — Wire the same snapshot/scorer into ECS and Lambda; return the DB lease before CPU work and bound pending requests/workers through cancellation.
- `apps/api/app/domains/listings/embedding_client.py` — Reuse bounded exact-text/model query vectors, with monotonic expiry and helper lifecycle/fork guards; cache no authorization or pages.
- `apps/api/tests/domains/listings/hybrid_reference.py` — Preserve original SQL as an independent test/diagnostic oracle; production imports none of this file.
- `apps/api/tests/domains/listings/test_hybrid_read.py`, `test_hybrid_snapshot.py`, `test_hybrid_read_postgres.py`, `test_embedding_client.py` — Check exact SQL equivalence, pages/filters/coverage/edits, cache bounds/expiry, inference/lease order and cancellation/lifecycle behavior.
- `apps/api/tests/domains/identity/postgres_fixtures.py` — Add explicit owned-container CPU/memory/connection limits for diagnostics; ordinary fixture defaults stay intact.
- `scripts/evaluation/search_local_profile.py` — Preserve the explicitly isolated original-versus-optimised SQL diagnostic, separate from the new full API capacity runs.
- `scripts/evaluation/capacity_local.py`, `capacity_local_worker.py` — Exercise real session/domain SQL/model paths in owned limited local containers; run required profiles, retain raw output/resource metrics and remove only owned resources. The worker is UDS-only and is never a deployment entry point.
- `scripts/evaluation/frozen_reference.py` — Verify/read the published accepted archive, paired fingerprints and unchanged judgments without regenerating historical inputs against new API contracts.
- `scripts/evaluation/nfr04_retrieval.py` — Use that frozen consumer; preserve current-target/revision and execution gates. The legacy image-root option is optional because archive photos are verified directly.
- `scripts/evaluation/k6/nfr03_schedule.js`, `nfr03_schedule.test.mjs` — Define/check the deterministic well-spread original100-operation mix shared by A/B.
- `scripts/evaluation/k6/nfr03_checks.js`, `nfr03_checks.test.mjs` — Validate Wanted page fields/uniqueness/order while controlled new writes displace older rows.
- `scripts/evaluation/k6/nfr03_load.js` — Use that schedule, check the designated Wanted fixture before measurement and preserve write IDs/reconciliation.
- `scripts/evaluation/k6/nfr03_profile_builder.py` — Document that the coordinator binds the frozen schedule with the profile.
- `scripts/evaluation/k6/nfr03_report.py`, `tests/evaluation/test_nfr_reports.py` — Account for the separate preflight request and retain strict mixed-route/write accounting.
- `scripts/evaluation/k6/core.js`, `core.test.mjs` — Compute the exact fixed arrival budget, including fractional-rate conditions.
- `scripts/evaluation/k6/comparison_load.js`, `exp05_pilot_load.js`, `nfr_load.js`, `nfr03_load.js` — Send exactly the frozen number of HTTP operations; retain surplus boundary executions separately without hiding failed/short/dropped traffic.
- `scripts/evaluation/k6/real_run_coordinator.py`, `tests/evaluation/test_workload_import_closure.py` — Stage transitive helpers and reject incomplete static import bundles before session access/execution.
- `data/generators/reference_login.py` — Expose the existing private CLI-login credential-refresh bridge with the explicit named-profile factory signature.
- `scripts/evaluation/k6/real_target_preflight.py`, `cloudwatch_capture.py`, `lambda_initialization.py`, `scripts/evaluation/nfr06_recovery.py`, `nfr07_restore_observer.py` — Use the existing login bridge consistently; restore derives its profile from the hash-bound source plan and rejects mismatches. Exact task-stop/restore approvals remain mandatory.
- `tests/evaluation/test_frozen_reference.py` — Verify accepted inputs load without regeneration and changed judgments are rejected.
- `docs/evaluation/deployment-20261103/public-input-overlay.json` — Record the approved1024CPU-unit ECS task allocation for a future reviewed deployment; no live change is applied.

## Invocation reuse and short local precommit diagnostics

- `apps/api/app/domains/identity/runtime_database.py` — Add an invocation-owned exclusive Identity connection. Separate session/account transactions share it; cleanup waits for active borrowers and physically closes it through cancellation. ECS keeps its existing pool.
- `apps/api/app/domains/identity/http.py` — Install the optional invocation scope around read-only Identity middleware; delay the terminal body until connection cleanup finishes. Preserve response content and normal authorization.
- `apps/api/app/domains/identity/runtime_configuration.py` — Wire that scope only into Lambda's one-connection null pool.
- `apps/api/tests/domains/identity/test_runtime_configuration.py`, `test_invocation_response.py` — Verify backend reuse across thread helpers, closure between requests, rollback/revocation/cancellation and response-before-cleanup ordering.
- `apps/api/tests/domains/listings/test_search_modes.py` — Update the fake ports to the new snapshot/scorer interface; preserve mode/filter normalization and rejection checks.
- `scripts/evaluation/k6/local_capacity_window.js`, `local_capacity_window.test.mjs` — Opt into10/60second diagnostic windows only after normal local target/profile validation; reject the flag on real targets. Formal inputs are unchanged.
- `scripts/evaluation/k6/exp05_pilot_load.js`, `nfr_load.js`, `nfr03_load.js` — Use that optional local window for scenarios and exact request/write-reconciliation budgets; normal deployed timing stays fixed.
- `scripts/evaluation/k6/nfr_report.py`, `nfr03_report.py`, `tests/evaluation/test_nfr_reports.py` — Add an explicit library-only diagnostic mode with exact shortened accounting; default formal parsers reject shortened profiles and no report accepts an NFR.
- `scripts/evaluation/k6/nfr_load.test.mjs` — Exercise the actual entry point despite k6 rewriting exported options, and preserve latency-versus-ranking separation.
- `scripts/evaluation/k6/real_run_coordinator.py` — Include the helper in staged import closure; its deployed environment never enables short mode.
- `scripts/evaluation/capacity_local.py`, `capacity_local_worker.py` — Add the short release sequence, immutable source versus runtime timing profiles, and invocation-scope wiring; retain failed raw results and stop incomplete delivery.
- `apps/api/app/domains/listings/hybrid_snapshot.py` — Final strict-type cleanup adds explicit clock/vector/index types and rejects missing Hybrid query text. Valid query arithmetic and ordering are unchanged.

## Shared proxy follow-up after fallback commit 6193ca7

- `apps/api/app/core/database_transport.py` — Resolve the explicit proxy host while preserving each role, password, database and TLS setting. Remove unsupported startup options only for proxy connections, disable automatic prepared statements, and verify bounded server deadlines without retaining a transaction.
- `apps/api/app/core/config.py` — Validate the nonsecret endpoint override, provide the common DSN routing method and reject source-proxy inheritance during an isolated restore.
- `apps/api/app/application.py` — Route Listings and Conversations through the common override; retain bounded pools and check stale proxy connections before checkout.
- `apps/api/app/core/database.py` — Apply the same proxy connection rules to the Conversations pool used by chat and notifications.
- `apps/api/app/domains/identity/runtime_configuration.py` — Route both full ECS Identity and read-only Lambda Identity through the same setting after reading their existing SSM source.
- `apps/api/app/domains/identity/runtime_database.py` — Apply proxy compatibility, deadline checks and stale-client replacement to startup and pooled Identity connections without changing authentication queries.
- `apps/api/app/domains/listings/search_runtime.py` — Route Hybrid retrieval through the same proxy and pass the selected DSN to its worker, retaining the release-before-scoring behavior.
- `apps/api/app/domains/listings/embedding_dispatch.py` — Apply the same compatibility and checkout checks to the bounded embedding worker pool.
- `infra/terraform/shared/test/database-proxy.tf` — Define opt-in private proxy, role-separated credential copies using ephemeral/write-only inputs, exact-secret IAM, private network rules and bounded backend settings. Provisioning and application routing are separate switches.
- `infra/terraform/shared/test/network.tf` — Permit only the proxy security group to reach the existing database on port 5432 while retaining direct rules for rollback.
- `infra/terraform/shared/test/service.tf` and `exp03-lambda.tf` — Put the same nonsecret endpoint override in ECS and Lambda only when explicitly activated.
- `infra/terraform/shared/test/tests/database_proxy.tftest.hcl` — Verify disabled defaults, provisioning without activation, TLS/bounds and required Identity configuration using mocks.
- `infra/terraform/shared/test/tests/exp03_lambda.tftest.hcl` — Supply synthetic ephemeral inputs required by the mock Terraform lifecycle; no live secrets or resources.
- `scripts/evaluation/database_proxy_credentials.py` — Prepare read-only metadata bindings to exact source versions, then privately resolve matching existing credentials for ephemeral Terraform inputs. Reject changed sources, mismatched account or expired plans; never applies resources.
- `scripts/evaluation/k6/real_target_preflight.py` — Bind new target-plan versions to one healthy proxy and its exact RDS target, require matching ECS/Lambda overrides and reject hidden proxy routing in direct plans. Continue accepting historical direct plans.
- `scripts/evaluation/k6/cloudwatch_capture.py` — Preserve proxy connection, borrowing, pinning, setup-failure and capacity metrics alongside existing runtime/database evidence; retain missing data explicitly.
- `scripts/evaluation/nfr07_restore_observer.py` — Refuse restore applications still pointing to the source proxy.
- `scripts/evaluation/k6/exp05_pilot.py` — Generate the authorized six-run baseline/full-Lambda pilot and require every declared result; historical 15-run plans remain readable.
- `scripts/evaluation/capacity_local.py` — Add an explicit ECS-only short fallback diagnostic, with truthful configuration metadata and no claim to emulate managed proxy capacity.
- `data/evaluation/workloads/exp05-target-bindings.template.json` — Match the six current pilot target bindings.
- `data/evaluation/workloads/real-target-plan.template.json` — Declare version 2 and an explicit optional proxy binding.
- `apps/api/tests/test_database_transport.py` — Check role/TLS preservation, invalid overrides, restore isolation, bounded defaults and clean transaction state.
- `tests/evaluation/test_database_proxy_credentials.py` — Verify read-only preparation, private handoff, version/digest drift rejection, redacted errors and non-overwriting private output.
- `tests/evaluation/test_database_proxy_preflight.py` — Reject mismatched runtime endpoints, wrong/unhealthy databases, weakened proxy settings and incomplete pilot evidence.
- `tests/evaluation/test_cloudwatch_capture.py` — Verify metrics use the selected proxy and aggregate connection counts across its nodes.

The command index, k6 guide, canonical experiment task list, deployment plan,
connection budget and shared-pool plan explain operation, evidence boundaries and
rollback. No new API response, schema, ranking, authorization or workload-rate
change is introduced by this follow-up. The current pilot candidate count changes
by Suraj's explicit instruction; NFR thresholds remain unchanged.

The final broad suite also required fixture updates: `test_database_lifespan.py`
and `test_lambda_read_app.py` now expect the explicit configure/check callbacks
while still asserting every existing pool bound; `domains/listings/test_embedding_dispatch.py`
uses a syntactically valid unused DSN so it reaches the intended mocked startup,
shutdown and cancellation failures. These tests still open no external connection.
