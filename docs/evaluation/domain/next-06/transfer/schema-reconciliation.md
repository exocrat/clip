# NEXT-06 Step 3 — source/schema reconciliation

The latest remote main is still `6edb52ba4e5a148386cd81e78b29c15b557193c7`.
This task branch and the transferred corpus each bind the same29migrations.
The shared RDS database has those29plus three Notifications migrations from
[Aditya’s PR21](https://github.com/exocrat/clip/pull/21), head
`db8a661a2fb1d3cdc01bfaf15c7186b9b4db7dd5`. PR21 is open, CI passed and no
peer review was recorded at inspection. NEXT-06 PR22 is also still open.
Exact paths, blob IDs, effects and inspection time: [evidence](schema-reconciliation-result.json).

## Finding and source choice for the proposed setup

This is a deployed-schema/source divergence, not a missing pull of current main.
The existing marketplace role’s intentional tracker denial is a separate issue;
admin inventory already resolved the read-only inspection route. Do not widen
that application role, migrate shared32backwards, adopt/reset shared application
data, merge another owner’s PR, or waive the loader’s exact schema check.

Continue preparing the previously proposed **new isolated database**
`clip_next06_reference` against accepted main/corpus29. This avoids creating a
new dependency on unreviewed Notifications implementation merely to bulk-load
this owned corpus. Isolation must include exact database/role grants, credentials,
empty-target checks and a run-owned image prefix. It does not switch the current
shared service to that database, prove final deployed integration or authorize
any cloud mutation. Verify this setup scope before execution.

The three additions are encrypted notification destinations, delivery retry/
reservation columns and index, and an opt-in-default-true conversation-email
preference plus suppression result. Static inspection gives no reason to change
the existing users/listings/photos or repeat the22unchanged relevance judgments.
It does not prove32schema/runtime compatibility. No source rebind/regeneration
has been performed. Keep existing accepted labels, fingerprint and December1
cutoff. Any later accepted Notifications integration needs exact source/schema
binding and affected real checks before final readiness/freeze; do not call the
29schema isolated load proof of the current shared32runtime.

## Exact remaining setup/load preparation sequence

1. Bind current29migration file hashes and corpus/source/contract/config hashes;
   retain source-owner/peer gates. Check main/target drift again before applying.
2. Prepare a reviewed create-only setup for new `clip_next06_reference` on the
   existing instance and absent `clip_next06_loader`/`clip_next06_runtime` names.
   Native PostgreSQL18.6 rehearsal must prove minimal actual lock/trigger/catalog
   and migration-tracker rights, no inherited privileged membership, no app
   admin credentials, and denial of unintended DDL/cross-database use. Do not
   guess loader grants or use ownership as a shortcut to a restricted role.
3. Run only the exact29reviewed migrations on the new database; revoke/restrict
   PUBLIC privileges only there. Prepare role credentials in memory and an exact
   private storage/retention route. Global role creation and nontransactional
   database creation need explicit partial-failure/cleanup evidence; never drop
   resources automatically or change existing role passwords.
4. Prepare actual post-setup target, session/TLS/migration/empty/catalogue checks,
   500000paise runtime threshold verification, limits and stopped closeout. Obtain
   affected-owner review and separate exact cloud setup/secret approval only
   after the commands and native checks are concrete. Current scope is preparation.
5. Prepare the separate1,000object create-only S3 and atomic5,000user/1,000listing
   load using existing guarded adapter, approved bucket/prefix and private ledger.
   Prefix recommendation remains `id01/next06-reference-42-v1` in current private
   id01bucket; maintainer review and effective access checks remain required.
   Preserve exact source photo bytes and bounded GET/hash verification. SQL
   rollback cannot remove already created S3 objects; retain attempted-key ledger,
   no blind retry or prefix deletion. Native loader/normal-flow checks precede
   the separately approved real load. No resource starts/uploads occur here.
6. Return to original real application auth/media/create-edit and pinned vector
   processing checks, bind final source/labels and freeze/reproducibility evidence.
   Follow NEXT-05’s scoped preparation allowance; do not claim Notifications or
   full32schema runtime integration from a29schema load. NEXT-06/DATA-READY remain
   incomplete until their actual required integration checks pass.

No repository source changes, AWS calls, secret reads, schema/data writes, uploads,
fetch, merge, cherry-pick, commit or push occurred during reconciliation. The last
verified cloud closeout remains both resources stopped at18:46:54UTC on October30.
