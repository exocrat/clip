# ID-01 Step 2 — corrected request-input retry approval

Prepared 2026-10-23 09:49:29 UTC. [Previous result](runtime-attempt-result.md)
shows one failed CLI invocation, no observed task/host/submission and no retry.
The anonymous-memory-file transport passed offline validation; no live request
has been sent through it.

Approve one corrected, idempotent RunTask invocation under every resource,
message, role, image, privacy, quota, cost and cleanup condition in the
[exact run plan](runtime-run-approval.md), with only these execution clarifications:
- Supply CLI JSON via a private Linux anonymous memory file and `/proc` FD path,
  not `/dev/stdin`. No recipient-bearing argv, persistent file, logs or evidence;
  close FD after CLI completion. Validate schema offline before live submission.
- Reuse the original private clientToken and startedBy marker with identical
  task/recipient parameters; inspect existing RUNNING/STOPPED tasks and audit
  evidence first. If a matching task appears, reconcile it instead of sending.
- One corrected invocation only, no automatic additional request after error or
  uncertainty. Record only a safe error category if rejected, then reconcile.
- Recheck full preflight; record a new exact UTC start/45-minute expiry after
  approval. No old live resource exists to extend. Same existing max-one host,
  one :1 task/one fixed generic email to the same verified inbox, USD1 cap,
  startup/process deadlines, owned-task cleanup and guarded idle-host fallback.
- Suraj's RDS activity entirely untouched; no DB calls/secrets/schema work. Stop
  if another ECS operator/workload appears. No image, task-definition, role,
  AMI, service or scaling-policy change.

This is fresh permission for the corrected live invocation, not acceptance of
prior failure or permission to send multiple emails. Real signed task-role/adapter
submission, human receipt and zero owned compute remain required. Production
access and subsequent Identity implementation gates stay pending.
