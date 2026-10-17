# Campus Marketplace — Shared Conventions and Cross-Domain Contract Rules

**Canonical repository path:** `docs/conventions/shared-conventions-and-cross-domain-contract-rules.md`
**Document 3. Status:** Shared baseline for repository and contract work. It records rules already present in the submitted PRD and project plan, plus the PD-06 shared choices approved on 2026-10-17. These definitions precede their implementation; PD-06 steps 3–6 remain required. It does not define the four domain APIs; those belong in the domain contract documents and the combined contract.

## 1. Purpose and precedence

Use this document to keep Identity, Listings, Search, and Conversations consistent. The submitted `ICC_Project_PRD_FINAL.pdf` sets product requirements. Document 1, `product-reference-and-architecture-decisions.md`, records the interpreted product and architecture baseline. This document defines cross-domain conventions. The four domain contracts define the actual operations, inputs, outputs, authorization, side effects, and errors.

If these sources conflict or leave behavior uncertain, do not silently choose an interpretation. Find the relevant contract/task, inspect the current repository, and ask the human to resolve the uncertainty before dependent implementation. Record the answer in its canonical repository location so later agents can read it there.

## 2. Shared data conventions

These conventions apply to data crossing domain or API boundaries. A domain contract may add field-specific rules, but it may not contradict them without a reviewed shared change.

| Concern | Shared rule | Contract must state |
|---|---|---|
| Identifiers | Use UUID identifiers. Expose identifiers as strings at API/domain boundaries. Treat IDs as opaque: callers must not parse meaning from their contents. | Which entity is identified; whether the ID is required or nullable; who creates it; and whether callers may supply it. |
| Time | Use UTC-aware instants in shared core logic. Serialize instants using one repository-wide ISO 8601/RFC 3339 UTC representation. Never interpret a timezone-free timestamp as local time silently. | Whether a field is an instant, a calendar date, or a duration; timezone/default behavior; and comparisons/expiry rules. |
| Money | Store and exchange money as integer paise. Do not use binary floating point for money. Convert to rupees only for display or explicit human-readable output. | Currency (currently INR unless a reviewed decision changes this), allowed range, whether zero is valid, and rounding/display rules. |
| Optionality | Missing, `null`, empty string, and empty collection are different values. Do not collapse them unless the field contract explicitly says to. | Whether omission means “not provided,” “leave unchanged,” or a default; whether `null` is allowed; and what an empty collection means. |
| Text and enums | Keep a field's meaning and allowed values stable across backend, generated API types, and clients. Do not make clients depend on database enum names or private model classes. | Length/format limits, normalization, allowed values, and behavior for an unknown value. |
| Collections | Preserve a documented ordering and stable tie-break rule wherever order is observable. | Sort key/direction, equal-key behavior, and whether order is guaranteed. |

### Approved identifiers, timestamps, and money

PD-06 inspected the existing skeleton before selecting these definitions. Implementation locations below are planned step 3 outputs, not existing callable helpers.

- **Identifiers:** generate UUIDv4 on the server. Wire output is a lowercase, hyphenated UUID string, e.g. `123e4567-e89b-42d3-a456-426614174000`. Callers treat it as opaque; knowing an ID grants no permission. Entity contracts determine whether an incoming ID references an existing entity or may be supplied at creation. Planned implementation: `app.core.identifiers`. [Decision](../decisions/identifiers.md).
- **Timestamps:** use timezone-aware instants internally and UTC for storage boundaries. Emit exactly six fractional digits followed by `Z`, e.g. `2026-10-17T06:30:00.000000Z`. Accept RFC 3339 timestamps with explicit timezone offsets and normalize to UTC; `2026-10-17T12:00:00+05:30` becomes that same example. Reject timezone-free inputs and avoid silent precision loss. Calendar dates and durations remain distinct types. Planned implementation: `app.core.timestamps`. [Decision](../decisions/timestamps.md).
- **Money:** API/storage units remain integer INR paise; reject booleans and binary floats as money values. Listing prices, offers, and price filters support whole rupees only: paise amounts must be multiples of 100. Convert exact whole-rupee text to paise at the display/input boundary; `125` rupees becomes `12500` paise and displays as `₹125`. Reject `₹125.50` rather than rounding. Zero remains valid for asking prices; each owning domain sets other ranges and offer rules. Planned implementation: `app.core.money`. [Decision](../decisions/money.md).

