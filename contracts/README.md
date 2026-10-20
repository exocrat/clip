# Shared contracts

PD-11 step 5 implements offline health-contract generation. Full domain
contracts/public declarations remain DL-00 outputs.

## Source and generated files

[Approved source decision](../docs/decisions/contract-source-and-generation.md):
edit reviewed typed Python declarations separately from implementation handlers.

| Path | Role |
|---|---|
| `contracts/source/health.py` | Editable health response and explicit HTTP metadata. |
| `scripts/generate_contracts.py` | Python orchestrator; format version 1; fixed output registry. |
| `scripts/generate_types.mjs` | Local Hey API TypeScript-only helper; rejects external references. |
| `apps/api/app/contracts/health.py` | Generated runtime declaration; imported by the real health handler. |
| `contracts/generated/openapi.json` | Generated HTTP-only OpenAPI 3.1 document. |
| `contracts/generated/types.gen.ts` | Generated TypeScript types; no runtime SDK/client. |

Do not edit generated files. Only explicit HTTP mappings enter OpenAPI and
frontend types; internal calls/private contact types are not automatically
published. Source models and shared core primitives have one authoritative
owner. Domain contracts must also record authorization, errors, transaction,
retry/duplicate and privacy semantics that schema types cannot prove.

## DL-00 Step 1 inventory

The [DL-00 inventory](dl00-inventory.md) records the existing core and contract
types, HTTP operations, domain source state, generated outputs, database
ownership schemas and frontend presentation surfaces before domain signatures
are drafted. The current generator handles only the explicit health route; the
typed Python source format can declare internal callables, but generation of
domain `public.py` modules is not implemented yet. The [source/generation
decision](../docs/decisions/contract-source-and-generation.md) records the
resolution: preserve one typed Python source and extend generation in DL-00
Step 11, while only explicitly mapped HTTP operations enter OpenAPI and web
types.

The [domain ownership and call boundaries](domain-boundaries.md) record DL-00
Step 3's authoritative record owners, frontend connections, and acyclic
cross-domain call direction. Operation names, callable signatures and the
reviewed retirement protocol are completed in later DL-00 steps.

The [Identity contract](identity.md) is the Step 5 behavior/privacy draft. It
binds the existing contact declarations to trusted actor and conversation
authorization; Step 9 completes per-operation semantics and Step 11 updates the
canonical typed source before generation.

The [Listings contract](listings.md) is the Step 6 data and operation-boundary
draft. Listings owns availability/selection and gates listing-based offer
mutations while Conversations owns offer records; Step 7 consumes its listing
query boundary and Step 9 completes operation semantics.

The [Search contract](search.md) is the Step 7 discovery, Wanted Request,
draft-match, and saved-list boundary. Listings remains the only owner of sale
query/index data; the proposed public Wanted Request fields and authenticated
marketplace visibility remain explicit Step 10 review items.

The [Conversations contract](conversations.md) is the Step 8 thread, encrypted
entry, read-state, offer, contact-share, notification-intent, and activity
boundary. It preserves the acyclic origin-owner call direction; the crypto
protocol and destructive cleanup order remain separate approval gates.

Identity now carries the explicitly required step 8 internal contact declarations;
the other three sources remain docstring-only. No domain HTTP operations or
generated public modules are registered:

| Editable domain source | Later contract / implementation |
|---|---|
| [Identity](source/identity.py) | Required internal contact declarations present; full contract DL-00, implementation ID-01. |
| [Listings](source/listings.py) | Contract DL-00; implementation LI-01/LI-02. |
| [Search](source/search.py) | Contract DL-00; implementation SE-01/SE-02. |
| [Conversations](source/conversations.py) | Contract DL-00; implementation CN-01/CN-02, notification delivery CN-03. |

DL-00 supplies reviewed domain contracts and generates each domain's `public.py`
before provider implementation. This health increment registers only `/health`.

## Tools and exact commands

