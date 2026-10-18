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

Planned domain source slots under `contracts/source/` are Identity, Listings,
Search and Conversations. Step 7 documents empty placeholders; step 8 declares
only the required Identity contact interfaces. DL-00 supplies reviewed domain
contracts and generates each domain's `public.py` before provider implementation.
This health increment does not create those four domain interfaces.

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
TypeScript compilation and existing API/web checks. Step 6 still adds formal
missing/stale-output and actual-API-schema regression tests. Provenance key
`x-clip-generator-format` is build metadata, not runtime behavior. Runtime parity
must compare the actual app's independently generated schema, not replace it
with this output. Generated declarations never establish implemented behavior,
authorization or domain acceptance.

Boundary checks remain in force. PD-12 wires stale checks into CI; PD-13 maps
them into the common command front door; step 9 records contract version/review.
