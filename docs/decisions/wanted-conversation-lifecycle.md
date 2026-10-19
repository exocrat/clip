# Wanted-request conversation uniqueness and closure

**Date:** 2026-10-18
**Origin:** PD-08 Step 1.

## Question
How do duplicate responses and request closure affect conversations?

## Options considered
- One conversation per request/responder pair, preserved after request closure.
- Multiple conversations per pair or terminating access on closure, adding ambiguity or removing existing communication access.

## Selected choice
Allow at most one conversation per Wanted Request/responder pair. Closing a request prevents new conversations but preserves existing participants' access. Existing account eligibility and participant authorization still apply. The responder need not own a sale listing, and temporary accounts cannot start request-response conversations.

Mohit subsequently approved reopening a non-retired request under the same ID. Preserve the same conversation uniqueness across close/reopen; reuse an existing pair's thread instead of creating another. Retired requests cannot reopen or receive new conversations.

## Rationale
A stable pair supports retry/concurrency uniqueness without discarding an existing private conversation when the request closes.

## Implications
PD-08 proposes the uniqueness constraint and origin relationships. DL-00/CN-01/SE-02 define and verify atomic creation-versus-closure behavior and duplicate results. Closure does not override later approved retention or account restrictions.

## Approver
Mohit (C), explicit approval in the execution session. The user later confirmed the PD-08 affected-owner schema gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). Domain implementation and integration checks remain with their task owners.

## Supersedes
None; refines the accepted wanted-request discovery/response decision.
