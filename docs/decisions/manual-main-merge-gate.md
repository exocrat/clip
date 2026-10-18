# Manual main merge gate

**Date:** 2026-10-19

**Origin:** PD-12 Step 7.

## Question
How should the team preserve review/check gates when private-repository host
protections are unavailable under the current plan/access?

## Options considered
- Upgrade hosting/change visibility or permissions: requires separate approval.
- Retain the private repository and approve a documented human-enforced gate.

## Selected choice
The contributor approved the [manual gate](../../CONTRIBUTING.md#approved-manual-fallback):
PR-only main changes, successful current local/hosted checks, exact revision/run
evidence, independent human peer/affected-owner approval, resolved findings and
separate exact-merge authorization. No hosting setting is changed.

## Rationale
Rulesets returned an explicit private-repository plan-upgrade requirement;
current access lacks admin rights. Protection lookup HTTP 404 was inconclusive.
The manual fallback preserves review requirements but cannot prevent bypass.

## Implications
Hosted CI success/failure-control evidence remains pending, not waived.
Approval does not authorize publication, any merge, a plan upgrade or visibility
change. Revisit supported protections through a separately approved change.
PD-18 maintains both checklists; upstream/foundation acceptance gates remain.

## Approver
Current integration contributor, explicit approval of the Step 7 fallback.
No person inferred from stream labels.

## Supersedes
None.
