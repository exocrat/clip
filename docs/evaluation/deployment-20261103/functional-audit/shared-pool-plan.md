# Shared-pool repair, protected ECS fallback and experiment closeout

Suraj approved local implementation on 2026-11-04 and explicitly requested the
existing optimized implementation be committed first. Cloud creation, activation,
SQL changes, exact merge, task loss and restore remain separately gated. Current
work is local preparation, not a claim that a managed proxy or any NFR works.

## Preserved fallback

- Exact source: `6193ca7119b74c07bc723ec30834cbb119f6338a` on
  `task/functional-runtime-repairs`. Includes all lunch optimizations and existing
  functional repairs. Prior quality/capacity evidence remains unchanged.
- Local API image: `clip-exp03-api:local-6193ca7`.
- Local deployable Hybrid image: `clip-exp03-hybrid:local-6193ca7`, image ID
  `sha256:830cd5f50a9afe563d0e1f8b1b5f0a16edc449bc3410879bf38f7b3139623be5`.
  It uses the exact archived API source/locked dependencies and the unchanged
  cached semantic runtime; real offline model inference passed. It is not yet
  published to ECR or deployed. Build receipt/logs are private under
  `/home/suraj/src/.clip-private/proxy-20261104/fallback-6193ca7/`.
  The receipt hashes both build logs and the cached-runtime build recipe.
- Local fallback Lambda image: `clip-exp03-lambda:local-6193ca7`, image ID
  `sha256:1c153e39ada7770dc44a479a494a695e4d34c57b45b6749b5eef0c49582f3016`.
  Built from the same archived source and pinned cached adapter; unpublished.
- The existing live image is a separate, older service-recovery point:
  `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:860c8c15fe29b2592976ca5b8dafdb5738d791de012ccbc4f57b9bc076ae674b`.
  Do not confuse it with the optimized ECS code that passed locally.
- Two ECS tasks total, one per existing host. The proposed1024CPU units per task
  remain separate from the currently deployed512units. Host/RDS sizes stay fixed.

## Design and compatibility

Both ECS and Lambda use the same private RDS Proxy and authoritative database.
Small ECS client pools remain. Lambda retains bounded per-invocation client
connections, while the shared proxy owns reusable database connections. The
different client lifetimes remain disclosed; this is a deployment comparison,
not an assertion of identical runtimes or cache populations.

The source SSM DSNs are unchanged. `CLIP_DATABASE_PROXY_ENDPOINT` replaces only
their hostname in memory. Database name, role, password and verified TLS stay
intact. Removing the override restores direct access. No password rotation,
role merging, data copying or automatic failover to direct access occurs.

Proxy clients omit unsupported startup `options`, disable automatic prepared
statements and verify the proxy's server defaults before use:5second statement,
1second lock and5second idle-in-transaction limits. Existing transaction-local
deadlines remain intact. Pool checkout checks replace stale client connections
before business SQL; failed application transactions are not blindly retried.
Read leases are still released before numerical search scoring.

The proxy is TLS-only, SQL debug logging disabled, client idle timeout300seconds,
connection-borrow timeout1second. MaxConnectionsPercent75 bounds backend use;
MaxIdleConnectionsPercent50 bounds idle retention. With observed max78 this is
an approximate ceiling58, not a promise of58usable application connections: AWS
reserves capacity internally; inspect `MaxDatabaseConnectionsAllowed` before load.
Keep administration and monitoring headroom. Proxy limits do not allocate fixed
shares to roles. Role limits, current connections and pinning must also be checked.

The previously proposed full-concurrency role limits Identity20/Marketplace40/
Conversations4 remain separately approved SQL work; current reported limits are
10/32/4. Do not launch the proposed ten-concurrency Lambda pilot against unreviewed
role capacity. Worker grants remain their existing separately reviewed proposal.
Neither the proxy plan nor this document applies those grants/limits.

