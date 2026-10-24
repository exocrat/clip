# Campus Marketplace — Product Reference and Architecture Decisions

**Canonical repository path:** `docs/product/product-reference-and-architecture-decisions.md`
**Status:** Revised planning baseline. Implementation choices still follow their human decision gates; task completion requires actual repository evidence.

This document translates the submitted PRD and the team's follow-up requirements into a repository-level reference. The submitted PRD remains the source for requirement intent. This document is the working source for implementation planning; domain contracts and task documents must remain consistent with it.

## 1. Product summary

Campus Marketplace (CLIP: Campus Listing and Item Platform) is a private, IISc-focused web platform for discovering items for sale, publishing wanted requests, and communicating with buyers and sellers. It structures information that is currently spread across chronological messaging channels.

The platform supports discovery, communication, offers, seller-controlled availability, and deliberate contact sharing. It does not verify payment, item quality, pickup, delivery, or handover.

## 2. Scope and priority

### Required MVP

- IISc identity validation and restricted temporary buyer accounts.
- Sale listings, images, seller-controlled availability, browse, search, filtering, sorting, and saved listings.
- Wanted requests and showing possible sale matches while a request is drafted.
- Private buyer–seller conversations, structured offers, seller selection, and deliberate contact sharing.
- End-to-end encryption (E2EE) for private message content.
- Sensitive-purchase flags and an optional seller declaration about proof of purchase.
- Required event and unread-message email notifications.
- AWS deployment, basic observability, recovery, cost control, and the primary ECS-only versus ECS+Lambda experiment.
- Verification against the applicable PRD non-functional requirements (NFRs).

### Optional/stretch work

Keep these items in the later task lists, clearly labeled **Optional** or **Stretch**. They are not foundation prerequisites and must not delay required MVP work. If a team member selects one, its task must first require the agent to inspect the repository, present implementation options and tradeoffs, recommend a step-by-step implementation and test plan, and obtain human approval for consequential choices. Define feature-specific behavior only in that task.

- **Weekly wanted-request email digest:** send a weekly email about wanted requests, with opt-in/opt-out behavior. The task must define subscription, schedule/window, unsubscribe, empty-digest, deduplication, and failure behavior before implementation.
- **Wanted-match alerts:** notify a wanted-request author when a newly created listing is judged relevant. The task must define relevance, preferences, deduplication, delivery, privacy, and failure behavior before implementation.
- **Advanced image-aware search:** optionally explore image-aware search, potentially using CLIP (Contrastive Language–Image Pre-training). The task must consider model/runtime or managed-service needs, image processing, evaluation data, latency/cost impact, and fallback. It must not make this a dependency of baseline text search.
- **Other exploratory comparisons:** for example, a dedicated search service or chat polling overhead, only if time remains and a task is explicitly selected.

Optional work must not displace required functionality, security, NFR evaluation, cost limits, or the final testing/submission buffer. The required search baseline remains PostgreSQL native indexed full-text search.

### Explicit exclusions

Payment processing or verification; delivery or pickup coordination; ratings; auctions; partial quantity sales; atomic swaps; native mobile apps; offline use; multilingual UI; WhatsApp listing creation; automated pricing; comprehensive moderation; active multi-region serving; and a separate search service as an MVP dependency.

## 3. Functional requirements

The requirement IDs and intent below were checked against the submitted `docs/source/ICC_Project_PRD_FINAL.pdf`. The table is a concise paraphrase, not a replacement for the PRD’s full wording. Later contracts, tasks, and tests/evidence must trace to these IDs and preserve the PRD intent. Any discrepancy found while producing those documents must be recorded and resolved rather than silently normalized.

