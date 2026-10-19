# DEC-11 — Re-supply active write-only credentials

**Date:** 2026-10-19

**Origin:** PD-16 Step 8 first service-plan validation failure.

## Question
How should later plans/applies satisfy the pinned provider's write-only credential schema without rotating passwords or persisting plaintext in Terraform artifacts?

## Options considered

- Omit unchanged master inputs, which the actual plan proved invalid.
- Re-supply the existing values ephemerally with unchanged versions.

## Selected choice
The user approved the second option and one fresh non-applying service plan. Supply master credential value/version pairs whenever the existing RDS/master parameter resources are configured. In service phase supply the probe pair too. Keep the write-only counters unchanged unless separately authorized rotation is intended.

For the corrected initial service plan, use the non-root profile to retrieve `/clip/test/database-master-password` version 1 into subprocess memory with decryption, verify metadata against the recorded version, and pass it only through the Terraform child's ephemeral input. Do not print it or store its plaintext in ordinary files/tfvars. Reuse the protected probe credential generated during the failed attempt; no probe parameter has been created yet. Both write-only counters remain 1. Use a fresh plan path; never reuse the errored artifact.

On apply re-supply both values; fetch the same unchanged master version and use the retained probe credential. On later authorized lifecycle plans/applies, retrieve existing approved parameter versions into memory. If values/versions change or become unavailable, stop for fresh review rather than rotating implicitly.

## Rationale
The provider validates `value_wo`/`value_wo_version` and `password_wo`/`password_wo_version` as pairs. Omission of a value with a configured version fails even when no update was intended. Supplying the existing value ephemerally preserves the intended no-rotation scope; actual plans must still prove no master/base changes.

## Implications
Steps 8/9/13, variable documentation and the runbook retain these inputs for active credential resources. Check generated/rendered plans, captured output and state for forbidden ordinary values without displaying secrets. Preserve the failed artifact privately, marked not for apply. No ordinary secret-value argument, version bump, apply, RDS restart, task execution or cleanup is authorized by this decision. Each later cloud action retains its separate approval gate.

## Approver
User in the current session; personal name not recorded. Approved the correction proposal and one fresh non-applying plan.

## Supersedes
The instruction to omit the master input in service phase and the implication that only the probe value must be re-supplied on service apply. Write-only storage rules, role scopes and action approvals remain unchanged.
