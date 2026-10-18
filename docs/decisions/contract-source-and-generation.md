# Contract source and generation

**Date:** 2026-10-18

**Origin:** PD-11 step 1.

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
frontend TypeScript declarations with a pinned `openapi-typescript` tool.
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
- Steps 4–6 select exact generated paths, pin tool versions and establish
  regeneration, reproducibility, stale-output and runtime-parity checks.
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
