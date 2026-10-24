# Contract source and generation

**Date:** 2026-10-18

**Origin:** PD-11 step 1.

**Updated:** 2026-10-19, PD-11 steps 4–9 layout, compatibility and version/review workflow; DL-00 Step 1 generator-boundary resolution.

## Question

Which editable source can describe HTTP contracts and internal Python interfaces
before domain implementations exist, without maintaining parallel definitions?

## Options considered

- Implemented FastAPI routes as the source: convenient HTTP generation, but
  insufficient for internal interfaces required before implementation by DL-00.
- Editable OpenAPI/YAML with internal-operation metadata: supports advance
  design, but needs additional Python generation and internal-call conventions.
- Typed Python contract declarations separate from handlers: fits the existing
  Python/Pydantic stack and represents both kinds of interface; requires a
  small, tested generation layer.

## Selected choice

Use reviewed typed Python declarations under `contracts/source/` as the
canonical editable machine-readable contract source. Keep models, operation
signatures and explicit HTTP metadata separate from domain implementations.
Shared technical types remain owned by `app.core`; declarations reuse them
rather than creating competing definitions.

Generate typed domain `public.py` interfaces from this source when
DL-00 supplies the reviewed contracts. Unbound operations remain declarations;
the approved ID-01 Step8 extension below adds scoped technical dispatch only for
explicitly reviewed runtime-binding metadata. Generate the HTTP OpenAPI schema
from explicit HTTP declarations using FastAPI's schema machinery, then generate
frontend TypeScript declarations with pinned `@hey-api/openapi-ts@0.99.0`
using its TypeScript-only plugin (approved during step 5).
Internal calls do not become HTTP routes unless explicitly declared as such.
Only approved HTTP-exposed types belong in the HTTP schema/frontend output;
private internal contact operations do not become frontend APIs automatically.

The actual application binds implementations to the declared HTTP shapes.
Contract tests compare its schema against the generated contract and detect
missing, extra or incompatible operations. Generated schema is not itself proof
that an operation exists or works. Generated declarations must not implement
business behavior or return fake success.

## Rationale

Domain consumers need reviewed interfaces before providers are implemented.
One declaration source supports that ordering and ties HTTP and frontend shapes
to the same reviewed types without using implementation code as the only source.

## Implications

- PD-11 initially documented and tested generation using the existing health
  surface, with the required Identity contact declarations as its step 8
  exception. DL-00 Step 11 now adds the owner-reviewed HTTP mappings and internal
  callables for all four domains.
- Step 4 records paths/commands in [the contracts guide](../../contracts/README.md):
  `contracts/generated/openapi.json` and `contracts/generated/types.gen.ts`, driven
  by `scripts/generate_contracts.py` (initial project format version 1, extended
  to format 2 in DL-00 Step 11). The selected
  TypeScript generator pin is `@hey-api/openapi-ts@0.99.0` with only the
  TypeScript plugin; one root TypeScript `5.9.3` serves the generator and web.
  A generated runtime health module lives in `apps/api/app/contracts/health.py`.
  Step 6 adds stale/parity regression tests.
- DL-00 produces the four reviewed domain public declarations and representative
  consumer type-check evidence; owning domain tasks implement the providers.
- Generated files are rebuilt, never hand-edited. Human-readable contracts
  retain required authorization, transaction, privacy and failure semantics.
  Schema/type generation does not prove those behaviors.
- Schema export is a local build/check action; it does not require publishing a
  new HTTP schema endpoint or starting a provider/database/cloud service.

## Approver

Current integration contributor, explicit approval of the PD-11 step 1 proposal.
Affected domain owners' documentation review is user-reported complete
(2026-10-20); independent review and exact-revision merge approval remain
required under CONTRIBUTING.md.

## Supersedes

None. Establishes the previously unselected generation approach. Future changes
update this decision file and affected canonical requirements.

## Step 5 compatibility revision — approved

The contributor selected one compatible compiler setup, replacing root
TypeScript 7.0.2 with **5.9.3** for both frontend and generation. Keep the approved
Hey API **0.99.0** generator and existing Node 24/npm 11 toolchain, root manifest
and single root lockfile. No tooling workspace or separate compiler is used.
The transitive YAML parser is pinned to patched **4.3.2** through the root
override; npm audit reports zero vulnerabilities at this checkpoint.

This replaces the step 4 openapi-typescript 7.13.0 selection: it rejected the
old compiler peer range, and Hey API's broader peer metadata did not establish
actual TypeScript 7 compiler-API compatibility. Successful generation and full
frontend checks now verify the shared 5.9.3 setup. Regeneration is deterministic;
stale-output/runtime-parity regression coverage is implemented in step 6.

