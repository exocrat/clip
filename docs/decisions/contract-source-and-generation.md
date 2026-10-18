# Contract source and generation

**Date:** 2026-10-18

**Origin:** PD-11 step 1.

**Updated:** 2026-10-18, PD-11 step 4 layout/tool selection.

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

Generate declaration-only domain `public.py` modules from this source when
DL-00 supplies the reviewed domain contracts. Generate the HTTP OpenAPI schema
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

- PD-11 documents and tests generation using the existing health surface.
  Required Identity contact declarations are the explicit step 8 exception;
  other domain operations remain empty until DL-00 review.
- Step 4 records paths/commands in [the contracts guide](../../contracts/README.md):
  `contracts/generated/openapi.json` and `contracts/generated/types.gen.ts`, driven
  by `scripts/generate_contracts.py` (project format version 1). The selected
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
Affected-owner/independent review and exact-revision merge approval remain
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
formal stale-output/runtime-parity regression coverage remains step 6.