Tests in PD-06 steps 4–5 cover parse/format round trips, malformed values, timezone conversion and naive-time rejection, exact money conversion, and whole-rupee boundaries.

## 3. API errors and validation

All public API errors use the repository's standard error envelope, selected in PD-06 before domain endpoints are implemented. The envelope contains:

- A stable machine-readable error code.
- A safe human-readable message.
- Optional structured field or operation details that do not expose internal state.
- A request/correlation identifier when the request has one.

Use conventional HTTP status categories consistently: malformed/invalid input, unauthenticated request, forbidden action, missing resource, state/uniqueness conflict, rate limit, and unexpected server failure. Domain contracts state which expected codes/statuses apply to each operation. A client must not infer business meaning from a message string when a stable code exists.

Rules:

1. Validate at the boundary that receives untrusted input, then keep domain invariants enforced in the owning domain/service as appropriate.
2. Report invalid fields without returning stack traces, SQL, secrets, tokens, private message content, or other users' data.
3. Use the same response form for equivalent errors across domains; do not create private error envelopes per domain.
4. Do not return a success response when the operation failed. If a related asynchronous notification or image operation can fail independently, its contract must state whether the primary action succeeds and how that separate failure is recorded/retried.
5. List expected errors in each public contract, including authorization, invalid input, duplicate/conflict, missing resource, and dependency failure where applicable.

### Approved error shape and mapping