| ID | Required behavior | Validation intent |
|---|---|---|
| FR-01 | Grant regular access only after validating a signed Microsoft identity token and confirming its account identifier belongs to an approved IISc domain. | Valid, expired, incorrectly signed, and non-IISc token integration tests. |
| FR-02 | Allow a lower-trust temporary buyer account after email OTP verification; expire it automatically after 14 days and do not allow self-renewal. | Lifecycle integration test with controlled time. |
| FR-03 | Temporary users may browse, search, save listings, create wanted requests, start conversations, and submit offers, but may not create sale listings. | Direct API authorization test for each permitted/restricted operation. |
| FR-04 | Eligible regular users can create sale listings with title, description, category, condition, asking price including zero, negotiability, optional pickup area, availability period, and at least one image. | Valid and invalid field combination tests. |
| FR-05 | Only the listing owner can edit a listing or change its authoritative availability; unavailable listings are hidden from discovery. | Ownership and state-transition tests. |
| FR-06 | Authenticated eligible users can browse available listings with pagination. | Seeded multi-page functional test. |
| FR-07 | Search listing titles/descriptions; filter by item category, price range, condition, and negotiability; sort by recency or price. | Deterministic queries over labeled data. Baseline: PostgreSQL indexed full-text search. |
| FR-08 | Eligible users can create/manage wanted requests with title, description, category, optional budget. Before submission, use the draft title to show possible active sale matches. | UI/API test with matching and non-matching seeded listings. |
| FR-09 | Users can save/unsave listings. A saved listing can remain in the saved-items view after becoming unavailable. | State-transition integration test. |
| FR-10 | A buyer can create at most one private conversation per buyer–listing pair and exchange text messages with the listing owner. Store message content as ciphertext in the relational database; retrieve new messages through the normal API. | Uniqueness, authorization, ordering, and incremental-retrieval tests. |
| FR-11 | A buyer can submit a structured offer in a conversation, containing amount, optional note, timestamp, and status. | Creation, revision/withdrawal, and ownership tests. |
| FR-12 | A conversation participant can deliberately reveal only their selected phone, email, or UPI to the relevant conversation. | Privacy and authorization tests. |
| FR-13 | Send asynchronous email for defined events, such as a new conversation; later send an unread-message reminder. If read before the reminder is due, do not send it. Notification failure must not determine whether the original message succeeds. | Event generation, suppression, retry/failure behavior, and forced email failure tests. |
| FR-14 | Store listing images in object storage and reference them from authoritative listing records. | Successful/rejected upload, missing object, and partial failure tests. |
| FR-15 | Sellers can mark items unavailable; the platform must not claim payment, quality, collection, delivery, or handover are verified. | UI/API inspection and end-to-end workflow test. |
| FR-16 | Encrypt private messages on clients and decrypt only on conversation participants' clients. Servers store and relay ciphertext and hold no plaintext or decryption keys. | Two-client exchange, unauthorized decryption, tampering rejection, and key-change handling tests. Key loss is not server-recoverable; MVP supports one active browser device per user. |
| FR-17 | Flag listings whose price exceeds a configurable threshold or whose category is mobile phone or laptop. Offer the seller an optional “Proof of purchase available?” declaration and show it to buyers as an unverified seller statement. | Threshold boundary, category, edit/reclassification, and omitted/Yes/No tests. |

### Optional requirements to be specified before implementation

These are not additions to the required FR-01–FR-17 set unless the team explicitly promotes them.

- **Optional wanted-match alert:** define relevance, whether one listing can trigger multiple alerts, deduplication, user preference, delivery channel, failure/retry behavior, and privacy before coding. Test relevant/non-relevant, duplicate, preference, and failure cases.
- **Optional weekly wanted-request digest:** define recipient eligibility, weekly window/time zone, opt-in or opt-out default, unsubscribe, empty digest behavior, and delivery failure behavior. Test subscription changes, boundary times, empty/non-empty digest, duplicate prevention, and send failure.
- **Optional image-aware search:** keep baseline text search available. Define a labeled evaluation set and compare relevance, latency, and cost before claiming improvement. Do not add a model/runtime/cloud resource without explicit task scope and cost review.

### Accepted project clarification: public wanted-request discovery and response

This records the team's verified direction; it does not change the submitted PRD
or add an FR identifier. See
[`docs/decisions/wanted-request-discovery-and-response.md`](../decisions/wanted-request-discovery-and-response.md)
for the decision record.

- Open Wanted Requests are discoverable in the public `/` discovery surface
  through a Sale Listings / Wanted Requests toggle. Each open request has a
  public detail view.
- A potential seller can contact the request author from that view through a
  private conversation associated with the request. The responder need not
  already have a sale listing. The public page does not reveal private contact
  information; conversation reads remain limited to participants.
- Temporary accounts may browse requests but cannot start wanted-request
  response conversations. This clarification does not remove their other
  approved temporary-account capabilities.
