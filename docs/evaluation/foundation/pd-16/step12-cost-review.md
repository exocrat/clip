# PD-16 Step 12 — budget, routing and early utilization review

**Status:** Read-only checks performed; evidence independently cross-checked by the agent at the user’s direction before commit/continuation. Post-run charges are not yet available in the budget snapshot. Compute remains off.

## Budget and routing

Account `335523638354`, non-root `adityalaxmi1`; Budgets endpoint `us-east-1`, project resources `ap-south-1`. Custom USD 200 account-wide cost budget, no service filters, credits excluded. Five actual-spend, absolute, greater-than alerts at **USD 50/80/100/120/130** are OK. Each has four EMAIL subscribers matching the historical approved recipient set. Addresses/raw subscriber data retained privately, not in this evidence. No email/test notification was sent; configured routes do not establish recipient inbox delivery.

Current period is **2026-10-17 00:00:00 UTC–2027-10-17 00:00:00 UTC** (05:30 IST). Earlier inventory text calling the API times midnight IST was inaccurate; no AWS setting changed.

Budget-reported actual **USD 0.04**, forecast **USD 1.232**; last update **2026-10-19 13:42:11 UTC**, before this run. This is account early spend, not this run's bill. AWS documents typical 8–12-hour update intervals and notification lag: [Budgets timing](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html). No charge/delivery test was induced. Cost Explorer was not called: its primary-view API requests cost USD 0.01 each and would not eliminate delayed billing data ([pricing](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/)). No paid billing query or root fallback was needed.

## Utilization and approved-estimate comparison

[Safe raw-summary result](step12-budget-utilization-result.json), 17:17–18:24 UTC, 300-second periods:

| Metric | Observed |
|---|---:|
| ECS API CPU peak / mean of period averages | 63.33% / 5.98% of task allocation |
| ECS API memory peak | 8.35% of task allocation |
| EC2 host CPU peak / mean of period averages | 5.83% / 1.01% |
| RDS CPU peak / mean of period averages | 45.06% / 5.77% |
| RDS minimum FreeableMemory | 131.23 MiB |

Samples include startup/shutdown. RDS DatabaseConnections samples were zero; brief setup/probe sessions can fall between samples, and successful task/SQL evidence remains authoritative for connectivity. This is foundation utilization review, not workload, sizing or NFR acceptance.

Observed lifecycle envelopes: host about **0.967 hours**, RDS start-to-confirmed-stop about **0.892 hours**. Applying the already approved reference rates gives **USD 0.1044 for host compute/root volume plus RDS compute**, excluding NAT/IPv4, DB storage, traffic, logs, ECR, backups, CPU credits and backend. These envelopes are not exact provider billed durations and prices were not refreshed; this is an estimate component, not a bill or total. Counts stayed within one host/one API task and ended before the two-hour window, whose full-active reference was approximately USD 0.3485 before variables/tail/continuing costs.

## Follow-up and remaining gates

Recheck actual account/service charges once billing updates past the run, and reconcile retained NAT/storage/other costs against estimates before final PD-16 cost acceptance. Use the current approved non-root budget path or human console; any paid detailed query needs its own authorization. Last verified eligible estimated credits USD 179.49 (Step 8) are historical, not refreshed here. USD 50 pause/review threshold and USD 25 reserve remain in force. No restart, budget change or resource change occurred. Step 13's remaining retention/lifecycle/owner-contact closeout and Step 14/upstream/peer acceptance remain open.
