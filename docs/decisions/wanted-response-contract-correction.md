# Wanted-response success body and owned backend correction

**Date:** 2026-10-25
**Origin:** SE-02 Step6 audit and human-verified corrective checkpoint.

## Question

The reviewed Search contract requires a conversation result on201/200, but its
alternate200 source/generated declaration had no body. The Search response route
was also absent, leaving response capability/serialization checks incomplete.

## Options considered

- Correct Search's200 model to the documented ConversationStartResult, implement
  the reviewed origin-owned delegation, then test both outcomes and row locking.
- Keep an empty repeat response. It cannot supply the existing thread ID after a
  lost first result and contradicts the documented same-pair retry behavior.

## Selected choice

`contracts/source/search.py` now declares ConversationStartResult on both success
statuses. Regenerate through the existing registry; never edit generated files.
This pre-implementation correction retains HTTP version0.1.0 and generator2:
path/input/documented semantics are unchanged, and no implemented producer or
accepted live behavior is being changed. Generated consumers must refresh the
200 result type. A compile-only TypeScript consumer covers both statuses and
rejects a missing conversation ID. Other domain declarations remain unchanged.

Implement Search's regular-only response route. Trusted identity and live regular
eligibility precede origin use. Missing/retired/pending is safe404, self403;
closed requests use only same-caller read-only lookup, with absent pair404. An
open origin uses bounded public create-or-existing.201/200 always return typed
thread ID/created fields. Temporary callers cannot create or perform that lookup.
Unknown/lost results503 recover through the same request/responder pair; there is
no fake thread, local thread storage, or invented C operation-ID argument.

## Rationale

Clients need the existing thread ID to recover after timeout or closure. The
origin owner must serialize state changes with the public call while preserving
the acyclic ownership boundary and independent Conversations enforcement.

## Implications

The origin guard uses FOR NO KEY UPDATE: it conflicts with owner state writes
but permits an independent C transaction's parent FK key-share lock. Native
checks prove a separate thread/member FK fixture commits under the guard and
observe actual owner-close lock waiting during a bounded response. That fixture
is not a public C provider or a membership/uniqueness integration proof.
SE-02 and its owner/peer acceptance are recorded in the work log. This dated
correction is not a current cloud/runtime check. No migration or deployment was
part of the backend correction.

## Approver

Mohit Mahapatra, Search owner, verified the exact Step6 correction plan before
contract or handler changes. This does not replace independent peer approval.

## Supersedes

The empty alternate200 response in Search's initial declaration and its missing
local implementation. The existing capability and origin-owner rules remain.
