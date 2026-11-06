# Future database backup and restore

**Origin:** PD-08 Step 7, 2026-10-18. **State:** planning handoff only.

This document specifies later work. No cloud backup, snapshot, export, restore,
cleanup or managed database operation was performed by PD-08. Native migration
down/up checks and temporary schema dumps are not managed-backup recovery
evidence. The user confirmed PD-08's carried checks and owner acceptance
complete on 2026-10-19; Linux AMD64/macOS results were confirmed on 2026-10-20
(Asia/Kolkata), but their exact machine details and raw outputs are not retained
here. NFR-07 and PRE-00 remain separate gates.

## Ownership and acceptance

| Task / owner | Required later output |
|---|---|
| [Accepted foundation handoff](../docs/status/foundation-handoff.md), integration owner with cloud-preparation owner | The shared environment and its current access, retention and cost notes are in the [Terraform runbook](../infra/terraform/shared/test/README.md) and [cloud inventory](../docs/environment/cloud-inventory.md). Foundation readiness does not accept an NFR. |
| [INT-01 Step 8](../docs/tasks/domain-task-list.md#int-01--verify-integrated-journeys-remaining-nfrs-recovery-and-total-cost), integration/release owner | After final domain migrations are integrated, configure/verify backup availability/retention, implement and validate restore/integrity/smoke tooling and its timed manifest, obtain approval, and run the real isolated restore. |
| A/B/C/D domain owners | Supply schema-aware integrity/privacy/smoke assertions for their owned records and review recovery compatibility, expiry, deletion, historical keys and side effects. Mohit supplies the coordinated migration/head evidence. |
| Named shared-cloud operator, selected before the run | Execute only the exact approved restore/cleanup window; serialize shared changes and record target identity and results. No operator is assigned by this document. |
| Human reviewer and independent peers | Review the concrete plan/revision, security/privacy boundaries, budget and evidence; approve each gated action. Step 7 verification does not approve those actions. |

[NFR-07](../docs/product/product-reference-and-architecture-decisions.md) requires
restoring the **latest available managed backup** into a usable test database
within **30 minutes**. INT-01 starts timing at the documented restore request and
ends only when required integrity and smoke checks pass. Preserve the source
database; a provider's ready status alone is insufficient. Runtime-loss recovery
is the separate NFR-06 procedure. Final project budget reconciliation remains
CLOSE-00; every recovery run must still satisfy INT-01's current budget/cap gate.

## Decisions required before implementation or execution

These are future gates, not selected values or reasons to block this planning
document. Read the current [cloud inventory](../docs/environment/cloud-inventory.md)
and [secret procedure](../docs/environment/secret-handling.md) when planning;
historical account/resource observations are not permission or current evidence.

| Decision / evidence | Required contents |
|---|---|
| Exact target | Verified account, operator identity/role, region/environment, source DB identifier, backup identifier/time and unique isolated destination. Inspect/reuse the approved shared foundation; never adopt unrelated resources or guess names. |
| Backup policy | Selected managed mechanism, schedule/availability, approved finite retention duration, maximum acceptable backup age/data-loss objective, encryption and authorized access. NFR-07 supplies a restore-time target, not a numeric RPO. Do not invent one. |
| Copy lifecycle | Explicit finite retention for automated/manual/final snapshots, exports and copies, plus owner, expiry and deletion verification. Live-row deletion does not delete backup copies. Cross-account/region copies need their own reviewed need, permissions and cost. |
| Compatibility | Final accepted repository/application revisions, complete domain migration head, PostgreSQL version/extensions/locale, roles and required infrastructure/object references. Current PD-08 head `20261018152702` is a foundation baseline, not the future final domain head. |
| Credentials/keys | Approved non-secret access references and verified recovery access. Secret-store access recovery is currently unselected; resolve it before relying on it. Never put values, ciphertext exports, private client keys or credentials in repository/chat/evidence. The server backup is not a client-private-key backup. |
| Privacy reconciliation | Reviewed source of post-backup expiry/revocation/deletion/delivery state and safe reconciliation tooling, including minimal lifetime/uniqueness guards. A stale backup alone cannot prove what was deleted or delivered afterward. |
| Exact action approval | Resources added/changed/deleted; private exposure and permissions; estimated/remaining cost; duration/concurrency/resource caps; stop conditions; rollback; cleanup/finite retention and named operator. Renew approval if any part changes. |

Record shared decisions through [decision records](../docs/decisions/README.md)
and update the canonical requirements/environment record before consumers depend
on them. Infrastructure changes belong to the assigned infrastructure owner;
PD-08 does not create commands or edit that owner's implementation here.

## Future run sequence

1. **Prepare and validate.** Verify the final accepted application/schema and
   synthetic dataset; inspect actual managed-backup availability and choose the
   latest available managed backup. If that backup cannot be used, stop and
   resolve the plan rather than substituting an older backup. Implement/register real restore and verification
   commands, validate their tools/manifests and safe-target refusals, and obtain
   human approval of the exact isolated plan before running it.
2. **Isolate before restore.** Keep the source intact. Provision only the approved
   private destination, inaccessible to ordinary application traffic. Prevent
   application workers, email delivery, scheduled cleanup and other external
   effects from starting against it. Use synthetic controlled test data and
   dedicated test permissions; never direct recovery tests at production.
3. **Restore and time.** Record UTC start at the actual documented restore
   request, backup time/identifier and provider operation ID. Restore through the
   selected managed mechanism. Retain sanitized status/failure events and
   resource metrics; stop at approved safety/cost limits. An incomplete or failed
   attempt remains an invalid/failed run, not a passing timing sample.
4. **Verify and reconcile while quarantined.** Check authenticated private
   connectivity, expected schema/head and constraints, representative user,
   listing/image-reference, Wanted Request/save, conversation/member/entry and
   offer/revision relationships. Apply the privacy/side-effect checks below
   through reviewed owning-domain tools; do not inspect private plaintext or
   copy payloads into evidence. Run final integrated application smoke checks.
5. **End timing and assess.** Stop the timer only after all required integrity,
   privacy reconciliation and smoke checks pass. Report elapsed time against
   30 minutes, with exact revisions, backup age, dataset fingerprint and test
   results. SQL rollback/reapply, an older convenient backup, or provider-ready
   timing cannot substitute for this measured path. No traffic cutover or worker
   enablement is implied by a successful isolated test.
6. **Review and clean up.** Record observed/estimated delayed costs, remaining
   resources and evidence. Delete only the approved isolated destination and
   associated test artifacts through the reviewed plan; preserve the source and
   its required backup policy. Any intentional retention needs an owner, finite
   expiry/review date, idle cost and approved cleanup route. Record actual
   cleanup evidence and remaining budget in canonical status/environment records.

## Restore-time privacy and side-effect checks

Follow [private-data retention](../docs/decisions/private-data-retention.md),
[origin retirement](../docs/decisions/origin-retirement.md), and the
[current migrations and schema guide](README.md).
Restoring older bytes must not renew an account lifetime, expiry, retention timer
or notification deadline.

- Reconcile post-backup revocations/deletions and current-time expiry before
  enabling access. Preserve original temporary activation/expiry and minimal
  enrollment guards so recovery cannot permit self-renewal. Restore must not
  silently reactivate sessions, password-reset challenges or removed contacts.
- Reapply approved content/authentication retention through owning-domain tools,
  preserving content-free origin/thread/offer uniqueness references and FK-safe
  cleanup order. Validate current-offer pointers, deletion markers and historical
  public-key references without claiming that opaque payloads prove crypto
  interoperability or client key recovery.
- Reconcile listing/upload/image metadata with actual authorized object storage.
  Do not resurrect retired details or expose deleted/missing objects merely
  because the restored database contains an old reference. Database recovery
  does not prove object-store or provider retention/deletion.
- Keep notification workers disabled until read episodes, original due/expiry,
  terminal delivery and bounded deduplication/replay state have been reconciled.
  Do not send restored pending email automatically or treat a restored outbox as
  proof an external message was never delivered.
- If trusted post-backup reconciliation state, required keys or safe tools are
  unavailable, keep the destination quarantined and report the blocker. Do not
  invent a recovery authority, bypass revocation checks or claim a usable restore.

## Evidence and handoff limits

The later manifest records approved plan/checksum, source/destination and backup
IDs, operator, UTC start/end and elapsed time, accepted revisions/migration head,
engine/configuration, logical dataset fingerprint, verification commands/results,
privacy reconciliation outcome, failures, budget/caps and cleanup/retention.
Evidence contains identifiers/counts and sanitized diagnostics, not database
contents, real contact values, credentials, private keys or encrypted payloads.

There is no implemented cloud backup/restore command in PD-08. The command
registry is updated only by the task that implements and validates it. NFR-07
restore evidence remains assigned to INT-01. PD-08 is user-confirmed complete;
PRE-00 remains pending PD-19 acceptance and the combined reviewed/main-merged
PD-17–19 handoff.
