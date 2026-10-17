# Shared API core

This package is the single home for technical primitives needed across domains. Domain authorization and marketplace business rules remain in their owning domains. PD-05 step 3 establishes this boundary; it does not freeze the unresolved PD-06 conventions or implement the PD-08 database lifecycle.

## Available implementation

`config.py` provides typed process-environment settings and safe startup validation. Import `Settings`, `ConfigurationError`, or `load_settings` from `app.core.config`. The settings behavior is documented in the [API README](../../README.md#startup-settings). A configuration error is a startup failure, not the shared public HTTP error envelope.

## Boundaries awaiting their creating tasks

| Concern | Existing rule | Required follow-up |
|---|---|---|
| IDs | UUID-based opaque string identifiers at public boundaries | PD-06 selects generation/version, representation helpers and tests before domain consumers rely on types. |
| Time | UTC-aware instants; no silent interpretation of naive timestamps | PD-06 selects one wire form, validation and round-trip tests. |
| Public errors | Stable safe error envelope without private state | PD-06 selects field names/common codes and implements mapping tests. Do not expose raw configuration exceptions to HTTP clients. |
| Trusted caller context | Only the server authentication boundary may establish trusted identity | PD-06 defines construction/validation; Identity later validates real credentials. No client-ID shortcut or pretend authenticated context exists here. |
| Database/session lifecycle | Database/session resources must have an explicit lifecycle and owning transaction | PD-08 selects and implements the actual database connection/session boundaries. This row is the lifecycle placeholder; no successful no-op connection, transaction or dependency check is supplied. |

These are pending task outputs, not callable interfaces, reviewed contracts or stub evidence. Concrete shared types are added only after their relevant decisions are reviewed. Database/provider access must not happen on importing `app.core`. Reuse the [canonical shared conventions](../../../../docs/conventions/shared-conventions-and-cross-domain-contract-rules.md) rather than defining alternative rules in domain modules.