Use Python 3.14/uv, Node 24/npm 11 and the existing single root manifest/lockfile.
FastAPI **0.143.3**, Pydantic **2.14.1**, Hey API **0.99.0** and TypeScript
**5.9.3** are pinned. One TypeScript compiler serves web and generation; no
workspace or second compiler is needed. The root override pins the transitive
YAML parser to patched **4.3.2**. Install with `uv sync --locked` and `npm ci`.

From the repository root:

```bash
uv run --locked python scripts/generate_contracts.py generate
uv run --locked python scripts/generate_contracts.py check
```

`generate` builds the contract-only app's schema without importing/starting the
real API, renders all artifacts in temporary storage, then writes registered
outputs. Metadata is shared with the actual health route. Generated JSON keys
and text are deterministic; generator format 1 is recorded in each artifact.

`check` renders in temporary storage and compares registered files, including
missing outputs. Exit 0 means current; nonzero means drift or source/tool failure.
It leaves outputs unchanged and reports stale paths without source values.
On drift, fix source, regenerate, review the diff and rerun check. Tool errors
require checking the pins/lock and installed tools; there is no network-install
fallback. Child tooling receives a clean environment and local JSON references
only. No database/provider/cloud calls or schema endpoint publication occurs.

Step 5 verified two identical generations, check-only preservation, generated
TypeScript compilation and existing API/web checks. Step 6 tests missing/stale-output detection, source/tool failures, check-only
preservation, TypeScript consumers and actual API schema parity. Provenance key
`x-clip-generator-format` is build metadata, not runtime behavior. Runtime parity
must compare the actual app's independently generated schema, not replace it
with this output. Generated declarations never establish implemented behavior,
authorization or domain acceptance.

Boundary checks remain in force. PD-12 wires stale checks into CI; PD-13 maps
them into the common command front door; step 9 records contract version/review.

## Contract regression tests

After `uv sync --locked` and root `npm ci`, run:

```bash
uv run --locked pytest tests/contracts -q -W error
```

Root pytest includes these tests and now requires the locked Node dependencies.
The API-only suite still needs only its Python dependencies. Negative generation
checks copy minimal inputs to temporary trees and share installed tools without
writing them; no tracked source/output is altered. Real generation, missing and
stale files, changed source, tool mismatches and sanitized source failures are
checked. The actual app's schema is compared against the declared schema after
removing only generator provenance; extra/missing operations and changed response
shapes remain differences. A valid TypeScript consumer must compile and an
invalid status literal must fail. HTTP tests use in-process ASGI only. External
schema references are rejected; no network/provider/database services are used.
The only tracked generator behavior correction here sanitizes source syntax
errors rather than allowing a traceback to echo source text.

## Internal Identity contact declarations

`contracts/source/identity.py` carries only `ShareableContactOptions`,
`SelectedOwnContacts`, `get_shareable_contact_options(user_id)` and
`get_selected_own_contacts(user_id, fields)`, as required by shared conventions.
`UserId` reuses core's existing UUID representation. Selected-contact fields are
required/nullable and hidden from repr; serialization remains private data.
No contact values are used in declaration tests.

Both async declarations raise `NotImplementedError`; neither reads data nor
returns fake success. DL-00 must bind the trusted caller/own-contact permissions,
field validation/errors and authorized conversation-sharing flow before ID-01
implements them. An arbitrary user ID is not authorization, and these operations
are not notification-recipient lookup. CN-02's encrypted-sharing protocol remains
its reviewed domain work. No HTTP metadata is assigned, so these types/functions
remain absent from generated OpenAPI/TypeScript; generated `public.py` is DL-00.

## Version and change review

The current HTTP contract version is **0.1.0**. Edit `CONTRACT_VERSION` only in
`contracts/source/health.py`; generation copies it into the runtime declaration,
which supplies FastAPI's version, and emits it as OpenAPI `info.version`.
Generator format **1** is a separate artifact-format version. Record the source
Git revision and exact PR base/head for every handoff; no SHA or timestamp is
injected into generated output. Internal declarations remain unimplemented until
DL-00's reviewed public-interface handoff and retain their exact source revision.

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