AWS documents session pinning and transaction-local settings separately. Keep
the real transaction semantics; measure pinning/reuse instead of assuming that
every backend can always be shared. Local doubles cannot reproduce managed
RDS Proxy capacity, TLS overhead, failover or execution-environment freezing.

## Exact provisioning stage — approved, not applied

Suraj approved this exact saved plan on 2026-11-04 12:24:22 UTC, with a USD2 additional
allowance and at most24hours, conditional on separately approved PR integration.
Application activation and other cloud/SQL actions retain their own gates.

Operator `surajs2`, account335523638354, region`ap-south-1`. Existing source
`clip-shared-test-postgres`, PostgreSQL18.6, `db.t4g.micro`, private in the existing
VPC. Source DB is `clip_next06_reference`; final dataset is present.

Saved full plan, generated from the complete shared root with current deployment
inputs and proxy routing **disabled**:

- Private directory: `/home/suraj/src/.clip-private/proxy-20261104/`.
- `provision.tfplan` SHA-256:
  `ea6be9edfbf3eae1845488d35baffb4eaab83e42ac76009c41cdd8fbeff3b01a`.
- `provision-summary.json`:15create,1update,0destroy. Includes one Terraform
  bookkeeping object; no EC2/RDS replacement or ECS task-definition change.
- `credential-sources.json`: source versions2 for all three existing DSNs,
  expiring2026-11-05T10:43:48.003694Z. SHA-256
  `23b235ee51af18cd6394f6c70bf29bf89a825c9ea4ce2fdc818d68ca022fd185`.
- Plan JSON records null values for ephemeral password inputs/write-only secret
  fields. Actual values enter only the Terraform child environment. Source
  passwords, TLS and SSM parameters remain unchanged.

Create proxy `clip-shared-test-pool`, its default pool/target registration,
security group `clip-shared-test-database-proxy`, ECS-to-proxy ingress and
proxy-to-database egress on5432, and role/policy
`clip-shared-test-database-proxy` / `read-exact-proxy-credentials`.
Create only these Secrets Manager secrets and their write-only versions:
`/clip/test/rds-proxy/identity`, `/marketplace`, `/conversations` (same prefix).
The proxy role can read only those three secret ARNs. Original app roles do not
gain Secrets Manager access. Existing database SG gains one proxy-source ingress
rule on5432; its ECS rule is preserved. No public port, DNS or certificate change.

The provision plan does not switch app traffic, deploy images, create Lambda,
alter SQL, resize resources, or start a load test. Lambda-specific SG rules enter
the later full B activation plan. Validate proxy target availability and actual
role/TLS access before enabling the runtime override.

Existing AWS inventory on2026-11-04 found no proxy or destination secrets. The
source was available and automated-backup metadata refreshed. Inspect live state
again before apply; a changed saved plan requires renewed review.

## Cost and bounded action

AWS Price List query on2026-11-04 returned Mumbai PostgreSQL proxy price
USD0.017/database-vCPU-hour:2vCPU gives0.034/hour,0.816/24hours. Propose an
additional **USD2 allowance for at most24hours** for this proxy stage, including
the three small secrets/API/storage allowances. This is an operational stop
budget, not an AWS-enforced billing ceiling. It excludes already-running baseline
costs, which remain in the project ledger and whole-experiment renewal.

Fresh Cost Explorer response:October usageUSD22.5225885272 and November-to-date
USD6.863760726, totalUSD29.3863492532 before separately recorded credits. November
is estimated and billing delayed. Do not treat the apparent credit-offset bill
as zero project spending. Final whole-run allowance and delayed/retained reserves
must be renewed before live load; project spending must remain belowUSD200.

If unused, remove the new proxy/policy/role/SG rules and only the three owned
secrets through a reviewed full cleanup plan. Secrets use seven-day recovery,
not immediate irreversible deletion. Stop proxy use before deletion; verify
both application paths have returned to direct settings. Never delete source
roles, SSM secrets, database, original SGs or data. If work is interrupted, this
directory's plan/receipt identifies the exact resources to inventory.

