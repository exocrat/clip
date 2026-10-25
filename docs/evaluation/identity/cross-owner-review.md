# ID-01 cross-owner changes and review handoff

Prepared 2026-10-25 06:07:40 UTC by Aditya (A). Purpose: one place for the people
whose features use Identity to understand **what changed, why, and what to check**.
This includes the whole ID-READY branch, not just the latest logging/migration work.

**Review source:** `task/id-ready-overnight-prep` at `a76d3e81e1770bd01d4a7ffcddae2307b1c24872`.
Refreshed 2026-10-25 20:05:44 UTC after the hosted-test startup addition; original prepared date retained above.
**Comparison base:** fetched `origin/main` at `6c860603bdd81a98485e721d789b557c5d433948`.
The pending migration-review candidate and this handoff are documentation additions;
they do not change the implementation pinned above. Refresh this comparison if
source or main advances before approval.

## Current review focus — 2026-10-25 09:05:19 UTC

Aditya reports that Suraj found **no decision-level conflict**. The remaining
technical focus is migration compatibility and shared cloud configuration (§§7–8).
This records Suraj's reported feedback, not a completed migration/cloud check or
approval of an exact source revision. Those checks remain pending.

For a focused review, verify these items in order:

1. Compare the fourteen upstream migration files with the pinned base; inspect the
   three added Identity migrations and the manifest hashes. Confirm shared FKs,
   retirement behavior and the first-apply effect on each owner's schema.
2. Review the proposed whole-chain apply: seventeen migrations through
   `20261025013000`, expected inventory of 37 tables/33 functions/43 triggers.
   Local lifecycle checks passed; **the shared RDS chain has not been applied**.
   A fresh check of all four domain namespaces and the migration tracker is still
   required. The earlier Identity-only inspection cannot establish a clean shared DB.
3. Review the separate Identity runtime role proposal for least privilege and
   credential separation. **No permanent Identity login, grants or DB URL were
   installed by the successful logging probe**; that probe rolled back its changes.
4. Compare the shared Terraform changes with the existing deployment: the AMI pin
   preserves `ami-0c10ee7b040aa465e`; the desired SES sender is
   `verify@clip-iisc.site`, while the last inspected live policy still used
   `no-reply@clip-iisc.site`. Sender permission and scoped runtime secret-read IAM
   remain work to review/apply, not completed configuration.
5. Confirm shared operations cannot interrupt Listings: serialized windows,
   fresh idle-state checks and cleanup restricted to owned resources. The temporary
   builder was removed; retained task definitions/images are not running compute.
   No NAT redesign was applied. The development scale-to-zero override must be
   removed before production; AWS's underlying managed protection was not disabled.

The [apply review candidate](id-01-step-12/shared-migration-apply-review.json)
is explicitly **not executable approval**: image/affected-owner review and a new
exact cloud/DDL approval are still required. No cloud query or mutation was performed
for this clarification. Keep the protected Listings client-write integration check
in §2 visible as well; absence of a policy conflict does not prove runtime compatibility.