- Authors manage only their own requests from `/my/listings` and may mark a
  request unavailable when it is no longer wanted. Sale Listings and Wanted
  Requests remain separate backend objects; their schemas and post-type taxonomy
  belong to their schema owner.
- The weekly wanted-request email digest remains optional and may link to public
  request details. It must not contain private conversation or contact data.
  Optional new-sale-to-wanted-request match alerts are a separate feature.

The domain tasks define authorization, request-to-conversation association,
duplicate/retry rules, filters, and closure behavior before implementation.

### Accepted project clarification: listing discovery and availability

Mohit approved the [listing discovery semantics](../decisions/listing-discovery-semantics.md) during PD-08 Step 2 on 2026-10-18. The PR #5 reviewer subsequently confirmed Suraj's distinction: **item category** means the kind of item (phone, bicycle, furniture, etc.), reusing the existing category catalogue. It is separate from the **Sale Listings / Wanted Requests** view toggle. This supersedes the earlier contrary interpretation recorded in that decision; a free item remains a Sale Listing priced at zero. A Sale Listing has a required availability start and optional end. Discovery excludes it before the start or at/after the end, independently of the seller's available/unavailable state and selected buyer. Saved references remain when a listing becomes unavailable or its availability window ends. Account/visibility and later approved retention rules still apply. This clarification does not modify the submitted PRD or establish affected-owner implementation/schema acceptance.

The submitted PRD retains its original wording, including “listing type.” In maintained requirements, that term is renamed **item category** and denotes the same field as category; FR-07 therefore specifies one item category filter, not two overlapping filters. This explicit clarification leaves the source PDF unchanged.

### PD-08 reviewed product/storage choices

Mohit approved the detailed [MVP schema directions](../architecture/mvp-database-schema.md) and linked decision records on 2026-10-18: application-owned temporary password/OTP/session state; required seller price/separate negotiability and optional buyer budget; catalogue/field/image limits; offer revision/withdrawal/selection rules; encrypted-content/key metadata; bounded notification episodes/retries; finite private-data retention; upload staging and inactive-origin retirement. The schema's source/decision links contain exact values and exceptions. These approvals are design choices, not implemented features, affected-owner approval, runtime/provider/security evidence or authorization to provision/deploy/delete cloud resources. Original FR/NFR acceptance remains with the named tasks.

## 4. Non-functional requirements and required evidence

The submitted PRD specifies a synthetic reference dataset of at least 1,000 listings and 5,000 users, a load generator such as k6, performance runs lasting at least five minutes after warm-up, and separate reporting of warm and cold-start behavior where applicable. The later evaluation procedure must define exactly how these conditions are constructed and measured.

| ID | Target | Measurement/evidence |
|---|---|---|
| NFR-01 Browse latency | At 20 requests/s sustained, at least 95% of successful browse requests complete within 1 second, excluding image-body transfer. | k6 client latency plus backend monitoring. |
| NFR-02 Search latency | With reference data and 10 search requests/s, at least 95% of indexed search requests complete within 1 second. | Load-generator latency and PostgreSQL query metrics. |
| NFR-03 Peak API behavior | At a controlled 50 requests/s for five minutes, successful-request rate is at least 95%, excluding intentionally rate-limited abusive requests. | Load-generator status codes and timeout statistics. |
| NFR-04 Search usefulness | On at least 20 manually labeled representative queries, Success@5 is at least 80%; a query succeeds if one or more human-labeled relevant results appears in the first five. | Offline evaluation script over a fixed query/listing set. |
| NFR-05 Active-chat latency | When both participants have the conversation open, at least 95% of messages become visible to the recipient within 5 seconds of send under normal workload. | End-to-end sender-submit to recipient-display timestamps. |
| NFR-06 Runtime recovery | With at least two healthy serving instances configured, forced loss of one runtime restores configured healthy capacity within 240 seconds; measure request failures during recovery. | Orchestrator events, health checks, and load-generator timeline. |
| NFR-07 Database recovery | Restore the latest available managed backup to a usable test database within 30 minutes. | Timed restore followed by integrity and smoke tests. |
| NFR-08 Budget | Total cloud spending for implementation and evaluation remains below USD 200. Every load experiment declares maximum duration and resource/concurrency caps before running. | AWS cost/billing evidence and experiment resource logs. |