Use FastAPI validation and HTTP exceptions with shared exception handlers that produce this envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [{"field": "price_paise", "code": "whole_rupees_required"}]
  },
  "request_id": "123e4567-e89b-42d3-a456-426614174000"
}
```

`error.code` is a stable machine code; `message` is safe display text, not a machine contract. Omit `details` when there are no safe field/operation details. Detail entries use contract-defined field names and safe codes; they never contain rejected values, arbitrary exception text, or request bodies. HTTP middleware supplies `request_id`; a helper used outside an HTTP request may omit it.

| HTTP status | Common code | Meaning |
|---|---|---|
| 400 | `bad_request` | Malformed request outside field validation |
| 422 | `validation_error` | Invalid request fields, including pagination inputs |
| 401 | `unauthenticated` | Missing, invalid, or expired credentials |
| 403 | `forbidden` | Authenticated caller lacks permission |
| 404 | `not_found` | Resource or route unavailable to the caller |
| 409 | `conflict` | State/uniqueness conflict |
| 429 | `rate_limited` | Request rate limit reached |
| 500 | `internal_error` | Unexpected failure, with a generic safe message |
| 503 | `dependency_unavailable` | Required dependency unavailable |

Domain contracts may declare additional stable codes with their HTTP mapping. FastAPI request-validation failures, including malformed JSON reported through its validation machinery, retain HTTP 422; do not expose its raw validation input. Preserve applicable protocol headers such as `WWW-Authenticate`, `Retry-After`, and `Allow`. Planned implementation: `app.core.errors` plus API handler wiring. [Decision](../decisions/errors.md). Tests cover mappings, equivalent envelope shapes, safe details, and unexpected-error redaction.

## 4. Authentication and authorization context

1. Only the authentication boundary validates the incoming identity credential and creates a trusted caller context.
2. A domain operation receives caller identity/trust information from that trusted server-side context. It must not trust a client-supplied user ID, account class, eligibility flag, or owner flag as proof of authorization.
3. Each domain enforces authorization for the resources and actions it owns. A successful login does not imply permission to perform every operation.
4. Apply the PRD's temporary-user restrictions consistently: temporary users may browse, search, save listings, create wanted requests, start conversations, and submit offers; they may not create sale listings.
5. Check resource ownership and participant access at the owning domain boundary, including direct API calls and object-ID substitution attempts.
6. Cross-domain callers use the other domain's declared public contract. They do not reproduce its authorization rules by reading private tables or importing private implementation code.
7. Treat absent/expired/invalid credentials consistently. Contracts must distinguish unauthenticated from authenticated-but-forbidden behavior.
8. Development authentication and unsafe fake providers must fail closed in deployed/production mode; they must not be enabled by an accidental default or a frontend setting.

### Approved trusted caller context

Use one immutable internal `CallerContext` with `user_id` (validated internal UUID), `account_class` (`regular` or `temporary`), and `valid_until` (aware UTC instant). For example, a synthetic regular caller may have user ID `123e4567-e89b-42d3-a456-426614174000` and validity ending at `2026-10-17T07:00:00.000000Z`.

Identity validates credentials and current eligibility/revocation, then supplies the context through server dependency wiring. `valid_until` is no later than the applicable credential/account validity deadline; it does not replace revocation or eligibility checks. A domain rejects an expired context and checks permissions for its own resource/action. No client request model, user-ID header, account-class flag, ownership flag, or public constructor endpoint establishes trusted context. A Python type/constructor cannot by itself prove authentication; the authentication boundary establishes provenance. PD-06 supplies the type and validation boundary, not real sign-in or a successful authentication stub. Tests use explicit test-only dependency overrides.

Planned implementation: `app.core.auth`; Identity supplies the real credential/account validation later. [Decision](../decisions/caller-context.md). PD-06 tests cover immutability/validity and show that user-controlled IDs cannot become a trusted caller through HTTP input.

## 5. Pagination, filtering, and sorting

Every list operation exposed across a domain/API boundary must specify:

- Whether it is paginated and its default/maximum page size.
- The continuation mechanism and the serialized response fields.
- Whether the continuation value is opaque to callers.
- Stable ordering and a tie-break rule, so records are not skipped or duplicated when keys tie.
- How filters interact with pagination and authorization.
- What happens when the requested continuation value is invalid, stale, or belongs to different filters.

### Approved page pagination

Use numbered pages backed by offsets: `page` defaults to 1 and must be a positive integer; `page_size` defaults to 20 and must be one of 20, 50, or 100. Example: `?page=2&page_size=20` has offset 20. Reject malformed values, page zero/negative values, and unsupported sizes through HTTP 422 / `validation_error`.

The shared response is `{"items": [], "page": 2, "page_size": 20, "has_next": false}`. `has_next` reflects whether another authorized, filtered result exists; a total count is not required. A page past the current end returns an empty collection and `has_next: false`. Page numbers are explicit, not opaque cursors; stale/filter-bound cursor rules do not apply. Reset to page 1 when filters, sort, or page size change; every request reapplies authorization and filters before pagination.

Every operation declares sort direction and a unique ID tie-breaker. This guarantees deterministic order for unchanged data, not a snapshot across requests: concurrent inserts/removals or changes to sort keys can move results between pages. That limitation is accepted. The web flow uses page navigation with Previous/Next controls; infinite scroll is not required. Existing incremental message/read-watermark contracts remain separate operation semantics, not a second shared page envelope.

Planned implementation: `app.core.pagination`; web/client implementation remains with its owner. [Decision](../decisions/pagination.md). Tests cover sizes, offsets, invalid pages, final/empty pages, stable ties, and filtered/authorized pagination at the owning domain's accurate test point.

## 6. Domain ownership and cross-domain calls

The project has four feature domains: Identity, Listings, Search, and Conversations. Their public contract files are the only supported code-level boundary between domains. Each domain contract document and the combined contract must agree on public type names, behavior, errors, and ownership.

Shared rules:

1. A domain owns its private implementation and authoritative writes for the records assigned to it. Other domains request behavior through the owner's public contract.
2. Do not import another domain's private modules, query its private tables, or write its data directly.
3. Keep public interfaces small and implementation-independent. Expose request/response types and documented operations, not ORM entities, database sessions, framework request objects, or private classes.
4. Avoid circular imports and call cycles. If two domains appear to require mutual calls, stop and propose an orchestration/ownership design before implementation.
5. A cross-domain operation must identify which domain owns the user-visible result, which public contracts it calls, and how partial failure is handled.
6. Cross-domain behavior must state authorization assumptions explicitly. A caller cannot assume the other domain rechecked an actor identity unless the public contract guarantees it.
7. Shared primitives belong in core only when multiple domains need the same stable behavior. Do not move domain business rules into core for convenience.

The domain-specific contract documents will assign exact records and operations. If the PRD does not make an ownership boundary clear, the contract task must present alternatives and ask the human; this document does not guess those assignments.

## 7. Transactions, retries, idempotency, and ordering

Each public operation must document:

- Whether it reads, writes, or triggers external/asynchronous work.
- Which domain owns the transaction and which state changes commit atomically.
- Whether retrying the same request can duplicate state or side effects.
- Whether the operation is idempotent; if not, what duplicate/retry response is expected.
- Ordering guarantees for returned or emitted records/events.
- What the caller sees if a downstream domain/provider fails after the primary state change.

Use these shared rules:

1. A domain owns its transaction. Another domain cannot join it through private database access.
2. Mark retry-safe operations explicitly. For a create/send/action that may be retried, the contract must define the duplicate behavior and any required idempotency key before implementation.
3. Do not promise exactly-once delivery for asynchronous email or other external side effects unless the selected implementation can support and verify that guarantee. State the actual retry/deduplication behavior in the owning contract.
4. When a primary operation succeeds but an independent notification fails, preserve the PRD rule that notification failure does not decide whether the original message/marketplace action succeeds; make failure observable and safely retryable according to the approved design.
5. Do not invent event ordering across domains. If order affects user-visible behavior, define it in the relevant contract and test it.
6. Integration tests must exercise duplicate submissions, retries, concurrent requests, and partial dependency failures where they apply.

### Approved common retry boundary

Do not automatically retry arbitrary writes. For example, after an ambiguous create timeout, a caller must not blindly repeat a create operation unless its contract defines a safe idempotency/duplicate path. Each operation declares retry eligibility, duplicate result, concurrency behavior, and any idempotency-key scope and lifetime before implementation. A confirmed read may be retried according to its operation contract; no universal retry count/backoff or idempotency store is introduced by PD-06. A successful primary action stays successful when an independent notification fails; its owning domain must make the failure observable and safely retryable under the reviewed delivery design. No exactly-once promise is made.

This is a documented boundary; it needs no pretend transaction implementation in core. The real DB lifecycle belongs to PD-08, operation transactions to domain tasks, and notification durability/delivery to CN-03 with its producer owner. [Decision](../decisions/retries.md).

The exact mechanism for cross-domain events, outbox/retry storage, or provider delivery is not selected here. The relevant foundation/domain task must inspect the architecture, present implementation choices and a step-by-step plan, and obtain human review for choices that change data, delivery behavior, cost, or infrastructure.

## 8. Privacy, logging, and secret handling

- Never place access tokens, credentials, OTPs, private keys, database passwords, or other secret values in source, fixtures, logs, examples, screenshots, or generated files.
- Do not log message plaintext, decrypted content, full contact data, UPI IDs, or credentials. Message ciphertext also must not be copied into logs or evaluation evidence.
- Use a request/correlation identifier to connect safe logs across components. Keep logged IDs and metadata to the minimum needed to diagnose behavior.
- Sanitize user-controlled text before it enters logs; bound size and avoid turning user content into log structure.
- Keep logs structured and redact sensitive fields centrally, while also ensuring call sites do not emit them.
- Public errors and logs must not expose database queries, stack traces, encryption material, or another user's private data.
- Store actual shared secrets only in the approved secret manager or access-controlled channel. Repository docs may contain secret names/references and access instructions, never values.

The required `docs/environment/secret-handling.md`, initialized in PD-03 and completed for shared access in PD-14, records owners, approved access paths, references, and rotation/revocation steps. ID-01 and CN-03 add provider references when selected. The task prompt requests access just in time only when a task needs it; it never asks the human to paste a secret into chat.

### Approved logging and correlation

Emit structured JSON containing approved diagnostic metadata only: event code, severity, timestamp, server request ID, and where applicable HTTP method, route template, status, and duration. Route templates exclude raw query strings and path values. Use centrally controlled event names/fields, bounded text, and central redaction; do not serialize arbitrary objects, exception messages/tracebacks, request bodies, headers, or provider responses into logs. Redaction is defense in depth; call sites must omit sensitive values in the first place.

Generate a fresh server UUIDv4 request ID for each HTTP request, propagate it through request-local context and the public error envelope, and return it in `X-Request-ID`. Client-supplied request IDs do not replace it. A synthetic event may report `{"event": "request_completed", "status": 200, "request_id": "123e4567-e89b-42d3-a456-426614174000"}`. Planned implementation: `app.core.logging` plus API middleware. [Decision](../decisions/logging.md). Tests cover correlation isolation/propagation, bounded structured output, and sensitive-value omission/redaction.

### Approved provider selection and production safety

Identity and email provider selections default to `disabled` until explicitly configured. Disabled means unavailable capability, never successful fake authentication/delivery. Local/test fakes require explicit selection in `local` or `test` mode and use synthetic values only. Production rejects fake identity/email providers and development authentication at startup, alongside the existing debug rejection. Real-provider setup must validate its required configuration; invalid or unavailable real providers fail closed and never fall back to fakes. A runtime dependency failure uses the shared error behavior when applicable; independent email failure still follows the primary-action rule in section 7.

For example, selecting fake identity in `test` is an explicit fixture choice; the same selection in `production` prevents startup. A disabled email provider sends nothing and must not claim delivery. PD-06 adds configuration validation in `app.core.config`; PD-10 supplies reusable controlled fakes, and ID-01/CN-03 implement actual providers. No live provider is created or contacted by this decision. [Decision](../decisions/provider-safety.md). Tests must demonstrate production rejection and no fallback to fake success.

## 9. Contract-document requirements

Each domain contract and the combined four-domain contract must describe every public operation with:

1. Purpose and owning domain.
2. Inputs: field types, required/optional/nullability, validation, and limits.
3. Outputs: field types, nullability, ordering, pagination, and stable meaning.
4. Authentication and authorization, including regular/temporary-user behavior where relevant.
5. Expected errors and status/code behavior.
6. Data read/written, authoritative owner, side effects, and transaction boundary.
7. Idempotency/retry semantics, concurrency/duplicate behavior, and ordering.
8. External dependencies and failure behavior.
9. Tests needed to prove the contract, including unauthorized and failure paths.

The Identity contract must also preserve the required contact-sharing public types and operations from the pre-domain requirements:

```python
class ShareableContactOptions(BaseModel):
    user_id: UserId
    has_email: bool
    has_phone: bool
    has_upi_id: bool

