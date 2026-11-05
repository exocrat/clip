# Bounded experiment deployment plan

**Current disposition (2026-11-05 15:26:56 UTC): Aditya marks INT-01 complete. Earlier pending/checkpoint statements below are historical; this status update records his direction and does not add new execution evidence.**

Prepared on 2026-11-03 for `exocrat/clip`, from the actual
`task/experiment-tooling-readiness` worktree. This plan is prepared **before
commit, PR checks and merge**, as Suraj directed. Git integration does not
approve the cloud actions described here. At initial preparation no deployment
or load had run; subsequent execution and the current repair hold are described
below and in the functional audit.

## Decision and approval state

**Historical baseline:** the original starting inventory and cost window below
describe preparation on2026-11-03, not current running state. The website has
since been deployed; both existing c7i-flex.large hosts and two revision13API
tasks were verified running during the functional audit, with RDS on the retained
micro and the ALB present. Lambda is not yet deployed. Current local repairs and
search optimisation are not on that website. The old execution window has
expired: refresh account/resources/drift/billing, bind the final image digests,
renew the concrete time/cost approval, and review the exact saved plan before
any subsequent cloud apply. Do not replay the original creation steps.

The direct-database fallback is preserved at `6193ca7`. The current
[PgBouncer plan](functional-audit/pgbouncer-plan.md) supersedes the earlier
managed RDS Proxy proposal: its approved creation failed because this AWS Free
Plan account does not permit that feature. A private pool on an existing ECS
host is now under local validation; a replacement provisioning plan includes
cleanup of the partially created proxy support resources. The AWS pilot is
being prepared with ten unreserved Lambda slots, pending release approval.
The account currently permits ten; its pending increase must not change a run.
A second database and RDS resizing remain
unselected. The pilot now uses only ECS baseline and 100% Lambda, three
repetitions each; older four-candidate descriptions below are historical. The approved1vCPU/task remains a planned allocation change;
it is not part of the older image-only approval or evidence of an applied change.

The normal running configuration is **two healthy ECS tasks on two hosts in
both A and B**, including NFR-01–03 and the formal comparison. Suraj clarified
that NFR-06 must support the actual deployment. The submitted PRD was extracted
directly (page 4, SHA-256
`8ac241d1e72472a5dc77edad18579ec5d2ca3ff2ac8fd454cbc6e9627abf4ad1`):

> With at least two healthy serving instances configured, forced loss of one
> serving runtime shall restore the configured healthy serving capacity within
> 240 seconds, while requests during the experiment are measured for failure.

The shared [capacity decision](../../decisions/experiment-runtime-capacity.md) records this choice.
Keep ECS desired count two while the accepted app configuration is running.
The test stops one ECS task and observes restoration to two healthy tasks;
it does not stop the database or the whole deployment. Lambda does not replace
one of those two ECS tasks. The earlier one-task-normal/two-only-for-test
suggestion is superseded. Budgeted shutdown outside an approved running window
still sets all app compute to zero.

NFR-06 is exercised under both A and B: the ECS replacement mechanism is shared,
but the request routing and database load differ, so record each configuration's
recovery/request outcomes separately. This is not a separate Lambda fault
injection. Its manifest template fixes desired count two.

The normal merge workflow follows this document. Cloud approval comes after the
merged release is built, immutable image digests and actual new resource
identifiers are bound, a full Terraform plan is reviewed, and the operator
confirms the limits below. A changed topology, cost bound, target or exposure
requires renewed cloud approval. Exact task-stop and restore approvals remain
separate. No PR, review or merge approves either destructive experiment action.

## Original verified starting point — 2026-11-03

The [inventory](inventory.json) contains the current read-only AWS observations.
STS verified `arn:aws:iam::335523638354:user/surajs2`, account `335523638354`,
region `ap-south-1`. Use only profile `surajs2`; never the unrelated default
root credentials. No open repository PR was returned; `origin/main` is
`2a0916e`, including PRs #27/#28. The tooling branch includes `663cfca` plus
this local batch. The Git head is rechecked before integration.

- ECS cluster `clip-shared-test`, service `clip-test-api-ap-south-1-pd16`:
  desired/running/pending zero, old task-definition revision 11.
- Retained ECS host `i-086045c48487471de`: stopped, `t3.micro`, private subnet
  `subnet-0c9df7ababd0154bc`, group `sg-0a3c8d683731470b4`.
