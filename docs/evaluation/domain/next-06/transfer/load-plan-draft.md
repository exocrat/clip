# NEXT-06 load plan draft — not executable approval

This draft consumes the verified metadata and SDK bridge checkpoint. It requests
no cloud mutation yet. OriginalSteps3/4/5/6real gates and peer/source approval remain.

## Proposed direction for the exact action package

Reuse the existing project account335523638354/Mumbai foundation. Prefer the
currently configured id01 image bucket with a new reviewed run-owned namespace
(e.g. id01/next06-reference-42-v1) if its maintainer approves; it already matches
current runtime/HTTPSCORS. The alternative li02bucket needs separate compatible
runtime/IAM/CORS review; do not switch implicitly or overwrite either feature's
objects. Effective task-role permissions are unverified because policy listing
was denied; obtain owner review/export or later real approved acceptance rather
than broadening IAM just to remove metadata errors.

Use a new isolated database (candidate clip_next06_reference) on existing private
clip-shared-test-postgres, with explicit restricted load/runtime roles. Names are
proposals, not claims those databases/logins/grants exist. Verify actual schema/
roles/migration state through the separately approved private access route before
any DDL/data write. Never reset populated shared data or disable constraints.

The known existing access-host candidate is i-086045c48487471de(t3.micro,stopped)
with appSG allowed to reach RDS5432. No managed-node record is currently returned;
SSMagent/connectivity/operator permissions need verification in an approved start
window. Session Manager plugin is not installed locally. Do not start a host,
scaleASG, open ports, run remote commands, read connection secrets or install a
plugin under the read-only scope. Resolve exact route/commands and coordination
with the shared infrastructure owner in the next reviewable access package.

## Required content before requesting any mutation approval

- Exact existing resource starts/scaling choice and managed private route; account,
  source revision, operator/roles, target DB/SSLcertificate and referenced secret
  identity, never secret values. Stop on missing access rather than widening it.
- Exact reviewed source/migrations, empty-target/rollback plan, active catalogues/
  actual sensitivity threshold, pending source/peer approvals, run-owned bucket
  prefix and1,000real object references/confirmed owner attachments.
- Actual deployable Linuxmodel/helper packaging plan: the standard APIimage source
  does not package the separate semantic environment. Existing flags remainoff
  until supported runtime packaging and complete coverage can be verified.
- Current official pricing for observed RDSdb.t4g.micro/20GiBgp3, hostt3.micro and
  S3~0.926GB/1,000PUTs/verificationGETs plus relevant network/transfer/storage
  effects. Explicit incremental cost cap, time window and cleanup/retention owner;
  existing charges are not included as a falsezero baseline. No price invented here.
- Separate precise approvals for starts/access/secret retrieval/SQL setup/load,
  object upload, runtime/IAM/CORS/deploy changes and publication/merge. Include
  stop-on-uncertainty behavior and exact safe cleanup ledger/prefix/DB scope.

Then execute only the approved increment, record actual counts/bytes/current
vectors/normal create-edit/session/media checks, and retain unchanged22accepted
judgments. No readiness or final freeze is inferred from generation/local passes.