Detailed local audit and the prepared post-merge/live acceptance sequence are in
[the integration handoff](integration.md#pre-merge-migration-and-configuration-audit--2026-10-25-093232-utc).

## People and fastest review order

Aditya asked Suraj to review Listings impact and Rahul to review Search impact.
The repository roster currently maps **Suraj (B) → Listings, Mohit (C) → Search,
Rahul (D) → Conversations/offers**. Rahul is also Aditya's primary Identity peer.
Rahul can review the requested Search interactions; include Mohit for Search-owner
approval. This handoff does not reassign ownership.

| Reviewer | Start here | Main decision |
|---|---|---|
| Suraj | §§1–3, 6–8 below | Listings eligibility correction, session/CSRF integration, unchanged seller protections, shared page/cloud effects. |
| Rahul | §§2–5, 7–9 | Identity/security peer review, requested Search policy review, and his Conversations/contact/offer interfaces. |
| Mohit | §§2–3, 6–7 | Search/Wanted/Saved policy, shared types/pages, schema integration. |

Read the sections first, then inspect the linked paths/diff. Record findings and
approval against the exact source head, using [the peer-review prompt](../../prompts/peer-review-prompt.md).
Reading this file or Aditya's step verification does not constitute owner approval,
a merge authorization, or permission to apply cloud/database changes.

## 1. Direct edits in Listings-owned files — Suraj

| Changed file | What changed and why | What Suraj should check |
|---|---|---|
| [integrations.py](../../../apps/api/app/domains/listings/integrations.py) | `PublicListingsIdentity.account_is_eligible` now calls Identity with `required_class=None` instead of `"regular"`. The old blanket filter denied eligible temporary buyers even for browsing and allowed buyer actions. | This is an active-account lookup, not a complete permission decision. Existing trusted-caller regular-only seller checks in Listings must remain authoritative. Check browse/offer/selected-buyer flows as well as seller denial. |
| [test_offer_boundary.py](../../../apps/api/tests/domains/listings/test_offer_boundary.py) | Replaces the old unconditional temporary-buyer rejection expectation with eligible/ineligible cases. A permitted offer also checks the current seller's eligibility. Uses a non-expiring synthetic caller date for this fixture. | Eligible temporary buyer reaches the existing offer command; ineligible buyer gets denied without persistence; seller/ownership/availability guards still run. This is a controlled public-port test, not final Conversations integration. |
| [test_image_upload_service.py](../../../apps/api/tests/domains/listings/test_image_upload_service.py) | Adds an autouse fixture used only in this test module aligning authentication time with the module's existing synthetic service clock. Calendar time had expired its fixed one-day sessions. Pytest restores the patch per case. | It changes test time only; production expiry comparison and image service behavior were not relaxed. |
| [Listings Terraform README](../../../infra/terraform/domains/listings/test/README.md) | Corrects one relative link to the shared password-logging decision. | Documentation-only; no Listings Terraform resource or lifecycle script change. |

Aditya explicitly authorized the narrow adapter/test corrections; Suraj's affected-owner
review is still needed. Listings service/store/routes/storage implementation is
unchanged relative to the base; its web request adapter now adopts only shared
session transport. In particular, `_require_regular_eligible`
still rejects a temporary seller. The adapter signature did not change.

## 2. One shared API, real request authentication — all owners

**Paths:** [application.py](../../../apps/api/app/application.py),
[main.py](../../../apps/api/app/main.py), [Identity HTTP](../../../apps/api/app/domains/identity/http.py),
[settings](../../../apps/api/app/core/config.py), [boundary checker](../../../scripts/check_boundaries.py).

- Moved reusable app construction into side-effect-free `app.application.create_app`;
  `app.main` preserves its established `settings`, `app` and factory exports.
- Explicit `IdentityHttpDependencies` can install the real Identity middleware/routes
  into the same app that already owns Listings routes, state and pool lifespan.
  Accepted Search/Wanted/Saved/Hybrid wiring and cancellation-safe pool cleanup
  remain. main.lifespan/probe hooks delegate to the same lifecycle. The import
  allowlist names only exact composition/facade imports.
- Fresh session authentication supplies `scope["clip.caller"]` and `scope["clip.session"]`.
  Incoming/ambient caller facts are cleared. Domain code still uses trusted core
  caller handling and owning-domain authorization; browser actor IDs/classes are not authority.
- When installed, middleware covers the shared app, with `/health` bypassed. It
  checks transport/origin before session access, applies private `no-store` responses,
  and checks current account/session state so logout, expiry and revocation take effect.
- **Protected browser writes need** an allowed Origin, `X-CLIP-Request: 1`, the session
  cookie and `X-CSRF-Token` obtained through `/auth/csrf`. Public authentication writes
  have their explicit exceptions to session/CSRF requirements, not to transport/origin checks.
- Default `app.main:app` remains Identity-unbound. Explicit Identity composition rejects
  production, development-auth, isolated fixed-caller and hosted-demo combinations;
  a missing DB/dependency bundle fails closed. Nothing silently enables fake auth.

**Local browser transport integrated:** Listings listingsApi.ts and Search
wantedApi.ts now call shared/http/sessionFetch.ts. Protected requests fetch a fresh
token and carry both headers; token failure prevents that request, with no cache or
automatic transport replay. Identity uses the same helper and /api prefix normally;
explicit Identity preview keeps its existing unprefixed route/build guard. Each
feature retains payload validators, safe errors and operation IDs. No feature imports
Identity-private code; presigned S3 bytes retain their separate transport. Review
Suraj/Mohit's narrow adapter/test-fixture diffs. Real TS/HTTP/SQL writes/denials pass;
physical browser, trusted proxy and deployed provider acceptance remain pending.

**Review:** existing Listings lifespans/routes survive; public reads stay usable;
real cookie users reach permitted endpoints; stale/expired/revoked users cannot
mutate; hostile origins/CSRF fail; isolated Listings demos remain isolated. The
current middleware uses the actual transport peer; trusted proxy/TLS/client-IP
configuration remains a deployment gate, not solved by trusting forwarded headers.

Existing isolated demos now expose only the reviewed CSRF response double under
their existing profile/origin gates. The shared app installs it only in the guarded
synthetic Listings profile before SPA fallback; default/production startup has no
synthetic route. This supports demos and is not proof of real CSRF protection.

### Latest local addition: explicit hosted test startup

The ASGI composition now has a real, default-off startup path for the bounded
test profile. When enabled, it requires `CLIP_ENVIRONMENT=test`, Microsoft and
dual email selectors, the shared Listings database URL, the single reviewed HTTPS
origin, and debug/development/demo flags off. It reads only the three fixed Identity
SecureStrings, audits the separate Identity DB role, and warms the email route; it
does not migrate, provision, or send mail. The same-origin bundled UI installs the
Identity routes below `/api`, matching the web transport. `/api` is normalized only
for the existing middleware's public-auth/logout CSRF policy checks.

| Changed file | Purpose and review point |
|---|---|
| [settings](../../../apps/api/app/core/config.py) | Adds default-off test-runtime and exact-origin validation; rejects production, fake/development auth, debug, demo and incomplete configuration. |
| [runtime configuration](../../../apps/api/app/domains/identity/runtime_configuration.py) | Shares fixed-reference loading between operator-local and hosted-test setup; hosted path derives the existing browser policy and refuses unapproved runtime mode. |
| [ASGI entry](../../../apps/api/app/main.py) | Calls hosted preparation only for the explicit setting; startup fails closed if required references or the Identity role are unavailable. |
| [application composition](../../../apps/api/app/application.py) | Allows this validated test profile to serve the UI and Identity on the same app, while preserving the normal default-unbound app. |
| [Identity HTTP](../../../apps/api/app/domains/identity/http.py) | Installs existing routes under `/api` only for bundled-UI mode and retains the same origin/session/CSRF rules. |
| [boundary checker](../../../scripts/check_boundaries.py) | Adds only the exact Identity runtime preparation import to the ASGI composition-root allowlist. |
| Identity tests | Exercise settings refusal, default-unbound startup, explicit hosted composition, `/api` paths and offline secret/DB preparation. The full repository check passed locally. |

These local changes do not wire ECS, SSM/IAM, DB URLs/roles, listener, TLS or a
trusted proxy. The shared task/environment still lacks those settings and ingress
details, so no hosted sign-in claim is made. Review the exact committed source and
this separate infrastructure gate before enabling anything. Owner review remains
pending and is explicitly deferred by Aditya until the morning.

## 3. Eligibility and capabilities — Listings, Search and Conversations

**Paths:** [capabilities.py](../../../apps/api/app/domains/identity/capabilities.py),
[public Identity interface](../../../apps/api/app/domains/identity/public.py),
[capability/runtime decision](../../decisions/identity-capabilities-and-runtime-binding.md).

| Operation policy | Active regular account | Active unexpired temporary account |
|---|---|---|
| Browse/search/save sale listings; browse open Wanted Requests | Allowed subject to normal resource rules | Same |
| Create/manage own Wanted Requests | Allowed subject to ownership/state | Same |
| Initiate/respond to someone else's Wanted Request through its response-conversation path | Allowed subject to normal rules | Denied |
| Create/manage sale listings and seller image flows | Allowed subject to ownership/state | Denied |
| Listing-origin conversations, authorized existing conversations, offers | Allowed subject to membership/availability/state | Same |
| Own profile/contact management and deliberately sharing own contacts | Allowed in authorized flow | Same |

These are implemented Identity policy rules and required consumer behavior, **not
proof that every Search/Conversations endpoint has been implemented or tested**.
Temporary activation lasts14days; login/reset does not renew it. Current-account
checks deny pending, revoked, removed, expired and invalid future state. Resource
ownership, selected-buyer constraints and conversation membership remain with the owner.

`check_account_eligibility(user_id, required_class=None)` keeps its existing signature
and returns only `AccountEligibility(eligible=...)`. `None` accepts either currently
eligible class; `"regular"` adds the class requirement. The target may be offline:
this is not target-session authentication. Supply IDs from trusted caller/authoritative
relationships, not a client-selected user directory. Authenticate the actor separately.
Dependency failure is a safe503, not `eligible=True`.

Why other owners can rely on the class only after trusted authentication: Microsoft
validation checks signature/issuer/audience/time/nonce and the exact signed IISc
email domain, then idempotently binds provider/issuer/subject to an account. It
uses no client-domain or preferred-username substitute. Real Microsoft browser
acceptance remains pending. Temporary registration requires email OTP before
activation; password hashing uses Argon2, reset revokes all sessions, and retained
enrollment markers prevent renewing the14day lifetime through registration/reset.
See [Microsoft validation](../../../apps/api/app/domains/identity/microsoft.py),
[temporary accounts](../../../apps/api/app/domains/identity/temporary_accounts.py),
[sessions](../../../apps/api/app/domains/identity/sessions.py), and
[Steps3–11 evidence](implementation.md) for the Identity-owned implementation.

**Search review requested from Rahul/Mohit:** temporary Wanted authorship and browsing
must stay permitted, response initiation must remain regular-only, and save/discovery
paths must retain ownership/current-state checks. Search's private backend/frontend
and generated public declaration were not edited on this branch. Real Search endpoint
integration and the full regular/temporary/expired/revoked matrix remain pending at
ID-01 Step14/owning tasks; Step14 is outside the current ID-READY-only scope.

## 4. Public runtime bindings and contracts — all backend consumers

**Editable sources:** [identity.py](../../../contracts/source/identity.py),
[types.py](../../../contracts/source/types.py), [generator](../../../scripts/generate_contracts.py).
**Shared technical implementation:** [runtime_bindings.py](../../../apps/api/app/core/runtime_bindings.py).

- Canonical source callables remain refusing declarations. Explicit generator metadata
  creates typed runtime dispatch for exactly three Identity ports: eligibility,
  shareable-contact options and selected-own-contact values. Generated `public.py`
  contains no Identity SQL or business-policy implementation.
- `runtime_scope`/`runtime_claims` use scoped immutable snapshots and reset after exit;
  the dispatcher strictly revalidates results, fails503 when unbound/malformed and
  suppresses private dependency errors. Constructing a context authenticates nobody.
- HTTP middleware binds real providers per request and clears ambient contact claims.
  Workers/background code do not automatically inherit a usable Identity service;
  trusted composition must explicitly supply the approved bindings/context there.
- Common types add `MicrosoftLoginAttempt`, `CsrfToken` and server-only
  `ContactSharingContext`; HTTP adds POST `/auth/microsoft/login-attempts` and GET
  `/auth/csrf`. Existing eligibility/contact callable signatures stay intact.
- Shared Python types, Identity `public.py`, OpenAPI and TypeScript outputs were
  regenerated from source. Search/Listings/Conversations declaration bodies remain
  unchanged. `resolve_notification_recipient` remains unimplemented; CN-03 must not
  assume real recipient/worker wiring exists because the other three ports work.

**Review:** callers use public interfaces, the exact boundary exception does not
permit arbitrary private imports, parallel requests cannot mix providers/claims,
and unbound functions safely deny rather than fabricate success. Never hand-edit
generated outputs; use the registered generator/checks.

## 5. Private contact sharing and retention — Rahul/Conversations especially

**Paths:** [contacts.py](../../../apps/api/app/domains/identity/contacts.py),
[shared context type](../../../contracts/source/types.py),
[contact/cleanup decision](../../decisions/identity-contact-sharing-and-cleanup.md),
[cleanup implementation](../../../apps/api/app/domains/identity/cleanup.py).

Availability returns booleans only. Selected-contact values require an inner trusted
`identity.contact_share` scope containing a `ContactSharingContext` matching actor,
conversation and deliberately confirmed fields. Conversations must first check its
own participation/flow/consent rules, then install that scope **inside** the request
boundary. The middleware intentionally clears preinstalled/ambient claims.
A conversation ID, browser payload or context object alone is not proof of permission.
Only requested, confirmed, still-present own values can leave Identity; missing or
unconfirmed fields refuse rather than substitute another contact. Current account
checks run again. General profiles/session summaries contain no private contacts.

Own-contact editing does not change the login email/Microsoft identity or establish
mailbox/bank verification. Deleting a source contact is immediate; it does not reach
into Conversations to erase already shared encrypted copies. Each owner retains its
own approved cleanup duties. Identity cleanup preserves minimal account/enrollment/
idempotency references and does not cascade into other domains: OTP24h, sessions7days,
expired/revoked temporary hashes24h and profile/source contacts30days at their approved
cutoffs. Revocation/expiry denial is immediate, independently of cleanup timing.
The bounded cleanup CLI is dry-run by default; a deployed schedule is still pending.

**Review:** no arbitrary-user lookup/contact enumeration, no private values in
listing/search payloads/logs/notifications, no stale selection leaking a deleted
field, and no reverse dependency/private Conversations table query.

## 6. Shared website composition and dependency changes — frontend owners

| Changed paths | Change, reason and review impact |
|---|---|
| `apps/web/src/App.tsx`, `app/AppShell.tsx` | Public `IdentityProvider` wraps the existing router and a session/logout control joins the shell. Provider renders children through unavailable/anonymous states; it does not replace the router. It refreshes on mount/focus/visibility and clears expired/stale UI summaries. Features still own their cached data and must react safely to session changes. |
| `apps/web/src/pages/ScaffoldPages.tsx`, Identity public `index.ts` | Existing sign-in/callback/contact slots now use public Identity components; existing marketplace compositions/placeholders and Listings components remain. No new product route or private cross-feature import. |
| `apps/web/vite.config.ts` | Normal `/api`→loopback8000 rewrite preserved. Explicit development-only identity-preview proxies only approved auth/me/preview prefixes to8001 and cannot be built. `/auth/callback` stays a SPA route, not a blanket `/auth` proxy target. |
| `apps/web/index.html` | Global `no-referrer` policy avoids leaking auth URL information. Owners should account for its effect on referrer-based diagnostics/navigation assumptions. |
| `apps/web/vitest.config.ts`, package/lock files | Functional Vite configuration handled explicitly; TSX/jsdom/React interaction tests enabled. Added pinned MSAL browser SDK and DOM test dependencies. Existing React/router/Vite versions retained. |
| `.env.example`, shared Settings | Microsoft/SES/dual selectors and public sign-in build flag added; defaults stay disabled. Real Microsoft/email production enablement remains rejected/gated; explicit controlled local/test recipients capped at5. Existing storage/isolated-demo guards retained. |
| `pyproject.toml`, `uv.lock` | Added Argon2 password hashing, JWT/crypto and email-validation dependencies; boto3 patch updated. Existing main psycopg-pool dependency retained. Use locked setup; do not replace another owner's dependency pins. |

Identity UI supports Microsoft callback, temporary registration/OTP/password/reset,
own contacts and logout/expiry states. Password minimum is8; OTP verification has3
attempts shared until the latest challenge expires. These choices affect test
fixtures/expectations, not a request to duplicate auth logic in other features.
Browser session summaries are in memory; HttpOnly cookies remain authoritative.
Use only `features/identity/index.ts` public exports, including `useIdentity`.

**Review:** Listings/public pages still render if auth is unavailable; previews cannot
be built/deployed; stale reads do not resurrect a logged-out UI; marketplace state
refresh/invalidation is coordinated; frontend summaries never authorize an API call.
Only the narrow Listings/Search transport adapters were edited; their business
logic and all Conversations feature implementation remain unchanged.

## 7. Database and validation changes — all schema owners

The branch preserves all14upstream migrations byte-for-byte and adds only3Identity
forwards: `20261023173439` (bounds/revocation/external identity), `20261023192856`
(OTP state), `20261023202807` (session/login state). They alter Identity-owned
objects, add7Identity tables and reuse shared FKs. No new reverse cross-domain
queries/cascades were introduced by these three forwards. Their occupied down
paths refuse unsafe security-state loss; live down/reset is not approved.

A fresh environment needs the **whole17file chain**, because the Identity forwards
need the original shared tables. It creates all4domain namespaces, so deployment
scope is wider than the3new SQL files even though existing SQL is unchanged.
[Manifest](id-01-step-12/shared-migration-manifest.json) pins versions/bytes;
[apply review candidate](id-01-step-12/shared-migration-apply-review.json) records gates.

[check_database.py](../../../scripts/check_database.py), [native-checks.sh](../../../database/tests/native-checks.sh)
and Identity SQL tests now cover the combined chain, clean/repeat/upgrades,
rollback/reapply/atomic refusal and structural inventory37tables/33functions/43triggers.
Native script edits are not evidence of a new native macOS run. Contract-generation/
runtime-binding tests also changed to check the new generated exception.

[Role proposal](../../../database/roles/identity-runtime.sql.proposed) and Identity
metadata/setup/migration tools are preparation, not automatic startup. A separate
Identity login is proposed; no ownership, other-domain access or global PUBLIC
revocation is granted by the proposal. The proposal keeps Identity credentials separate from Listings; other-domain credentials are not changed.
The migration runner rejects unknown/partial/manual namespace state and unreviewed
images, uses verified TLS/stdin-only credentials, preserves a failed committed prefix,
and removes only its owned temporary containers. No live fixture/smoke DML is implied.

**Review:** each owner accepts its shared first-apply impact and FK/retirement
compatibility; no missing baseline is skipped and no published SQL rewritten;
no accidental app-role privilege broadening or destructive cloud cleanup. A fresh
all4namespace preflight is required; earlier cloud inspection established only that
Identity tables and public migration tracker were absent.

## 8. Shared cloud, mail and lifecycle impact — Suraj/shared operator

| Changed area | Why and impact |
|---|---|
| `infra/terraform/shared/test/base.tf`, `locals.tf`; image-pin decision | Replaced mutable recommended-AMI lookup with the exact existing deployed AMI, retaining sensitivity marking. This prevents an unrelated SES/IAM plan from upgrading the shared host. Any future AMI upgrade needs its own review. |
| `infra/terraform/shared/test/identity-email.tf` | Added narrowly scoped SES permission and optional exact sandbox-recipient identity. Source now requests `verify@clip-iisc.site`; last inspected live policy still used the old sender. A source diff is not proof that sender-policy transition was applied. |
| `infra/terraform/domains/identity/test/*` | Separate temporary AMD64 image builder and one-shot email-task preparation/history. Builder was cleaned up; task registration/image retention is distinct from running compute or sending. No Listings Terraform lifecycle resources changed. |
| Identity SES/Resend adapters and SSM router | Verification/reset mail can prefer one provider and try the other once, same message/OTP,4hour lazy configuration cache. Uncertain failures may produce duplicates. Controlled recipient/production guards remain; general provider readiness is pending. CN-03's notification retry/recipient/scheduling contract is separate. |
| Secret/DB runtime preparation | Persistent authentication keys provisioned securely; separate Identity DB URL/login and task secret-read permissions remain pending. No master credentials in app runtime or source. Resend credential previously supplied in chat still needs private rotation. |
| Shared ECS/RDS operation | Runs use serialized exact windows, one owned task/host, guarded cleanup. Development prompt scale-to-zero did not disable AWS's underlying15minute managed behavior; restore normal reliance/remove the development override before production. |
| `.gitleaks.toml` | Adds only an exact public image-tag/path exception; default rules and existing checksum exception retained. No general secret-scan bypass. |

Last confirmed cloud baseline is **2026-10-25 05:41:05 UTC**: original RDS stopped,
cluster/ASG/API capacity0, no sessions, owned probe host/root removed. The live
logging/default probe passed and rolled back; no migrations/permanent app login or
URL were applied. Earlier attempts failed on AWS capacity and were recorded honestly.
NAT cost alternatives are a [deferred note](../../environment/shared-test-foundation-proposal.md),
not an accepted network change. Shared RDS/ASG state and concurrent users must be
rechecked before every future run; do not stop Suraj's work on stale evidence.

Local preparation found a concrete image trust-store gap, still unresolved
after accepted-main integration at the source pinned in this file's header. The cached AMD64 base image contains none of the regional RDS roots used
by the probe, while app TLS requires system roots. See the
[offline evidence and proposed coordinated fix](integration.md#explicit-local-runtime-preparation-and-image-trust-finding--2026-10-25-114606-utc).
Shared Dockerfile now installs these roots and points bundled libpq at the OS
CA file. The stronger native TLS proof and remaining platform/runtime gates are below.

### Prepared shared image correction — 2026-10-25 18:00:39 UTC

The current pinned source addresses the trust finding: apps/api/Dockerfile installs pinned public
regional roots and explicitly selects the standard OS CA file for bundled libpq.
This affects system-root TLS clients across the ordinary image; Hybrid inherits
only from a corrected parent. No provider/URI/hostname policy change. Four actual
native ARM64 image checks pass, including real synthetic TLS success and wrong-
hostname/unknown-CA refusal; all148distribution roots remain. See
[exact source/image/check evidence](id-01-step-12/image-trust-local.json) and the
[shared decision](../../decisions/identity-rds-system-trust.md). B/C/shared image
review, AMD64/Hybrid proof and real deployed RDS checks remain pending; no apply
or publication is authorized. Refresh pins if source/main advances before review.

### Prepared shared browser transport — 2026-10-25 19:00:23 UTC

The previously identified Listings/Search browser-header gap is now corrected
locally in the current pinned source: both narrow adapters use
shared/http/sessionFetch.ts; Identity uses the same helper and normal /api route.
Fresh protected CSRF, marker/no-store/same-origin and no automatic transport retry;
feature payloads/validators/operation keys/S3 bytes unchanged. Existing isolated
demos supply only a guarded contract double, never a client-side bypass.
[Actual TS/HTTP/SQL evidence](id-01-step-12/browser-transport-local.json) covers real
cookie-authorized writes and missing/stale/temporary/logout denials. Suraj/Mohit
review the bounded adapters/demo fixtures; Rahul remains the primary Identity peer.
This closes the local transport gap, not real browser/provider/ID-READY acceptance.
The current source pin includes these changes; acceptance still requires review.

## 9. Evidence and requested review outcome

Latest source-identical full gate: **1800Python passed,24skipped,
94data,257web passed/3skipped; all11gates passed**, Black258files, contracts/types/boundaries/build,
real PostgreSQL18.6 migration lifecycle, Gitleaks8.30.1. Runner/probe focused suite:
17passed. Recorded results are not a new run performed to write this document.
Local combined API/session/Listings/contact tests cover real SQL, cookies, temporary
seller denial, current-session rechecks and Origin/CSRF; controlled Microsoft/mail
ports are not real provider evidence. Earlier separate Listings DB workflow passed.
See [integration evidence](integration.md) and [implementation record](implementation.md).

Required real work remains: shared schema apply, Identity login/URL and scoped
runtime IAM, proxy/TLS/public routing, provider/browser/phone/cleanup scheduling,
independent review/current CI and readiness merge. No ID-READY or full FR-03
acceptance is claimed. End-to-end consumer matrix remains Step14 later.

Please return **findings with path/behavior/severity**, then an explicit accept or
changes-required decision for your affected area and the exact source head.
Especially answer: does Listings retain seller protection while allowing permitted
temporary buyers; is the browser CSRF/public transport follow-up understood; is
Wanted-response policy correct; is contact disclosure gated by real owner checks;
and is the shared first-apply scope safe for your work?

| Review area | Requested reviewer | Status |
|---|---|---|
| Identity/security and Conversations/contact integration | Rahul | Pending |
| Listings adapter/tests/shared page/client/cloud impact | Suraj | Pending |
| Search/Wanted/Saved policy/shared types/pages/schema | Mohit; Rahul's requested cross-review | Pending |
| Shared manifest/image/first apply | Affected owners + Aditya/operator | Pending; no live apply authorized |

## 10. Complete shared/other-owner source inventory

The following is the net path inventory at the pinned base/head for code, config,
contracts, migration/validation tools and other-owner documentation outside the
Identity-owned implementation/tests. Related changes and reasons are grouped above.
Pure Identity files are grouped by consumer impact above; historical reports were
compacted into the evidence index/archive map, not treated as implementation changes.
Canonical documentation changes carry these same rules: `contracts/identity.md`,
`contracts/combined.md` and contract README explain the HTTP/typed runtime boundary;
`docs/architecture/frontend-collaboration.md` records public slots/writer boundaries;
`mvp-database-schema.md` and database README describe the3forwards/combined chain.
Changed decisions cover runtime binding, contact sharing, sessions/cleanup, temporary
storage, provider/email safety and the shared AMI pin. Environment command/secret/
provider/cloud records and API/web/root READMEs document invocation, gating and
observed live state. Evidence consolidation adds navigation/archive references,
not new runtime permissions. These documentation changes do not replace approvals;

the work log retains original ownership approvals, exact checks and pending gates.

To inspect the complete branch diff, including all Identity files and historical
evidence/documentation, run from the clone (read-only):

```sh
git diff --name-status 6c860603bdd81a98485e721d789b557c5d433948 7bc5b6083caac673ce264b6daa6675d5ddf3a20f
git diff 6c860603bdd81a98485e721d789b557c5d433948 7bc5b6083caac673ce264b6daa6675d5ddf3a20f -- PATH_TO_REVIEW
```

```text
.env.example
.gitleaks.toml
README.md
docs/decisions/identity-test-runtime-activation.md
apps/api/Dockerfile
apps/api/README.md
apps/api/app/application.py
apps/api/app/contracts/domain_types.py
apps/api/app/core/README.md
apps/api/app/core/config.py
apps/api/app/core/runtime_bindings.py
apps/api/app/domains/listings/integrations.py
apps/api/app/main.py
apps/api/app/domains/identity/runtime_configuration.py
apps/api/tests/core/test_runtime_bindings.py
apps/api/tests/core/test_provider_settings.py
apps/api/tests/test_health.py
apps/api/tests/domains/identity/test_main_runtime.py
apps/api/tests/domains/identity/test_application_composition.py
apps/api/tests/domains/identity/test_runtime_configuration.py
apps/api/tests/domains/listings/browser_demo.py
apps/api/tests/domains/listings/test_image_upload_service.py
apps/api/tests/domains/listings/test_offer_boundary.py
apps/api/tests/domains/search/wanted_ui_preview.py
apps/web/README.md
apps/web/index.html
apps/web/src/App.tsx
apps/web/src/app/AppShell.tsx
apps/web/src/features/listings/listingsApi.ts
apps/web/src/features/search/wantedApi.ts
apps/web/src/pages/ScaffoldPages.tsx
apps/web/src/shared/http/sessionFetch.ts
apps/web/tests/helpers/csrf.ts
apps/web/tests/listings-api.test.ts
apps/web/tests/listings-image-api.test.ts
apps/web/tests/session-fetch-http.test.ts
apps/web/tests/session-fetch.test.ts
apps/web/tests/wanted-api.test.ts
apps/web/vite.config.ts
apps/web/vitest.config.ts
contracts/README.md
contracts/combined.md
contracts/generated/openapi.json
contracts/generated/types.gen.ts
contracts/identity.md
contracts/source/identity.py
contracts/source/types.py
database/README.md
database/migrations/20261023173439_identity_account_profile_integrity.sql
database/migrations/20261023192856_identity_otp_transactions.sql
database/migrations/20261023202807_identity_sessions_and_login.sql
database/roles/identity-runtime.sql.proposed
database/tests/identity-otp-smoke.sql
database/tests/identity-schema-smoke.sql
database/tests/identity-session-smoke.sql
database/tests/identity-upgrade-check.sql
database/tests/identity-upgrade-seed.sql
database/tests/native-checks.sh
infra/terraform/domains/identity/test/.terraform.lock.hcl
infra/terraform/domains/identity/test/README.md
infra/terraform/domains/identity/test/email-smoke-container.json
infra/terraform/domains/identity/test/email-smoke.tf
infra/terraform/domains/identity/test/main.tf
infra/terraform/domains/identity/test/versions.tf
infra/terraform/domains/listings/test/README.md
infra/terraform/shared/test/README.md
infra/terraform/shared/test/base.tf
infra/terraform/shared/test/identity-email.tf
infra/terraform/shared/test/locals.tf
package-lock.json
package.json
pyproject.toml
scripts/check_boundaries.py
scripts/check_database.py
scripts/generate_contracts.py
scripts/identity_cleanup.py
scripts/identity_readiness.py
scripts/identity_runtime.py
scripts/identity_ui_preview.py
tests/contracts/test_domain_declarations.py
tests/contracts/test_generation.py
tests/contracts/test_identity_declarations.py
tests/contracts/test_runtime_binding_generation.py
uv.lock
```