- ASG `clip-shared-test-ecs-host`: min/desired zero, max one, all listed
  processes suspended; retained host protected from scale-in. Its stopped
  instance still appears InService. Do not interpret that as usable capacity.
- Private encrypted RDS `clip-shared-test-postgres`: stopped, PostgreSQL 18.6,
  `db.t4g.micro`, 20 GiB gp3, deletion protection on. Endpoint:
  `clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com:5432`.
- VPC `vpc-04b0cc01cbf93cd17`, `10.64.0.0/20`; existing subnet CIDRs
  `10.64.0.0/24`, `10.64.1.0/24`, `10.64.2.0/24`. The proposed extra ALB
  subnet `10.64.3.0/24` is currently unused; recheck before applying.
- No ALB or Lambda exists. The existing `clip-iisc.site` certificate is issued:
  `arn:aws:acm:ap-south-1:335523638354:certificate/a9775d00-2af5-4b12-990d-1ce9795f1859`.
- The legacy HTTPS proxy `i-0d1947299024cae06` stays stopped. Keep its disk,
  EIP and original configuration for rollback; include their residual cost.

## Resource choices and limits

| Component | Proposed deployment and limit |
|---|---|
| Ingress | One public HTTPS ALB, two public subnets, port 443 only; default ECS target group. No public RDS or SSH rule. Use existing VPC/NAT. |
| ECS app | Reviewed x86 image from the merged revision; 1,024 CPU units and 2,048 MiB per task (Suraj-approved allocation increase; not yet applied); real Microsoft Identity, Conversations, Hybrid and Notifications enabled consistently in A/B. Normal desired count two, one task on each host. |
| Hosts | `c7i-flex.large`, at most two, same type in A/B. Resize the stopped retained ECS host in place; preserve its disk and identity. A second host, when needed, is owned by this run. Do not terminate the retained host. |
| RDS source | Retain the existing micro instance and 20 GiB; start without replacement or deletion-protection changes. No database-class upgrade is silently authorized. |
| Lambda B | Reviewed x86 image, 2,048 MiB, five-second timeout. Reserved concurrency 2 for smoke, proposed 10 before pilot; hard implementation maximum 20 is not permission to use 20. Verify DB headroom before adopting 10. No provisioned concurrency. |
| Routing A | `exp03_selected_reads_lambda_weight_percent=null`; selected reads and all other operations use ECS. |
| Routing B | Only approved Listing GET routes split between ECS/Lambda; fixed pilot-selected weight, stickiness disabled. Other methods/routes use ECS. Failed/throttled Lambda requests remain failures. |
| Restore app | Opt-in `restore.clip-iisc.site`, initially zero tasks, separate target group/port 18001 and three isolated domain database parameters. Run only under A. Keep both source tasks healthy; use one additional 256-CPU/1,024-MiB smoke task with Hybrid search and background workers disabled so it can share a host. Verify actual free memory before activation. Remove smoke resources before weighted B. |
| Restore database | One new private encrypted `clip-exp261103-restore`, same micro class/20 GiB, same reviewed subnet/security scope. Restore only the approved latest automated snapshot. Source remains intact. Observer deadline 30 minutes; at most two instance-hours including cleanup. |
| Storage/images | Reuse `clip-test-listings-images-ap-south-1-id01`, prefix `id01/next06-reference-42-v1`. No dataset regeneration or image re-upload. ECR uses the existing project API repository with separate API/Lambda tags and immutable digests. |
| Logs | Content-free app telemetry; API access logs disabled; new Lambda logs retained seven days. No sessions, DSNs, Microsoft assertions or chat bodies in evidence. |
| Generator | Suraj's existing WSL2 Linux workstation and custom monotonic k6 binary; no extra AWS load-generator VM. Freeze binary/module hashes, CPU/RSS/concurrency limits and network location before traffic. |

Run ownership identifier: `exp261103`. Refresh its date/expiry if execution is
rescheduled. Maximum elapsed deployment window: 36 hours from first new billable
resource. ECS compute: at most 12 active hours and 24 host-hours. Lambda traffic:
at most four active invocation-window hours with the proposed concurrency 10.
Total planned load/preflight traffic must stay below 300,000 HTTP requests and
150,000 Lambda invocations. Each concrete Terraform/run plan has an explicit
shorter phase window; the existing EXP-03 input caps each phase at 120 minutes.
Tags and alerts are accounting aids, not automatic hard shutdown controls.