The targets and measurement intents above were checked against the submitted PRD and are summarized here. The later experimental evaluation procedure must operationally define terms that need a repeatable rule, including successful request, normal workload, cold/warm state, restore completion, cost attribution, and how each percentile or rate is calculated. A task must identify the NFRs it affects and its local/cloud checks. The integrated release gate must demonstrate all applicable NFRs. Cloud checks may be batched, but evidence must identify the exact deployed revision, covered tasks/NFRs, commands or actions, results, and cleanup. A code change or passing local test alone is not proof of NFR completion.

## 5. Architecture baseline

- **Frontend:** responsive React + TypeScript web client across all domain surfaces. The [browser verification decision](../decisions/responsive-ui-and-camera-verification.md) makes desktop/phone human checks explicit and adds supported-phone camera/gallery selection to LI-02, retaining desktop file selection and existing image limits. This is a team clarification; the submitted PRD remains unchanged.
- **API:** Python + FastAPI REST service.
- **Authoritative state:** managed PostgreSQL for users, listings, wanted requests, conversations, offers, and related state.
- **Search:** PostgreSQL native indexed full-text search for MVP.
- **Images:** S3 object storage, with short-lived authorized upload URLs where practical; listing records remain authoritative for image references.
- **Baseline API runtime:** ECS containers. Lambda is available for asynchronous work and for the defined read-heavy experiment.
- **Experiment:** compare ECS-only against mixed ECS+Lambda for preselected read-heavy browse, listing-detail, and search/filter routes. State-changing operations stay on ECS in both configurations. PostgreSQL remains authoritative in both.
- **Identity:** Microsoft identity for regular users; separate email verification for temporary accounts.
- **Conversation delivery:** adaptive/lightweight polling over the ordinary API and HTTPS/TLS.
- **Message privacy:** client-side E2EE; clients hold private keys; servers persist and relay ciphertext only. Key loss cannot be recovered by the server; one active browser device per user for MVP.
- **Notifications:** asynchronous email. Notification failure does not roll back a successful marketplace action.
- **Network:** frontend and approved API ingress are public over HTTPS; database and internal workers are not public.
- **Observability/recovery:** correlate a request across browser/API/database without logging secrets, message plaintext, or sensitive contact data; finite retention and documented restore/recovery procedures.

The architecture above reflects the submitted PRD’s selected baseline. The exact offloaded routes, payloads, query distribution, and benchmark configuration must be frozen before measured comparison runs and recorded with the results. Any details not fixed by the PRD—such as a specific E2EE library or key-registration mechanism—remain implementation choices for their task, subject to the design checkpoint in Section 7.

## 6. Infrastructure-as-Code direction

The team plans to use Terraform because it may make infrastructure setup and recreation easier. The intended direction is to make repository-managed Terraform the reproducible source for the cloud resources in scope, with parameterized environment/account/region/resource settings and recorded outputs. Terraform must not introduce hard-coded account IDs, credentials, secrets, or unreviewed public exposure.

The implementation plan must decide and document before infrastructure work begins:

1. Which resources Terraform owns and which are intentionally managed elsewhere.
2. Where Terraform state is stored, who can access it, how locking/backups work, and how secrets are kept out of state where possible.
3. How plans are reviewed and applied by a human or approved CI role; ordinary coding agents must not apply infrastructure changes without the task's explicit authorization and human gate.
4. How deploy, verify, and teardown commands map to Terraform components and dependencies.
5. How the resource inventory and current-environment record are updated from actual outputs.

A Terraform change is a consequential infrastructure change: review its plan, expected resources, cost/exposure, rollback/recovery, and verification before apply. The human checklist must require identifying the exact AWS identity, account, region, environment, and target before any cloud action. No credentials are stored in the repository.

## 7. Where information belongs and when to ask for it

Do not treat every unresolved value as a question to ask at the beginning of every task. First classify it:

