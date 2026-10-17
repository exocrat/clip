# Shared API core

This package contains shared technical primitives. [Canonical conventions](../../../../docs/conventions/shared-conventions-and-cross-domain-contract-rules.md) define the approved behavior and link to the PD-06 step 2 decisions. Domain authorization and business rules remain in their owning domains.

## Available interfaces

| Module | Purpose and important behavior |
|---|---|
| `identifiers.py` | `new_id`, `parse_id`, `format_id`: generate/validate UUIDv4 and emit canonical strings; IDs grant no authorization. |
| `timestamps.py` | `as_utc`, `parse_timestamp`, `format_timestamp`: require aware instants, normalize offsets, and emit six fractional digits plus Z without silent precision loss. |
| `money.py` | `validate_paise`, `rupees_to_paise`, `format_rupees`: exact integer paise restricted to whole rupees; reject floats/booleans/fractional rupees. Signed values are representable; domains enforce their permitted ranges and zero rules. |
| `pagination.py` | Immutable `PageRequest`/`Page`, `page_parameters`, `page_from_window`: page 1/size 20 defaults, sizes 20/50/100, offset and size+1 lookahead. Queries must first authorize/filter and sort with an ID tie-breaker. The helper preserves query order; it cannot enforce SQL ordering or snapshot consistency. |
| `errors.py` | `ErrorSpec`, `FieldError`, `PublicError`, `install_error_handlers`: reviewed public codes/messages and safe response mappings. Raw exception messages and validation inputs are excluded; generic schema failures identify only body/query/path/header/cookie to avoid leaking nested input keys. Domain details use reviewed field/code pairs. |
| `auth.py` | Immutable `CallerContext` and `require_caller`: user UUID, regular/temporary class, UTC validity deadline. Only trusted server wiring may set ASGI scope `clip.caller`; headers/body/query IDs are ignored. Without Identity wiring the dependency denies access. Context construction alone proves no identity. |
| `logging.py` | `SafeJsonFormatter`, `RequestLoggingMiddleware`, `configure_logging`: server request IDs in request-local context, response `X-Request-ID`, and errors; bounded metadata-only JSON. Application/Uvicorn messages, exception text and unknown extras are discarded. Integrations must review other library logs separately. |
| `config.py` | Typed process settings and safe startup failures, disabled provider defaults, explicit reserved local/test fake selections, and production rejection of fake providers/development auth/debug. Real provider selection remains unavailable until its implementation task adds validated configuration. |

`main.py` installs common error handlers and request correlation; `/health` remains the only application route. HTTP requests that fail before response headers receive the safe 500 envelope. A response failing after headers (streaming or background work) cannot be replaced; the middleware reports a generic transport failure without exposing the original exception. `configure_logging` replaces application/Uvicorn handlers and disables propagation on those named loggers; it never enables request-body logging. Unknown routes use a fixed route marker, never their raw path/query.

`ErrorSpec` messages and `FieldError` values must be code-owned, reviewed public metadata. Do not construct them from user/provider text. The logging allowlist is an additional safeguard, not permission to put private content into an allowed field.

## Pending integration and checks

PD-06 step 3 implements these interfaces; persistent unit/adversarial tests and task-wide review remain steps 4–6. The existing PD-05 suite covers the earlier health/configuration surface only. No domain, sign-in, provider, database, or deployment completion is implied.

Identity must validate actual credentials, eligibility and revocation before supplying caller context; each domain enforces resource access. PD-10 implements controlled reusable provider fakes. ID-01/CN-03 implement real providers; reserved settings do not simulate authentication/delivery. PD-08 implements database/session lifecycle. Domain contracts specify transactions, idempotency, duplicate behavior and notification durability; core performs no automatic write retries. Importing core must not contact a database or provider.