class SelectedOwnContacts(BaseModel):
    email: str | None
    phone: str | None
    upi_id: str | None

async def get_shareable_contact_options(user_id: UserId) -> ShareableContactOptions: ...
async def get_selected_own_contacts(user_id: UserId, fields: set[str]) -> SelectedOwnContacts: ...
```

The Identity contract must specify authorization and exposure rules for these operations. Selected values are private contact data: return only requested fields through the approved conversation/contact-sharing flow, and never place them in logs or test output.

Use stable contract types across `public.py`, generated OpenAPI, frontend API types, and generated agent stubs. The source contract is edited; generated outputs are rebuilt with the documented generator, never hand-edited. Cross-domain changes require review from affected owners because contracts are shared surfaces.

Exact filenames, commands, generators, and generated paths will be settled in the minimal repository-structure and pre-domain documents. Later task lists must explicitly include work that may otherwise be treated as “implied,” such as creating the synthetic dataset, workload scripts, test fixtures, generated outputs, and validation evidence. A dependency that is necessary for completion must be a named task with an owner, prerequisites, checks, and completion condition.

## 10. Shared decisions to settle once

The foundation contract/repository tasks must inspect the current repo and create one canonical home for each value before domain agents need it. Do not ask four agents to make separate choices.

| Shared item | Required action before relying on it |
|---|---|
| UUID creation/version and wire representation | Inspect core; present choices if not established; select and record one format. |
| Exact UTC wire format | Inspect existing API/types; choose one representation and add examples/tests. |
| Standard error JSON shape and stable common codes | Define one envelope and examples before endpoints are implemented. |
| Pagination mechanism, response shape, limits | Compare cursor/offset options against expected use; choose once and document. |
| Trusted auth-context fields and caller trust classes | Define the shared core type and the source of each field. |
| Cross-domain event/async failure convention | Decide only the common boundary; provider/worker implementation belongs in its task. |
| Category values, sensitive threshold and owner, IISc domains, provider config references | Record shared non-secret values in the correct canonical configuration or contract after human decision. |

If an item is only needed for a specific cloud command, deployment, review, or test, keep it as a just-in-time task input instead of adding it as a shared convention. If an implementation choice is undecided, the relevant task must make the agent present options, tradeoffs, risks, and an implementation/test plan before the human approves the consequential choice.

## 11. Ready-for-domain-contract check

- [ ] Shared core has one UUID, UTC, money, error, auth-context, pagination, and safe-logging convention.
- [ ] The current core and common frontend utilities were inspected before defining duplicate shared types.
- [ ] Cross-domain calls use public contracts only; ownership and transaction boundaries are explicit.
- [ ] Retry, idempotency, ordering, nullability, and authorization are required fields in every operation contract.
- [ ] Common decisions have one repository home; secrets and task-specific inputs are handled as specified above.
- [ ] Contract generation source, output locations, and command are documented in the repository plan before generated files are edited.
- [ ] Each domain gets its own contract document, and the combined contract matches those four documents.
- [ ] Required synthetic data, workload tooling, fixtures, generated outputs, and their tests are explicit tasks in later task lists.

## 12. Required boundary decisions and runtime workflow

DL-00 must explicitly define Search's supported listing-data boundary: a Listings-owned public query interface or an approved Search-owned projection with public-event/update synchronization. PostgreSQL-native indexed search remains the baseline. If a projection is selected, SE-01 explicitly implements its creation, backfill, update/delete/availability synchronization, indexes, failure recovery, and tests. Shared PostgreSQL storage is not permission to query another domain's private tables.

The Conversations contract must define authenticated read-watermark/receipt updates and the public recipient/read-state/event interfaces consumed by notifications. CN-01 implements and tests read acknowledgement; CN-03 uses that interface for read-before-due suppression. Define notification intent persistence and its producer transaction before final message-latency measurement.

Identity contact functions must have an explicit trusted-caller authorization binding in their final contract; the required signatures shown above are interface requirements, not permission to reveal arbitrary user IDs' contacts. Define a separately authorized notification-recipient resolution interface rather than reusing a broad public profile/contact response. DL-00 also classifies offer notes and contact-share payloads, their encryption/exposure and retention, and records any unresolved privacy choice before CN-02 stores them.

The runtime interaction protocol is `docs/prompts/reusable-task-prompt.md`; Git/PR collaboration is `CONTRIBUTING.md`; phases, readiness milestones, owners, and command responsibility are in `docs/tasks/project-task-index.md`. A missing output assigned to the selected step is created by that step. A missing prerequisite/source or genuinely uncertain action blocks that action and requires a precise question. Routine known implementation work proceeds within the verified scope; uncertainty must never be silently hidden.

## Dependency test doubles

Use `docs/architecture/stubs-and-integration-gates.md` for explicit isolated checkpoints. Test doubles implement the frozen public types/errors and adversarial scenarios, use controlled synthetic data and stay in test-only bindings. They never establish real identity/ownership/contact/encryption/storage/notification integration, schema integrity or NFR evidence. Production/deployed configuration rejects fake providers and cannot silently fallback to them. Domain owners track and verify the original real integration obligations before accepting readiness or complete work.
