# Shared contracts

DL-00 Step 11 extends PD-11's offline health generator to the reviewed domain
contracts. The source describes explicitly mapped HTTP operations and internal
calls; generated declarations remain behavior-free.

## Source and generated files

[Approved source decision](../docs/decisions/contract-source-and-generation.md):
edit reviewed typed Python declarations separately from implementation handlers.

| Path | Role |
|---|---|
| `contracts/source/health.py`, `types.py`, and `{identity,listings,search,conversations}.py` | Editable shared models, domain HTTP mappings, and internal callables. |
| `scripts/generate_contracts.py` | Python orchestrator; format version 2; fixed output registry. |
| `scripts/generate_types.mjs` | Local Hey API TypeScript-only helper; rejects external references. |
| `apps/api/app/contracts/health.py`, `domain_types.py` | Generated runtime health and shared wire models. |
| `apps/api/app/domains/{identity,listings,search,conversations}/public.py` | Generated typed internal interfaces; each callable refuses use until implemented. |
| `contracts/generated/openapi.json` | Generated HTTP-only OpenAPI 3.1 document. |
| `contracts/generated/types.gen.ts` | Generated TypeScript types; no runtime SDK/client. |

Do not edit generated files. Only explicit HTTP mappings enter OpenAPI and
frontend types; internal calls never become routes by inference. Private
internal types stay out unless an explicitly reviewed HTTP operation uses them,
as contact preparation does for a caller's selected own fields. Shared technical
primitives remain owned by `app.core`; domain types live in canonical contract
source. Human-readable contracts still define behavior the schemas cannot prove.

## DL-00 Step 1 inventory

The [DL-00 inventory](dl00-inventory.md) records the existing core and contract
types, HTTP operations, domain source state, generated outputs, database
ownership schemas and frontend presentation surfaces before domain signatures
are drafted. PD-11 initially handled only the explicit health route. DL-00
Step 11 extends the same typed Python source to domain HTTP mappings and
internal callables. The [source/generation decision](../docs/decisions/contract-source-and-generation.md)
records the resolution; only explicitly mapped HTTP operations enter OpenAPI
and web types.

The [domain ownership and call boundaries](domain-boundaries.md) record DL-00
Step 3's authoritative record owners, frontend connections, and acyclic
cross-domain call direction. The
[combined Step 9 operation registry](combined.md) maps HTTP operations,
internal callables, and approved frontend surfaces. The user reports that
affected domain owners reviewed and approved the documents on 2026-10-20; exact
destructive cleanup ordering remains a separate human gate.

The [Identity contract](identity.md) is the Step 5 behavior/privacy contract. It
binds the existing contact declarations to trusted actor and conversation
authorization; Step 9 records per-operation semantics in the combined registry,
and Step 11 updates the canonical typed source before generation.

The [Listings contract](listings.md) is the Step 6 data and operation-boundary
contract. Listings owns availability/selection and gates listing-based offer
mutations while Conversations owns offer records; Step 7 consumes its listing
query boundary and Step 9 records operation semantics in the combined registry.

The [Search contract](search.md) is the Step 7 discovery, Wanted Request,
draft-match, and saved-list boundary; the combined registry records Step 9
operation details. Listings remains the only owner of sale query/index data;
the owner-reviewed public Wanted Request fields and signed-in marketplace
visibility are recorded in the combined contract.

The [Conversations contract](conversations.md) is the Step 8 thread, encrypted
entry, read-state, offer, contact-share, notification-intent, and activity
boundary; the combined registry records Step 9 operations and page connections.
It preserves the acyclic origin-owner call direction; the crypto protocol and
destructive cleanup order remain separate approval gates.

The owner-reviewed sources register each domain's HTTP operations and internal
callables. Generation creates the four public modules and shared model module;
provider behavior remains with domain implementation tasks:

| Editable domain source | Later contract / implementation |
|---|---|
| [Identity](source/identity.py) | HTTP mappings and four internal callables; implementation ID-01. |
| [Listings](source/listings.py) | HTTP mappings, five internal callables and consumer protocol; implementation LI-01/LI-02. |
| [Search](source/search.py) | HTTP mappings; consumes Listings, Conversations and Identity interfaces; implementation SE-01/SE-02. |
| [Conversations](source/conversations.py) | HTTP mappings and ten internal callables; implementation CN-01/CN-02, notification delivery CN-03. |

The generated contract-only OpenAPI contains 50 domain HTTP mappings plus
health. The running API currently installs health and the Listings create,
detail, owner-list, and replacement routes. Other generated domain declarations
remain offline until their owners implement them. Listings routes fail closed
until trusted authentication and an explicit storage/Identity adapter are wired;
the generated declarations are not runtime implementations.

## Tools and exact commands

Use Python 3.14/uv, Node 24/npm 11 and the existing single root manifest/lockfile.
FastAPI **0.143.3**, Pydantic **2.14.1**, Hey API **0.99.0** and TypeScript
**5.9.3** are pinned. One TypeScript compiler serves web and generation; no
workspace or second compiler is needed. The root override pins the transitive
YAML parser to patched **4.3.2**. Mypy **2.0.0** is scoped to the Search-owned
consumer-double type check. Install with `uv sync --locked` and `npm ci`.

From the repository root:

```bash
uv run --locked python scripts/generate_contracts.py generate
uv run --locked python scripts/generate_contracts.py check
make contracts-double-check
```

`generate` builds the contract-only schema without importing/starting the real
API, renders all artifacts in temporary storage, then writes registered outputs.
The real app installs health and the currently implemented Listings HTTP
subset; the other generated domain endpoints remain offline. Health metadata is
shared with the actual route. Generated JSON keys and text are deterministic;
format 2 is recorded in each artifact.

