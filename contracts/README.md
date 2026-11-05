# Shared contracts

This directory defines typed HTTP and internal-call interfaces. Canonical Python
declarations are editable; generated Python, OpenAPI, and TypeScript outputs must
be regenerated. Contracts describe shapes and boundaries, not service behavior or
proof that a provider is wired. Current task status is in the
[work log](../docs/status/work-log.md).

## Source and generated files

See the [source and generation decision](../docs/decisions/contract-source-and-generation.md).

| Source or output | Purpose |
|---|---|
| `source/health.py`, `types.py`, and the four domain files | Shared types and reviewed domain HTTP/internal operation declarations. |
| `scripts/generate_contracts.py`, `scripts/generate_types.mjs` | Pinned contract/OpenAPI/TypeScript generator. |
| `apps/api/app/contracts/`, `apps/api/app/domains/*/public.py` | Generated Python interfaces; domain public modules expose typed call boundaries. |
| `generated/openapi.json`, `generated/types.gen.ts` | Generated HTTP schema and frontend types. |
| `combined.md`, `identity.md`, `listings.md`, `search.md`, `conversations.md` | Human-readable operation semantics and ownership constraints. |

Do not edit generated files. Only explicit HTTP mappings enter OpenAPI and web
types. Internal calls never become routes by inference. Domain behavior remains
with its owning implementation; unbound internal operations fail closed. Shared
technical primitives belong in `app.core`.

## Checks

From the repository root, after the locked Python and Node dependencies are
installed:

```bash
uv run --locked python scripts/generate_contracts.py check
uv run --locked pytest tests/contracts -q -W error
make contracts-double-check
```

`check` renders into temporary storage and reports stale or missing registered
outputs without rewriting them. To update generated files, edit canonical source,
run `generate`, review the complete diff, then run all listed checks. The tests
cover deterministic generation, schema parity, route registration, private type
exposure, consumer typing and failure cases; they do not prove cloud/provider
integration.

## Shared changes

Before changing semantics, identify owning operations and affected producers and
consumers; record authorization, privacy, transactions, errors, retries, and
compatibility. Obtain affected-owner review, regenerate all outputs, run the
relevant checks, and prepare one PR with exact base/head and migration notes. Follow
[CONTRIBUTING](../CONTRIBUTING.md) and the
[peer-review prompt](../docs/prompts/peer-review-prompt.md) for independent review
and merge authorization. A merge does not deploy cloud resources.
