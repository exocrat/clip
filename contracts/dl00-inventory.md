# DL-00 Step 1 — existing contract and boundary inventory

**Audit date:** 2026-10-19 UTC  
**Scope:** Repository state on `task/pre-00-dl-00-foundation` at `6218f92`.

This inventory is a pre-draft snapshot. It records existing declarations and
presentation/data boundaries; it does not treat scaffold UI, migrations, or
declaration-only functions as implemented domain behavior.

## Shared API/core surface

| Area | Existing types and operations | Contract implication |
|---|---|---|
| Identity | `UserId` is the shared `UUID` alias; `new_id`, `parse_id`, and `format_id` use UUIDv4. `CallerContext` carries `user_id`, `account_class`, and UTC `valid_until`; `require_caller` accepts only the trusted ASGI scope value. | Reuse core identifiers and caller context. Identity must establish/revoke authentication; each domain still authorizes its own resources. |
| Pagination | `PageRequest`, generic `Page[T]`, `page_from_window`, and FastAPI `page_parameters`; page size is 20, 50, or 100. | Reuse the shared page shape; each query contract must define stable sort and tie-breaks. |
| Errors | `ErrorSpec`, `FieldError`, `PublicError`, common FastAPI handlers and an error envelope. | Domain operations use stable shared errors; spell out operation-specific codes and authorization outcomes. |
| Money/time | Money helpers accept integer paise; timestamp helpers normalize aware UTC values and parse/format the shared wire representation. | Reuse helpers and state limits/nullability in domain models. |
| Logging/config | Safe JSON formatter/request middleware and shared `Settings` configuration. | Do not add private contact/message payloads or secrets to logs; provider choices remain with their owning tasks. |
| HTTP | `GET /health`, operation ID `health_health_get`, response `HealthResponse(status="ok")`. The real route is in `apps/api/app/main.py`. | This is the only currently declared HTTP operation. It is process liveness, not readiness. |

## Contract sources and generated artifacts

| Source/output | Current state |
|---|---|
| `contracts/source/health.py` | Typed `HealthResponse` and explicit `HEALTH_ROUTE` HTTP metadata. |
| `contracts/source/identity.py` | `ShareableContactOptions`, `SelectedOwnContacts`, and internal async declarations `get_shareable_contact_options(user_id)` and `get_selected_own_contacts(user_id, fields)`. These declarations do not authorize the caller; trusted-caller and own-contact authorization remain to be frozen in DL-00. |
| `contracts/source/listings.py`, `search.py`, `conversations.py` | Placeholders with no operation declarations. |
| `scripts/generate_contracts.py` | Loads only health source, creates the health-only OpenAPI schema, then invokes the pinned TypeScript generator. Its registered outputs are fixed to the health runtime declaration, OpenAPI JSON and TypeScript types. It does not discover arbitrary Python callables or generate domain `public.py` modules. |
| `contracts/generated/openapi.json`, `types.gen.ts`, `apps/api/app/contracts/health.py` | Current generated HTTP/client/runtime artifacts cover health only. |
| `apps/api/app/domains/{identity,listings,search,conversations}/` | Each directory has a README; no `public.py` or domain implementation exists. |

## Existing data and frontend boundaries

The current migration creates domain schemas/tables as follows. This is a
storage inventory only; shared PostgreSQL does not authorize cross-domain
private-table access.

| Schema | Existing tables |
|---|---|
| `identity` | `users`, `external_identities`, `contacts`, `temporary_credentials`, `sessions`, `otp_challenges`, `temporary_enrollments` |
| `listings` | `categories`, `conditions`, `sale_listings`, `image_uploads`, `images` |
| `search` | `wanted_requests`, `saved_listings` |
| `conversations` | `threads`, `members`, `public_key_versions`, `entries`, `encrypted_payloads`, `offers`, `offer_revisions`, `contact_shares`, `notification_intents` |

The approved frontend map has twelve routes, currently rendered by scaffold
components with no domain API calls or simulated domain success:

| Feature surface | Routes / composition connections |
|---|---|
| Identity | `/sign-in`, `/auth/callback`, `/account/contacts`; shared shell/session state. |
| Listings | `/listings/new`, `/listings/:listingId`, `/listings/:listingId/edit`; sale records also appear in `/my/listings`, discovery, saved items and conversation context. |
| Search | `/`, `/saved`, `/wanted/:requestId`; wanted records also appear in `/my/listings`. |
| Conversations | `/my/conversations`, `/my/conversations/:conversationId`; listing detail and wanted-request detail initiate conversations, while conversation views consume listing and authorized contact interfaces. |

The [frontend collaboration map](../docs/architecture/frontend-collaboration.md)
is the authority for page ownership and detailed presentation connections.
DL-00 must freeze server contracts and state ownership; placeholder composition
props do not establish those contracts.

## Source/generator gap and resolution

The typed Python source format can express the two required forms: explicit HTTP
metadata (`HEALTH_ROUTE`) and typed internal Python callables (the Identity
contact declarations). The present PD-11 generator only processes the former
for health and cannot yet generate generic domain interfaces. Keep the existing
single Python source of truth. DL-00 Step 11 will extend the generator to emit
reviewed declaration-only domain `public.py` files from accepted internal
signatures, while emitting OpenAPI and frontend TypeScript only for operations
with explicit HTTP mappings. Internal-only calls will not become routes by
inference. No domain signatures are defined by this inventory.