The [public input overlay](public-input-overlay.json) fixes these non-secret
choices explicitly, including desired count two. It is an incomplete overlay,
not a standalone runnable tfvars file: merge the existing verified base inputs,
reviewed image digests and secure private inputs before generating the full plan.
For B smoke, override reserved concurrency to two; apply the approved ten only
after the connection-budget check and before pilot runs.

## Data, versions and real-user access

The final dataset is present and accepted. Preserve fingerprint
`7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98`,
5,000 users, 1,000 listings and the 22 reviewed queries. The accepted database is
`clip_next06_reference`. Its frozen availability window ends
2026-12-01T00:00:00Z; do not measure outside it without a reviewed data-window
extension. Model: `all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

Bind the final merged application revision, API/Lambda image digests, actual
migration head, index/model/pipeline hashes and existing approved account IDs
before measuring. Check actual DSN destinations securely; old metadata alone
does not prove the runtime points at the accepted database. Identity,
Listings/Search and Conversations retain their separate roles. Do not print
secret values while checking host/database/role commitments.

Use the two owner-confirmed regular synthetic Microsoft accounts. Sign-in stays
outside measured load. Existing approved recipient/secret references are supplied
securely, never copied into this document. Verify the test accounts' eligibility,
chat encryption/keys, source-session handoff and notification behavior. If a
required wanted/conversation/offer fixture is absent, create at most ten scoped
synthetic fixtures through the real app under the concrete fixture approval;
record IDs and cleanup. This does not regenerate the frozen listing corpus.

The restore app uses its own real Identity profile and fresh session file, not
an assumed session from the old backup. Supply three restored DSNs through
Terraform's ephemeral write-only inputs; preserve each domain role/database
name. The observer checks every endpoint and TLS binding. Freeze all source
fixtures and relevant migrations before the fresh automated backup is captured.

## Spaceship and Microsoft handoff

Send these instructions to the domain owner; the agent does not contact them.
Keep the existing nameservers, mail records and source ACM validation record.
In Spaceship Advanced DNS, use Custom records:

| Host | Record | Value |
|---|---|---|
| `@` | CNAME in Spaceship's UI, flattened to an apex ALIAS | Actual ALB DNS hostname, copied from the approved deployment output |
| `restore` | CNAME | The same actual ALB DNS hostname |
| The exact token name provided by ACM for restore | CNAME | The exact ACM validation hostname returned after the approved certificate request |

Use TTL 300 seconds if offered. Save the old apex A/AAAA values for rollback;
remove only records conflicting with the new apex alias. Do not pin ALB IPs or
change MX/SPF/DKIM/DMARC. Spaceship documents that a CNAME entered for `@` is
resolved as an ALIAS in its [official guide](https://www.spaceship.com/en-GB/knowledgebase/dns-alias-record/).
Actual ALB/validation values do not exist yet; provide the exact generated values
after their separately approved creation, not guessed placeholders to enter now.

The Identity owner must register the additional SPA redirect
`https://restore.clip-iisc.site/auth/callback` in the existing Microsoft app.
Keep the current source redirect. Request an ACM certificate for the restore
hostname in Mumbai; do not buy a certificate or move DNS to Route53.

## Cost model and project budget

[prices.json](prices.json) records current public on-demand AWS Price List API
results retrieved on 2026-11-03. [cost-model.json](cost-model.json) contains all
quantities, rounding and allowances. No free-tier allowance or credit discount
is assumed. Selected prices are:

| Item | USD rate |
|---|---:|
| c7i-flex.large | 0.08479 / host-hour |
| RDS db.t4g.micro | 0.021 / instance-hour |
| NAT | 0.056 / hour plus 0.056 / GB processed |
| Regional ALB | 0.0239 / hour plus 0.008 / LCU-hour |
| Public IPv4 | 0.005 / address-hour |
| EC2/RDS gp3 | 0.0912 / 0.131 per GB-month |
| Lambda x86 | 0.0000166667 / GB-second plus 0.20 / million requests |

Expected additional window cost: **USD 8–14**, depending on active time, selected
weight, actual request duration and traffic. Conservative component scenario,
including 20% tax/usage/rounding contingency: **USD 27.677818**. Proposed maximum
incremental authorization: **USD 30**. This is a new proposal for this window;
the historical USD 10 credit cap is superseded.

