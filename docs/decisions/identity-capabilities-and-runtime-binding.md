# Identity capabilities and scoped runtime eligibility binding

**Date:** 2026-10-24
**Origin:** ID-01 Step8 verified plan, recorded2026-10-24 05:50:29 UTC.

## Question
How are the approved regular/temporary rules enforced and the generated public
eligibility declaration connected without business logic in generated code?

## Selected choice
Aditya verified the Step8 plan. Implement fresh Identity account eligibility and
capability policy. Both classes may browse/search sale/open wanted content,
save listings, manage own wanted requests/profile/contacts, start listing
conversations, use existing authorized conversations and submit offers/share
selected own contacts. Only regular users may manage sale listings or initiate
wanted-response conversations. Do not deny temporary wanted authors' existing
conversations. Owners still check resource ownership/membership/state.

Expired/pending/revoked/removed accounts and stale/mismatched caller facts fail
closed. Public check_account_eligibility keeps the existing async UUID/optional
exact-class signature and returns only AccountEligibility{eligible:bool}; no
new HTTP lookup, identity directory or private denial data. Targets originate
from trusted context/authoritative owner relationships, not browser IDs.

A shared technical ContextVar scope holds immutable, explicitly supplied async
callbacks for the current trusted runtime/request. No process-wide mutable
provider, environment selector, automatic import binding or fake fallback.
Unbound/wrong-result/dependency failures return safe503. Validate result models
strictly and suppress private exception payloads. Scope resets on exit/failure;
parallel app/runtime contexts cannot overwrite each other.

Canonical Identity source adds a reviewed runtime-binding metadata set for only
check_account_eligibility. Its source callable still refuses execution. The
format2 generator transforms only that declared body into a typed dispatcher
with result validation; no SQL/business policy/private implementation import in
public.py and no HTTP/schema/type shape change. Other generated domains/contact
functions retain their original refusing behavior. Update generation/boundary
checks to assert this narrow exception; never hand-edit generated outputs.

Explicit HTTP middleware installs its own real eligibility service per request;
workers must provide an explicit trusted scope too. The existing own-session
summary uses fresh capability enforcement. Test probes are not marketplace API
implementations; Step14 retains the final cross-domain matrix. No runtime/cloud/
provider/key/scheduler activation or readiness closeout is authorized here.

## Approver
Aditya(A), explicit verification of Step8 capability matrix and dispatcher plan.

## Supersedes
Extends the [contract generation decision](contract-source-and-generation.md)
with a thin approved runtime adapter, preserving canonical declaration separation,
all reviewed signature/ownership rules and the existing wanted-request policy.

## Step9 extension

The [verified Step9 plan](identity-contact-sharing-and-cleanup.md) adds only
get_shareable_contact_options and get_selected_own_contacts to the selected
Identity dispatch metadata, preserving declaration-only canonical bodies and
unimplemented notification recipient resolution. A separate immutable technical
claims scope carries owner-checked sharing context. HTTP middleware clears
ambient claims and binds its real providers per request; trusted Conversations
composition installs an inner scope after its authorization/confirmation checks.
No browser input, import or object construction installs authority automatically.
