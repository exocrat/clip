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