The bound includes two hosts for 12 hours; source RDS/NAT/ALB up to 36 hours;
two hours of restore RDS; up to 20 ALB LCUs throughout that window; six public
IPv4 addresses; 120 GiB retained/new EC2 disks; 20 GiB source/restore DB storage;
Lambda's concurrency/memory/time bound; and USD 5 for traffic, logs, ECR/S3/mail
and smaller charges. These are coupled operational ceilings, not hard provider
billing caps. Stop before their estimated combination can exhaust USD 30.

Current completed-period gross usage is USD 26.232051 through 2026-11-02,
offset by separately recorded credits. The [project ledger](../nfr/project-cost-ledger.json)
contains these actuals; it remains explicitly incomplete. Reserve USD 2 for
current-day/delayed baseline charges and USD 30 for remaining project work and
retained liabilities. After the proposed USD 30 window cap, unallocated project
headroom is **USD 111.767949**. Update actuals/delay estimates before approval and
after each run. The USD 200 requirement is cumulative project implementation/
evaluation spending through experimentation and cleanup, not annual hosting.

The old USD 1,217 annual forecast is not the experiment estimate. Existing NAT,
IPv4 and storage continue costing money while compute is off. Record retained
resources and their later cost instead of treating shutdown as zero spending.
The 36-hour bound intentionally covers waiting for the nightly automated backup.

Before final comparison results, derive and human-verify the numeric good/poor
cost-score endpoints from the selected topology, these public prices, the fixed
normal profile and resource bounds. Freeze the interval/allocation formula and
credit/tax treatment then. This required input is not fixed by merging this
plan, and must never be chosen from final A/B results.

## Earliest DNS-owner handoff

Suraj wants to forward all domain-owner work in one message. Collect the exact
records at the earliest stages below, then present one complete handoff as soon
as both certificate validation and ALB records are available. Do not wait for
application startup or site readiness. The two preparation stages are:

1. **Certificate validation first:** as the first separately approved AWS write,
   request a standard **non-exportable public ACM certificate** for
   `restore.clip-iisc.site` in `ap-south-1`. This does not depend on the release
   image build. Immediately read and retain its exact validation CNAME name/value for
   the combined owner handoff. Do not wait for issuance: the
   owner's DNS record is what allows validation to finish. Request no private CA
   or exportable certificate.
2. **Application aliases next:** once the approved ALB creation finishes, give
   Suraj one complete message containing certificate validation, the exact ALB
   hostname, and the apex/restore records, before
   waiting for ECS/RDS startup or site readiness. Preserve existing mail/source
   validation records. Suraj forwards the records; the agent contacts no owner
   directly. Verify DNS/TLS after the owner confirms the edits.

Release build and certificate DNS propagation can proceed independently after
these scoped actions are approved. The ALB still requires its reviewed full
Terraform plan; do not use targeted apply to bypass dependency guards just to
obtain its hostname earlier. Keep app compute stopped while waiting for DNS.