Local checks and retained failures are recorded in the
[validation report](shared-pool-validation.md).

## Execution order and gates

1. Preserve fallback; implement application, IaC, preflight, telemetry and restore
   protections. Complete meaningful focused tests and release checks. Suraj separately approved committing/publishing the reviewed
   41-file follow-up and running CI; the first fallback commit was also explicitly
   approved. Exact merge approval remains pending. No extra candidate or resource upgrade automatically.
2. Finalize/review this deployment plan before PR integration. Resolve checks,
   commit/publish/CI and exact merge under Suraj's review/authorization.
3. Approve/apply the saved proxy provisioning plan. Inspect actual target/TLS/
   credentials/deadlines, then prepare the full image/CPU/endpoint/B plan with
   accepted image digests. Any SQL grants/limits remain separately explicit.
4. Deploy A, then B for small functional checks. Verify auth/current permissions,
   Saved/Wanted, repeated card/detail photos, all search pages, controlled writes,
   two-account chat/offers, real mail and workers. Confirm selected GET routing
   and equivalent results; no assumed ALB fallback. Suraj inspects the website.
5. Freeze final datasets, cases, model, resource/connection settings, image/code/
   tool revisions, costs, timing, run order, stop conditions and evidence paths.
   Verify actual generator and DB/proxy headroom. Establish ECS cloud NFR evidence
   first; NFR-06/07 actions retain exact approval. Keep destructive/recovery work
   outside performance windows. Check backup readiness early.
6. Pilot ECS baseline then100%Lambda only, three repetitions each,60second
   warm-up/120second measurement, same formal burst mix. No75/50/25candidates,
   whether100%succeeds or fails. Keep required attributable cold observations.
7. Run B's applicable NFRs with frozen configuration, preserving any failure.
   NFR01/02/03 both architectures; NFR04both search paths; NFR05both under their
   different background routing; NFR06both with two healthy ECS tasks; NFR07one
   valid shared-source restore if unchanged; NFR08throughout. NFR03creates up to
   180synthetic Wanted records per architecture including warm-up, so its exact
   action package must authorize these beyond the small manual-inspection fixtures.
8. Reconcile/retire synthetic writes and restore steady capacity/inputs before
   the read comparison. Run the frozen18-run paired schedule across low/normal/
   burst. The50rpscomparison rate is a design choice; lowering it requires a
   recorded equal-A/B revision and disclosure of the higher-rate failures.
   NFR03's50rps/five-minute requirement cannot be lowered.
9. Audit separate reports against immutable raw evidence, failures/drops and
   telemetry. Report exact locations, results, validity, limitations and costs.
   A configuration losing/failing is a legitimate result, not permission to
   hide data. Select an eligible architecture, clean up only approved owned
   resources/fixtures, reconcile costs and complete report/demo/task closeout.

If proxy behavior regresses ECS or remains unsuitable, stop the run and return
to the preserved direct configuration. Publish the optimized fallback image under
the approved release action if needed. Switching configuration invalidates only
the affected evidence; preserve failed runs and identify the replacement revision.
Do not claim the older deployed image already passes cloud NFRs.

## Sources

- [AWS proxy connection/startup parameters](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-connecting.html).
- [AWS pinning behavior](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-pinning.html).
- [AWS proxy metrics and aggregation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.monitoring.html).
- [Terraform secret write-only fields](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_version).
- [PRD-derived NFR definitions](../../nfr/measurement-design.md) and
  [the canonical experiment](../../ecs-only-vs-ecs-lambda-task-list.md).

The default AWS-managed Secrets Manager key is used; no new customer-managed key
or broad KMS policy is added. Its key policy permits same-account access through
Secrets Manager for principals authorized to read the corresponding secret. The
proxy role can read only its three exact secret ARNs. See the
[AWS-managed key policy](https://docs.aws.amazon.com/secretsmanager/latest/userguide/security-encryption.html).
