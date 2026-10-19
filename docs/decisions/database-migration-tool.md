# SQL migrations with pinned dbmate

**Date:** 2026-10-18
**Origin:** PD-08 Step 3.

## Question
Which single tool can own coordinated PostgreSQL migrations within Stream 3's paths?

## Options considered
- Alembic: fits the Python stack but adds shared Python manifest/lock dependencies and couples initial DDL to a Python migration environment.
- dbmate: standalone, timestamp-ordered transactional SQL migrations; can run as a pinned container without editing another stream's manifest. The pinned release has no CLI-wide migration lock.

## Selected choice
Use dbmate 2.36.0 and SQL migration files under `database/migrations/`. The intended container is `ghcr.io/amacneil/dbmate:2.36.0`; Compose wiring/digest verification belongs to the local service/lifecycle steps. Use transactions, strict ordered migrations, explicit validated local targets and disabled implicit dotenv discovery/schema dumps. Each up/down transaction takes PostgreSQL advisory key `(1129072976, 8)` with a 10-second lock wait. A single named operator serializes full CLI runs: this per-transaction lock is not a substitute for a CLI-wide lock/re-read of migration history. No implicit create/drop or cloud-target command is added in Step 3.

## Rationale
Keeps DDL readable and independent of an ORM while respecting Mohit's instruction not to change others' directories or shared dependency manifests. Repository local/CI lifecycle is integrated in the later named steps.

## Implications
One ordered migration head, with tables before cross-row integrity and initial catalogue data. Once published/applied, correct migrations forward rather than rewriting history. Down sections are explicit local-test rollback definitions; they are not approval to delete data and avoid broad CASCADE drops. Tool/SQL syntax inspection alone is not evidence of real apply/rollback; PD-08 Step 6 later passed its required checks, as recorded in the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). The user later confirmed the affected-owner gate complete on 2026-10-19. The provisional sequencing exception did not waive the required real apply/rollback checks.

Primary references: [dbmate release 2.36.0](https://github.com/amacneil/dbmate/releases/tag/v2.36.0) and [official documentation](https://github.com/amacneil/dbmate). PostgreSQL/server selection remains Step 4.

Version-specific verification used the [2.36.0 README](https://github.com/amacneil/dbmate/blob/v2.36.0/README.md): `--strict` is supported but the main branch's newer `--migration-lock` flag is absent. Do not pass that unsupported flag or claim automatic concurrent migration safety. A conflicting concurrent CLI run may fail safely; inspect status and rerun only after serialization.

### Step 6 native execution correction — 2026-10-18

Actual dbmate 2.36.0 execution confirmed that `--strict` is a **command option**:
use global options followed by `migrate --strict`. Do not pass it globally or
to `status`/`rollback`. The original Step 5 wrapper's placement was incorrect;
native verification caught the failure before migrations ran. Corrected both
wrappers and reran the 22 simulated safety cases; native clean apply/repeat/
rollback/reapply and smoke now pass. Container execution remains deferred.

## Approver
Tool selection was a Step 3 implementation choice within Mohit's authorized scope. At that point he separately authorized proceeding before affected-owner review; the user later confirmed that gate complete on 2026-10-19. This does not grant commit, push or merge approval.

## Supersedes
None.