## Version/review workflow — PD-11 step 9 and DL-00 Step 11

The current HTTP version remains 0.1.0, declared once in canonical health source
and consumed by generated runtime metadata/OpenAPI. Generator format 2 and source
Git revision are recorded separately. The [contract guide](../../contracts/README.md#version-and-change-review)
requires compatibility classification, affected-owner decisions before shared
semantic changes, regenerated outputs, real consumer checks, independent human
peer approval and authorization of the exact merge. This records existing
CONTRIBUTING/shared-contract gates without granting self-approval or accepting
unimplemented domain behavior. Future source revisions update this same decision.

## DL-00 Step 1 generator-boundary resolution — 2026-10-19

The Step 1 inventory confirmed that typed Python source can express both explicit
HTTP metadata and typed internal callables: the health route is the former and
Identity's contact declarations are the latter. At the time of that inventory,
the PD-11 generator was health-only and did not discover generic callables or
emit domain public modules. Preserve the single typed Python source of truth
and extend generation in DL-00 Step 11 to emit declaration-only domain
`public.py` modules from the reviewed internal signatures. Only explicitly
mapped HTTP operations enter OpenAPI and generated frontend types; internal
calls never become routes by inference. No domain signatures were authorized
by this Step 1 resolution. The affected owners later reviewed the contract
documents, as the user reported on 2026-10-20.

## DL-00 Step 11 typed-interface implementation

The canonical source now consists of `contracts/source/types.py` plus explicit
HTTP mappings and internal callables in each domain source module. Generation
emits shared runtime models and four declaration-only `public.py` modules. It
uses FastAPI only in an offline contract app to build OpenAPI, then the existing
Hey API TypeScript-only plugin. Generated HTTP declarations are not installed
into the live app; only the implemented health route is served. Each domain
callable raises `NotImplementedError` until its owner implements it.

The Search-owned Listings test adapter implements the generated
`ListingsPublic` protocol and uses PD-10 synthetic IDs/clocks/scenarios. Its
type check uses pinned Mypy 2.0.0 because Step 11 requires a Python 3.14-aware
checker; the selected check is limited to the consumer double. Runtime/provider,
database and cleanup behavior remain with domain implementation tasks.

## DL-00 Steps 12–13 audit — 2026-10-20

The cross-domain audit reconciled the Search/Conversations call descriptions
and preserved the approved acyclic graph. Shared contract timestamps now use
the PD-06 parser/formatter, reject naive and over-precise inputs, and serialize
as UTC with six fractional digits. Every paise field is constrained to
nonnegative integer multiples of 100, matching the approved whole-rupee price
rule. Regeneration updates the generated Python models and OpenAPI constraints;
regression tests cover these rules. The final local aggregate and exact results
are recorded in the [DL-00 work log](../status/work-log.md).
These checks establish contract and repository quality only; no domain provider
or FR/NFR behavior is claimed as implemented.

## ID-01 Step8 scoped runtime adapter extension — approved

Aditya verified [the capability/runtime binding plan](identity-capabilities-and-runtime-binding.md)
on2026-10-24. Canonical callables still raise NotImplementedError when invoked;
Identity RUNTIME_BINDINGS selects only check_account_eligibility. The format2
generator replaces that one refusal body with a typed shared-core dispatcher,
requiring its reviewed technical import, refusing source body, supported signature
and BaseModel result. No business logic/private provider import enters public.py.
Other domain/contact outputs stay refusing and byte-identical. HTTP/OpenAPI/
TypeScript signatures and format version remain unchanged.

Trusted composition supplies an immutable ContextVar mapping for each runtime
scope/request. There is no mutable global provider, environment discovery or
implicit binding. Unbound/malformed results fail safe503, including strict
revalidation of preconstructed Pydantic models without private warnings. Actual
eligibility SQL/authorization stays in Identity and runs outside the event loop.
Workers must enter explicit trusted scopes; imports/schema generation remain
side-effect-free. Source/refusal invariants, generated adapter shape/isolation,
current output checks and boundary tests cover the narrow exception. This does
not accept real runtime/consumer integration or authorize provider/cloud actions.

## ID-01 Step9 contact dispatch extension

The [reviewed Step9 mechanism](identity-contact-sharing-and-cleanup.md) selects
both contact functions in addition to eligibility, through the existing generator
metadata. All three use typed scoped dispatch; notification resolution and other
domains continue refusing. ContactSharingContext is a frozen internal Python
record, exported through generated Identity/public shared types, without changing
HTTP OpenAPI or TypeScript models. Regenerate; never hand-edit these outputs.