| Information type | Where it belongs | Agent behavior |
|---|---|---|
| Shared, non-secret, and needed repeatedly | A canonical repository file: product reference, architecture, conventions, public contract, checked-in non-secret config, or task plan. Examples include agreed domain rules, API behavior, a globally selected threshold, time zone, reminder delay, approved region, naming rules, or evaluation targets. | Read it from the repository. If missing and needed by several tasks, create a foundation/documentation task to decide and record it once; do not ask every domain agent independently. |
| Shared secret or credential | A separate access-controlled secret inventory/handling document and the designated secret manager. The repository contains only secret names/references and safe placeholders, never values. | Follow the approved access path. Request access just in time from the human only if the assigned task actually needs it. Never put the secret in a prompt, source, test fixture, log, or report. |
| Task-specific or environment-specific value needed only now | Keep it out of permanent product docs unless it becomes a reusable project rule. Examples include the exact target resource for a cloud operation, selected AWS identity/profile, deployment revision, one-time test address, or reviewer/PR target. | Ask the human just in time, before the dependent action. State what value is needed, why, and what action it enables. Do not guess. |
| Implementation approach not yet selected | The relevant task document, as an explicit design checkpoint before implementation. | Inspect the repository and constraints; present feasible implementation choices, tradeoffs, risks, and a recommended step-by-step plan with tests and verification. Wait for the human to choose/approve when the choice changes observable behavior, security/privacy, data, cost, contracts, dependencies, or cloud resources. For routine reversible details within an approved design, choose a sensible option and document it. |

A future access-controlled secret-handling document must contain only the approved secret names/references, access procedure, responsible owner, and rotation/revocation instructions. It must never contain secret values. Actual values belong in the approved secret manager or other explicitly access-controlled channel; do not paste them into the repository, an LLM prompt, or chat. An agent requests access through the approved route only when the assigned step needs it. Any shared, non-secret decision made during task work must be written back to its canonical repository location before other tasks depend on it.

## 8. Working rules for implementation planning

- Keep the foundation and repository structure as small as possible while still enabling repeatable local work, contracts, CI, deployment, integration, and verification.
- Build shared core primitives and domain boundaries before parallel feature work; do not pre-build domain feature implementations in the foundation phase.
- Each of the four domains gets its own contract document. All domain execution tasks live in the single authoritative `docs/tasks/domain-task-list.md`, organized into domain and cross-domain sections; do not create separate domain task-list files or a duplicate combined copy.
- Domain owners work in parallel only after shared dependencies and contracts are stable.
- Every task includes implementation, tests, local verification, and required cloud verification. Compatible cloud verification may be batched under a recorded revision/evidence map.
- Use Black for Python formatting, with the exact command/configuration specified in repository tooling documents.
- Do not weaken security, privacy, authorization, validation, rate limits, recovery, or tests to finish a task.
- Never record credentials, OTPs, real contacts, UPI IDs, message bodies, or private keys in source, fixtures, logs, examples, or generated artifacts.

## 9. Decision status and information ownership

### Requirements and architecture selected in the submitted PRD

The following are part of the submitted PRD baseline, not new choices introduced by this summary: AWS; React + TypeScript; FastAPI REST; managed PostgreSQL; S3; ECS baseline; Lambda for asynchronous work and the read-heavy experiment; PostgreSQL full-text search; adaptive polling; HTTPS/TLS; E2EE; one active browser device per user in the MVP; synthetic evaluation; and no payment or transaction verification. The PRD also makes FR-16 E2EE and FR-17 sensitive-purchase handling required MVP work.

The PRD describes full Infrastructure-as-Code as a stretch goal. The team has since expressed an intention to use Terraform. Treat Terraform as the team’s planned direction, while its precise ownership/state/apply workflow remains a design checkpoint before infrastructure work. This is a team planning update, not a claim that Terraform was already required by the submitted PRD.

### Shared facts to record in the repository

A foundation task should identify the canonical repository home for each shared, non-secret value and record it there when needed. Do not ask each domain agent to decide these independently. Examples include approved IISc domains, non-secret identity-provider identifiers, sensitive-purchase threshold, API/domain behavior, AWS region and naming/tags, budget and capacity caps, and stable evaluation targets. The foundation or domain task must state which values it owns and when they must be decided. Values that are only needed by a particular environment or operation should remain just-in-time inputs.

### Implementation choices to resolve in the relevant task

Do not decide every implementation detail in this product reference. If the implementation is still open, the relevant task must require the agent to inspect the current repository and constraints, present feasible options with tradeoffs and risks, recommend a step-by-step implementation/test/verification plan, and wait for human approval before consequential work. This applies, for example, to E2EE library/protocol and key lifecycle details, Terraform state/apply design, and any selected optional feature. The agent may choose routine, reversible details within an approved design and document them.

Optional/stretch details (such as digest schedule/default, wanted-match relevance and deduplication, or image-search model/runtime and evaluation target) are decided only if the team selects that stretch task. They are not shared foundation decisions.