`restore.clip-iisc.site` is a subdomain under the existing registered domain,
used temporarily for the isolated NFR-07 application connected to the restored
DB. It does not require buying another domain or Spaceship hosting. It reuses
the same ALB. Standard non-exportable public ACM certificates have no certificate
charge ([AWS pricing](https://aws.amazon.com/certificate-manager/pricing/)).
The temporary restore database/app still incur the costs already budgeted here.
This ordering change needs no application-code change and grants no cloud write
approval by itself.

## Ordered execution and gates

1. **Complete this plan, then Git integration.** Use the selected two-task baseline; commit the
   tooling/plan; run current local aggregate and hosted PR checks; merge through
   the normal workflow under Suraj's authorization. No cloud writes in this step.
2. **Start the certificate handoff and bind the release.** First prepare and
   approve the narrow, no-certificate-charge ACM request described above; send
   retain its exact validation CNAME for the combined owner handoff. Build API/Hybrid/Lambda from accepted main
   using pinned cached dependencies/model, verify x86 manifests and hashes,
   then obtain approval for the exact ECR publication and full Terraform plan.
   ECR tags are `exp03-api-<SHA>` / `exp03-lambda-<SHA>` in the existing project
   repository. Digests replace tags in runtime inputs. Preserve private plan/state
   files outside Git; publish sanitized actions and their hashes for review.
3. **Provision ingress and DNS prerequisites.** Under the approved A plan,
   create the extra public subnet, ALB/target group, scoped ingress and image/
   secret permissions; attach the previously requested restore certificate only
   when issued and required. Send all exact DNS records together immediately
   after ALB creation. Keep retained ASG launch/
   replacement processes suspended while DNS/host readiness is prepared. Pending
   ECS tasks are not proof of a running site. Obtain actual DNS values from
   outputs and let the owner apply the handoff above. If DNS is delayed, keep
   compute off rather than consuming its active-hour allowance.
4. **Start safely and establish source A.** Preserve the original host's stopped
   type/groups/protection/ASG/LT record. Resize it in place while stopped, attach
   only the reviewed additional ALB ingress group, set the ASG capacity appropriate
   to the selected task count and start it. Resume only the required launch
   process after the retained host is healthy; allow a run-owned second host if
   selected/needed. Do not blindly resume Terminate/ReplaceUnhealthy. Start the
   existing RDS without replacing it. Check exact image, roles, grants, schema,
   accepted data/model/index state, signed images, real sessions and workers.
   Apply only separately approved forward migrations/grants if actually required.
5. **Prove A/B routes and let Suraj inspect the site.** Capture A response
   evidence, deploy B for bounded functional checks at an explicitly reviewed
   weight, capture B and compare the receipts. Verify target-group request
   attribution and access restrictions; return to A as needed. Give Suraj
   `https://clip-iisc.site` and wait for the real desktop/phone inspection.
   Correct findings and repeat affected checks. No pilot traffic before this gate.
6. **Freeze capacity, inputs and cold-observation method.** Read actual
   PostgreSQL max/reserved/current connections; account for ECS pools, workers,
   direct Identity connections, Lambda environments and operator reserve.
   Adopt proposed Lambda concurrency 10 only if the approved connection budget
   supports it; otherwise stop for revised sizing before pilot traffic. Verify
   k6 CPU/RSS and VU capacity. Bind all cases/profiles, request caps, thresholds,
   source/binary/module hashes and evidence paths. No source/data drift inside a
   pair. Freeze stop criteria before observing pilot results.
7. **Collect separate cold observations and pilot weights.** Obtain at least
   three confirmed new-runtime observations for each configuration under an exact
   approved restart/version plan; record task start/readiness or Lambda init
   telemetry, attributable first selected read and monotonic client latency.
   In isolated ECS cold cohorts allow only the known new task to serve the target
   group; validate the regular session before its controlled restart. Use a
   single-request call through the existing HTTPS fetch/timing helper, keeping
   responses in memory. In Lambda cold cohorts use the separately approved
   100% Lambda route and an identified new function/version, with no unrelated
   invocation; correlate the first request window with platform reports. Record
   preflight/auth/cache warming explicitly. Unconfirmed samples stay missing,
   never become cold or warm by assumption. Do not derive p95/p99 from three
   examples. Restore normal capacity before the pilot/formal profiles.
   Run the existing ECS baseline plus Lambda/ECS 100/0, 75/25, 50/50, 25/75,
   three repetitions of 60-second warm-up and 120 measured seconds each.
   Review correctness, delivered rate, drops, throttles, DB/runtime headroom,
   latency and cost against the pre-agreed criteria. Freeze B's selected weight
   and the cost-score inputs before final comparison traffic.
8. **Run the formal matrix and required NFRs.** Use the approved paired
   18-run schedule: A/B, low/normal/burst, three repetitions, each with its fixed
   warm-up, five-minute measurement and drain. NFR-01/02/03 each have separate
   A and B profiles/reports. Run NFR-04 with the same 22 reviewed queries on
   both configurations; NFR-05 on both because background routing changes;
   NFR-06 on both with two healthy tasks, separately approved exact task loss.
   Capture recovery failures including Lambda-routed reads. Run controlled writes/
   chat after the read comparison to avoid polluting its quiet windows.
9. **Restore the fresh managed backup under A.** May be scheduled earlier when
   the snapshot is ready; it is outside comparison windows. Current backup window
   is 23:47–00:17 UTC (05:17–05:47 IST). The latest listed automated snapshot is
   older than the final freeze, so retain the source online until a fresh managed
   snapshot includes the frozen data/migrations and representative fixtures.
   Do not change the backup window or substitute a manual snapshot silently.
   Avoid measured traffic during backup and verify snapshot availability afterward.
   Preprovision the isolated smoke service stopped; get the exact restore
   approval, run the observer, publish the three restored DSNs/start the smoke
   service under the approved activation plan, and supply a fresh isolated login.
   Count the entire process toward 30 minutes. Preserve failure evidence and
   remove/retain only the approved restore target. Shared unchanged DB evidence
   may cover B under the documented reuse rule.
10. **Report, stop and verify cleanup.** Run the analysis/cleanup evidence tools
    over immutable raw outputs; review validity and calculations. Stop generators
    and workers, set app/smoke desired counts zero, remove only run-owned Lambda,
    ALB/extra subnet/SG rules/cert attachment and restore resources through the
    reviewed full plan. Revoke/remove only run-owned parameters and test data
    through approved domain procedures. Preserve frozen data, shared RDS/backups,
    existing roles/buckets/state and raw evidence. Shut down app compute until
    separately approved demo/final checks. Reconcile delayed billing in NFR-08.

## Rollback, interruption and cleanup ownership

Suraj is the human operator; the agent performs the approved commands with the
verified profile. Before cloud creation, attach the actual resource IDs, full
saved-plan hash, release binding, phase deadline and executable stop checklist.
Suraj must be able to take over that checklist if this agent/session is
interrupted. If the workstation itself is lost, use a separately verified
project-account console/CLI session; confirm that fallback before kickoff.
Do not represent tags or local timers as a hard AWS spending cutoff.

On wrong target, failed routing/auth/data parity, unsafe data, unexpected traffic,
unverified telemetry, generator saturation or approaching a time/cost cap: stop
new requests immediately. A pre-approved emergency ingress action may remove
weighted forwarding and return HTTP 503 on the exact owned listener, stopping
uncontrolled public workload while preserving data. Bind its actual ARN before
approval. Record partial runs and request fresh approval for any repair/retry.

For the retained host, restore original instance type/network groups and stopped
state after tasks are drained. Keep its scale-in protection. Detach only the
verified run-owned second ASG instance while decrementing capacity, then
terminate that owned instance/root volume. Restore min/desired zero, max one and
the recorded suspended processes. Reconcile the full Terraform state/plan after
imperative lifecycle operations; never use targeted apply to hide drift. Leave
the old HTTPS proxy stopped. Do not terminate an original instance or delete an
original volume to force a cleaner-looking state.

Stop source RDS at closeout, preserving deletion protection and data; AWS may
later restart a stopped RDS, so monitor the documented restart deadline and
retained charges. Delete the isolated restore only under its exact cleanup
approval. Verify services/tasks/instances/functions/ENIs/ALB/IPs/disks/SSM/logs,
record what remains with owner/review date and price, and run EXP-08 accounting.
DNS owner rolls back/removes only the new application aliases as approved,
preserving mail and ACM validation records. Do not publish results from an
invalid or interrupted run as passes.

## Evidence locations and result presentation

- Planning evidence: this directory's inventory, prices and cost model.
- Release and sanitized plan: `docs/evaluation/experiment-runs/<RUN_ID>/release/`;
  raw secret-bearing state/plans stay private and ignored.
- Individual runs: `docs/evaluation/experiment-runs/<RUN_ID>/`, preserving raw
  k6 output, staged profile, execution receipt, UTC windows, target/routing proof,
  CloudWatch component files and `lambda-initialization.json` under new paths.
- NFRs: `docs/evaluation/nfr/nfr-01/<RUN_ID>/` through `nfr-08/<RUN_ID>/`;
  cost actuals/delays in `docs/evaluation/nfr/project-cost-ledger.json`.
- Final derived analysis and cleanup: new versioned files linked from
  `docs/evaluation/experiment-log.md`; raw evidence is never rewritten.

From execution step 5 onward, report the exact files and actual results to
Suraj, explain each result and its limits in plain detail, identify required
changes, and preserve the website-inspection and separate stop/restore gates.
A successful build, health response or synthetic check is not a live NFR result.

Sources: [AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/),
[AWS ALB pricing](https://aws.amazon.com/elasticloadbalancing/pricing/),
[AWS VPC pricing](https://aws.amazon.com/vpc/pricing/),
[AWS automated backup behavior](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.BackupRetention.html),
and the committed public Price List API response in this directory.
