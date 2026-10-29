# Wanted-response backend correction — review plan

**Status:** Mohit verified this exact correction plan; isolated implementation and
checks passed. Result verification and actual provider integration remain pending.
**Origin:** SE-02 Step6 coverage audit; consumes the already reviewed Search →
Conversations request-response interface before Step7's Contact requester UI.

## Original gaps (corrected locally)

- Search declared `POST /wanted-requests/{request_id}/conversations`, operation
  `search_start_wanted_response`, but the actual Search router did not mount it.
  Functional response capability, close/create race and retired-response tests
  were incomplete at audit time.
- `contracts/combined.md` and `contracts/search.md` describe a
  `ConversationStartResult` on201/200, allowing a client to navigate an existing
  thread after retry. `contracts/source/search.py` originally set the alternate200 response
  to `None`; generated OpenAPI200 had only a description and no body. Those generated
  consumers could not obtain the existing thread ID through that declaration.

## Proposed correction, in order

1. Change only Search's alternate200 declaration to `ConversationStartResult`,
   preserving path, input, primary201 model and existing capability/privacy rules.
   Regenerate registered outputs and check generated TypeScript consumers. This
   is a pre-implementation correction to the documented response, recorded at the
   current contract version; no implemented endpoint/accepted live behavior is
   being changed. Generated consumers must use the corrected result type before
   the Step7 connection. Keep other domains' declarations outside this patch;
   independent/affected-owner review remains required for the normal handoff.
2. Add the Search service/handler and a short Search-owned origin-lock context.
   Validate current trusted caller; temporary callers cannot initiate or look up
   a response through this operation. Regular callers require live eligibility.
   Derive author from the locked request, never from a client field. Reject self
   response. Missing, retired or pending requests fail with safe404 and call no
   create operation. Existing owner edits/reopen keep their reviewed behavior.
3. For an open request, hold its row lock while calling the bounded public
   `open_or_create_wanted_conversation(caller, WantedConversationContext)`.
   Search shares no DB session; Conversations owns its transaction, eligibility,
   distinct participants and unique `(request_id,responder_id)` thread.
   Return201 for created and200 for existing, both with the validated result.
4. For an unavailable request, call only
   `find_existing_wanted_conversation(caller, ExistingWantedConversationLookup)`
   for that actor/request pair. Return its existing thread as200; a missing pair
   is safe404. Never create a thread after closure. A claimed created=true from
   this read-only lookup is an invalid dependency result (503).
5. Dependency unavailability/timeout yields safe503. An ambiguous create may have
   committed remotely: retry the same request/responder pair. If closure happened
   meanwhile, use only the read-only existing-pair operation. No fabricated
   thread ID, automatic write retry or competing local thread/receipt storage.
   The validated operation UUID remains the HTTP field; existing public
   Conversations arguments have no operation-ID field, so use their reviewed
   pair-uniqueness semantics rather than inventing an input.
6. Add isolated regular/temporary/expired/revoked/self/missing/unavailable/pending/
   retired cases, created/existing/closed retries, malformed results and lost
   responses. Real PostgreSQL row locks must prove close-first prevents creation
   and response-first serializes closure, using an explicit public Conversations
   double rather than a fake SQL/thread implementation. Re-run Step6 coverage,
   actual schema/consumer generation, boundaries and relevant full checks.

## Scope and gates

Expected owned changes: wanted service/route/store lock helper and their tests;
Search contract source/generated response correction and shared installed-schema
assertions. No migration, UI, scheduler, deployment, cloud action, push or merge.
The handler defaults to the real public Conversations declaration and fails
closed until its provider is available. Test-only successes do not become a
browser fixture fallback. Actual C eligibility/thread-membership/unique-thread/
close-retirement integration remains Step8/INT-01; UI work follows at Step7.

## Implemented verification

The approved200 model is generated and consumed by a strict TypeScript sample.
`wanted_response.py` implements regular-only capability/state checks and public
C calls; the route returns typed201/200 bodies. `wanted_store.response_guard`
uses FOR NO KEY UPDATE to serialize owner writes while allowing a separate
transaction to check its thread FK. Normal defaults remain real public providers,
with no fake success. No schema/resource change was required.

Unit and actual Search/PostgreSQL HTTP checks cover all listed local cases,
including lost response followed by closure/read-only lookup, closed-first and
response-first order, and actual server-observed owner lock waiting. A separate
C schema-only thread/member fixture commits under the guard to verify FK lock
compatibility; it does not implement or accept real C service behavior.
The detailed receipt is in Git history; see the
[evaluation retrieval guidance](../evaluation/README.md). Human result
verification remains; Step6 real provider checks remain Step8/INT-01 obligations.