### Secrets and just-in-time inputs

Shared credentials, API keys, identity secrets, database passwords, encryption material, and tokens use the designated secret manager or approved secure channel. The repository and its secret-handling document contain references and procedures only, never values. Request access only when an assigned task actually requires it.

Confirm exact AWS identity, account, environment, target resource, deployed revision, and one-time verification details immediately before the dependent operation. Ask the human then if the information is unavailable; do not collect it from every teammate at project setup or guess it from a console.

## 10. Traceability gate for the next documents

This is a review checklist for Document 1. PRD comparison was completed against the submitted PDF on 2026-10-14; downstream documents must still complete their own traceability checks. Before using this reference for downstream task generation, verify:

- [ ] FR-01 through FR-17 are present and accurately represented.
- [ ] NFR-01 through NFR-08 retain their target, workload condition, and measurement evidence.
- [ ] Required, optional, and excluded scope are clearly distinguished.
- [ ] Terraform, Black, E2EE, sensitive-purchase behavior, and all three optional feature ideas are represented consistently.
- [ ] Shared facts, secret references/procedures, just-in-time values, and implementation choices are assigned to the right place; optional task details are deferred unless selected.
- [ ] Shared non-secret decisions have one repository home; secret values are excluded from repository files and prompts.
- [ ] Tasks tell agents to propose options and an implementation/test/verification plan before consequential undecided work.
- [ ] The contracts, evaluation procedure, repository plan, and task documents can link back to this reference without contradicting it.

## 11. Execution, collaboration, and accepted scheduling update

The project starts with BOOT-00 in `docs/tasks/bootstrap-task-list.md`, followed by the pre-domain list, PRE-00 foundation milestone, domain tasks, Document 2's experiment tasks, and CLOSE-00 final closeout. The phase and milestone registry is `docs/tasks/project-task-index.md`.

The mandatory loop is read-only inspection → explain understanding → human verifies → execute one numbered task step → report expected/observed results and evidence → human verifies → advance. Stop within a step at any unresolved question or separate action approval. Persist step/checkpoint and verification state in `docs/status/work-log.md` so a new session resumes without repeating completed side effects.

Git collaboration follows root `CONTRIBUTING.md`: separate clones/worktrees and task branches, peer-reviewed PRs to main for later work, affected-owner review for shared changes, and local/CI gates. BOOT-00 has a one-time, docs-only direct-to-main commit rule for the existing repository; it does not require separate peer review. Publishing the local seed requires separate approval of the exact target and revision, but does not block PD-00 in that clone. The combined PD-00–PD-03 handoff goes directly to `main` after its full audit passes. Merge does not authorize deployment or Terraform apply.

**Accepted team scheduling change, 2026-10-14:** The submitted PRD §8 schedules stretch work after required functionality, evaluation, and submission material. The team's later instruction permits selected optional features to begin after their own technical prerequisites, provided the human approves their scope and confirms that required MVP work, accurate NFR verification, the primary experiment, budget, and final submission buffer will not be put at risk. This is a planning change; preserve the submitted PRD unchanged. Record it at `docs/decisions/optional-work-scheduling.md` during bootstrap. It does not turn optional work into required MVP or permit it to block required milestones. Optional changes require affected regression checks and protection of frozen experiment revisions.

Use the task index's optional prerequisites: OPT-01 needs ID-READY, SE-02, and CN-03; OPT-02 additionally needs LI-CORE and SE-CORE; OPT-03 needs LI-02, SE-CORE, and DATA-READY. Their design decisions and image-aware labels remain work within the optional task.

A required task with an unmet check remains blocked. Readiness milestones may unblock named consumers, but are distinct from final task/FR/NFR completion. NFR-08 is tracked throughout and finalized in CLOSE-00 after experiment expenditure and cleanup. Source updates that change a measured path, schema/indexes, authorization, workload, runtime configuration, or resource capacity invalidate affected evidence until it is rerun or a documented equivalence review justifies reuse.

## Development execution clarification

The existing repository is exocrat/clip. Existing WSL is reused with the Linux clone/agent startup guide. The canonical stub guide permits early isolated domain work after real PRE-00/DL-00 and reviewed interfaces; it does not change product behavior or relax real feature/NFR acceptance. Checklists are supplied and used immediately, with later maintenance tasks.