`check` renders in temporary storage and compares registered files, including
missing outputs. Exit 0 means current; nonzero means drift or source/tool failure.
It leaves outputs unchanged and reports stale paths without source values.
On drift, fix source, regenerate, review the diff and rerun check. Tool errors
require checking the pins/lock and installed tools; there is no network-install
fallback. Child tooling receives a clean environment and local JSON references
only. No database/provider/cloud calls or schema endpoint publication occurs.

PD-11 established health generation and runtime health parity. DL-00 Step 11 adds
the 50 explicit domain HTTP mappings, typed internal callables, Python `public.py`
modules, OpenAPI and TypeScript shapes. Contract tests compare the real API's
health route/schema to its declared health subset and assert domain declarations
are not installed. Provenance key `x-clip-generator-format` is build metadata,
not runtime behavior. Generated declarations never establish implemented
behavior, authorization or domain acceptance.

Boundary checks remain in force. PD-12 wires stale checks into CI; PD-13 maps
them into the common command front door; step 9 records contract version/review.

## Contract regression tests

After `uv sync --locked` and root `npm ci`, run:

```bash
uv run --locked pytest tests/contracts -q -W error
make contracts-double-check
```

Root pytest includes these tests and now requires the locked Node dependencies.
The API-only suite still needs only its Python dependencies. Negative generation
checks copy all canonical source/core inputs into temporary trees and share
installed tools without writing tracked outputs. Tests cover deterministic
generation, missing/stale outputs, changed source, tool mismatches, sanitization,
all 50 operation IDs, live schema parity for health and implemented Listings
routes, noninstallation of other domain routes, private type exposure, and
TypeScript consumers. The Listings test double is
type-checked against the generated `ListingsPublic` protocol with Mypy. HTTP
tests use in-process ASGI only; no provider, database or cloud is used.

## Internal Identity contact declarations

Identity source declares the four internal callables in the reviewed registry.
The contact methods take trusted `CallerContext` plus conversation scope; they
never accept a target user ID as authorization. Notification recipient
resolution takes server-injected `NotificationWorkerContext` and returns only
an ephemeral destination. Contact values and recipient addresses have repr
redaction. Every generated callable raises `NotImplementedError` until the
Identity owner implements it. Only selected own contacts explicitly returned
by the Conversations contact-preparation HTTP operation enter the HTTP/TypeScript
schema; availability flags and notification-recipient values remain internal.

## Version and change review

The current HTTP contract version is **0.1.0**. Edit `CONTRACT_VERSION` only in
`contracts/source/health.py`; generation copies it into the runtime declaration,
which supplies FastAPI's version, and emits it as OpenAPI `info.version`.
Generator format **2** is a separate artifact-format version. Record the source
Git revision and exact PR base/head for every handoff; no SHA or timestamp is
injected into generated output. The declarations define reviewed interfaces;
each provider remains unimplemented until its domain task supplies behavior.

For every shared contract change:

1. Identify the owning operation/types and affected producers, consumers and
   domain owners. Describe changed fields, required/null semantics, call paths,
   errors, authorization/privacy, transactions, retry/order and failure behavior.
2. Classify compatibility for Python callers and HTTP/TypeScript clients.
   Additions are not automatically compatible: a required field, narrower enum,
   changed error/permission or altered transaction may break a consumer. Propose
   the version change with its justification for owner review. Editorial changes
   with identical public semantics can retain the contract version.
3. Obtain affected-owner review before changing shared semantics. For an
   incompatible change, obtain the required human decision and record consumer
   migration, ordering and real verification obligations before implementation.
   Pre-1.0 numbering does not waive any review or compatibility gate.
4. Edit the canonical source and relevant human-readable requirements/decisions.
   Regenerate all registered outputs; never repair generated files directly.
   Domain implementations stay behind their reviewed public interfaces.
5. Run freshness, actual API schema/consumer tests, boundaries and affected
   application checks. Update matching test doubles through their consumer
   owners, preserving denied/failure cases and pending real integration checks.
6. Prepare one coherent PR with source/generated diffs, base/head, versions,
   compatibility/migration notes, exact checks, affected owners and unresolved
   gates. Arrange independent review using the
   [peer-review prompt](../docs/prompts/peer-review-prompt.md). AI findings do not
   constitute the designated human's approval; authors cannot approve themselves.
7. Follow [CONTRIBUTING](../CONTRIBUTING.md): resolve findings, obtain affected
   owners' and independent human approval and explicit authorization for the
   exact merge revision. Record accepted main SHA and refresh consumers afterward.
   Changed reviewed semantics require renewed review; merge never deploys cloud.

## SE-01 draft public search query amendment

[Keyword/Hybrid and both-mode relevance proposal](search-mode-proposal.md) is a
review packet, not registered schema. It names the existing query/response boundary,
exact validation/ranking/switching rules and downstream review/test gates. Current
source/generated/runtime declarations remain unchanged in this checkpoint.

## SE-02 wanted-response200 correction

Mohit verified the [pre-implementation Search correction](../docs/decisions/wanted-response-contract-correction.md).
Only Search's alternate200 response now has the already documented
ConversationStartResult body;201/path/input/capability stay unchanged. HTTP0.1.0
is retained for this documented-semantic correction. Registered outputs are
regenerated; `tests/contracts/search_response_consumer.ts` compiles both success
statuses and requires the conversation ID. Normal independent/affected-owner
review and publication/merge gates remain; no other domain response was changed.
