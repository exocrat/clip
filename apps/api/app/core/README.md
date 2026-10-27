# Shared API core

This package contains shared technical primitives. [Canonical conventions](../../../../docs/conventions/shared-conventions-and-cross-domain-contract-rules.md) define the approved behavior and link to the PD-06 step 2 decisions. Domain authorization and business rules remain in their owning domains.

## Available interfaces

| Module | Purpose and important behavior |
|---|---|
| `identifiers.py` | `new_id`, `parse_id`, `format_id`: generate/validate UUIDv4 and emit canonical strings. `UserId` aliases the same UUID representation for contracts; it adds no validation or authorization. |
| `timestamps.py` | `as_utc`, `parse_timestamp`, `format_timestamp`: require aware instants, normalize offsets, and emit six fractional digits plus Z without silent precision loss. |
| `money.py` | `validate_paise`, `rupees_to_paise`, `format_rupees`: exact integer paise restricted to whole rupees; reject floats/booleans/fractional rupees. Signed values are representable; domains enforce their permitted ranges and zero rules. |
| `pagination.py` | Immutable `PageRequest`/`Page`, `page_parameters`, `page_from_window`: page 1/size 20 defaults, sizes 20/50/100, offset and size+1 lookahead. Queries must first authorize/filter and sort with an ID tie-breaker. The helper preserves query order; it cannot enforce SQL ordering or snapshot consistency. |
| `errors.py` | `ErrorSpec`, `FieldError`, `PublicError`, `install_error_handlers`: reviewed public codes/messages and safe response mappings. Raw exception messages and validation inputs are excluded; generic schema failures identify only body/query/path/header/cookie to avoid leaking nested input keys. Domain details use reviewed field/code pairs. |
| `auth.py` | Immutable `CallerContext` and `require_caller`: user UUID, regular/temporary class, UTC validity deadline. Only trusted server wiring may set ASGI scope `clip.caller`; headers/body/query IDs are ignored. Without Identity wiring the dependency denies access. Context construction alone proves no identity. |
| `runtime_bindings.py` | Trusted immutable async callback snapshots in ContextVar scopes; generated typed dispatch strictly revalidates model data (including constructed instances), fails safe503 without binding and restores nested/parallel contexts. No domain imports, DB/provider discovery, environment selector or authorization policy. |
| `logging.py` | `SafeJsonFormatter`, `RequestLoggingMiddleware`, `configure_logging`: server request IDs in request-local context, response `X-Request-ID`, and errors; bounded metadata-only JSON. Application/Uvicorn messages, exception text and unknown extras are discarded. Integrations must review other library logs separately. |
| `config.py` | Typed process settings and safe startup failures, disabled provider defaults, explicit local/test fake selections, production rejection of fake providers/development auth/debug, and an optional masked/validated PostgreSQL DSN. |
| `database.py` | Creates the process-level async Psycopg pool with a zero-connection startup minimum and one-connection initial bound. FastAPI owns its lifetime; domains acquire their own connections and transactions. |

`main.py` installs common error handlers and request correlation; `/health` remains the only application route. Its lifespan opens/closes an optional pool only when a DSN is explicitly configured; it imports no private domain implementation, and lazy startup does not establish database connectivity. `/health` remains process liveness, not database readiness. HTTP requests that fail before response headers receive the safe 500 envelope. A response failing after headers (streaming or background work) cannot be replaced; the middleware reports a generic transport failure without exposing the original exception. `configure_logging` replaces application/Uvicorn handlers and disables propagation on those named loggers; it never enables request-body logging. Unknown routes use a fixed route marker, never their raw path/query.

The Conversations-owned [`origin_retirement.py`](../domains/conversations/origin_retirement.py) provider implements `get_origin_activity` and `mark_origin_retired`. [`thread_creation.py`](../domains/conversations/thread_creation.py) implements the Listing and Wanted Request open/create operations. Both providers use their own database transactions; thread creation calls Identity through its public eligibility interface and trusts server-resolved origin contexts rather than querying Listings or Search. Both are tested directly but are not composed into the application; no shared entry point imports private domain code. Retirement does not clear origin content, and isolated provider tests do not prove real Listings/Search integration.

`ErrorSpec` messages and `FieldError` values must be code-owned, reviewed public metadata. Do not construct them from user/provider text. The logging allowlist is an additional safeguard, not permission to put private content into an allowed field.

## Pending integration and checks

PD-06 step 3 implements these interfaces. Step 4 adds the focused shared-core suite under `apps/api/tests/core/`, including format/parse boundaries, error mapping, page-window ordering, caller construction/expiry, redaction/correlation and settings guards. Step 5 adds `test_security_boundaries.py` for client-claim spoofing, server-context positive controls, and fresh-process production startup rejection. Step 6 reviews fixtures, captured output and the task-wide acceptance set; the work log records its execution/verification state and the remaining peer-review/main gates. No domain, sign-in, provider, database, or deployment completion is implied.

Identity must validate actual credentials, eligibility and revocation before supplying caller context; each domain enforces resource access. PD-10 provides [explicitly selected scripted test providers](../../../../tests/fixtures/core/README.md) for identity/email/storage; normal API wiring installs none. ID-01/CN-03 implement real providers; reserved settings do not simulate authentication/delivery. PD-08 implements database/session lifecycle. Domain contracts specify transactions, idempotency, duplicate behavior and notification durability; core performs no automatic write retries. Importing core must not contact a database or provider.

Step9 adds `runtime_claims`/`runtime_claim` for immutable scoped owner-reviewed
claim records. This technical storage authenticates nothing; the owning provider
checks the record type, actor and scope after trusted composition establishes its
preconditions. Nested replacement/restoration and parallel isolation apply;
HTTP composition clears ambient claims before processing each request.
