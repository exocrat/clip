# CLIP — Canonical NFR and Architecture Experiment Results

Prepared 2026-11-06T11:40:16.524036+00:00. AWS account 335523638354; ap-south-1 (Mumbai).

The full canonical folder, including all raw captures and calculation files, is stored privately at `s3://clip-eval-gen-335523638354-261105/canonical-results/20261106/full-folder/`. Repository scope is this report; the evidence links below open that private S3 copy and require authorized AWS access.

This document evaluates the measured NFR requirements first, then the main ECS-versus-Lambda experiment. A = ECS-only. B = the same system with the selected Listing GET routes served 100% by Lambda. Writes, Saved, Wanted and Conversations remain on ECS. Both configurations use the same database, shared PgBouncer, data, search model, authentication rules and workload cases. No workload retries and no automatic Lambda-to-ECS fallback were enabled.

**Reading the numbers.** Latencies are milliseconds unless stated otherwise. p95 means 95% of the indicated successful responses were no slower than that value. Errors remain in the request-success denominator even when excluded from successful-response latency percentiles. Warm-ups are separate from measured windows. Requirements are judged against the PRD; operational accounting is reported separately.

API load and chat browsers ran on a separate EC2 generator in Mumbai over public HTTPS with normal certificate validation. The observations characterize this AWS-to-AWS network path, not arbitrary user/mobile/campus networks. The generator is separate from the application hosts. Each API performance run had fresh API tasks and, for B, a fresh Lambda runtime marker; shared host/database/pool caches were retained. Chat repetitions used the actual repaired browser application and active conversation tabs, without fresh API/Lambda resets.

**Application provenance.** API performance, main comparison and search-quality measurements use `ed0a6aa3fbe404d96e8a4181433463b59b9726f7`; final chat, integrated NFR-03 and later recovery checks use `ac7417f6fe5effae38e01a822d53b97db945e5ba`. The difference is limited to frontend conversation/history behavior and Discover cards plus their tests/documentation; backend/API/search logic is unchanged. Each run retains its own image and source receipts. Dataset fingerprint: `sha256:7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98`; model revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

The retained topology has two c7i-flex.large application hosts, two API tasks total (1 vCPU / 2 GiB each), a shared PgBouncer task, and one db.t4g.micro PostgreSQL database. B adds the selected-read Lambda at 3,008 MiB, a five-second timeout and ten available concurrent executions. Both application hosts remain running in B; this experiment does not assume an ECS downsizing saving.

## NFR-01 — Browse latency

At 20 browse requests/second, at least 95% of successful browse requests complete within one second. Image-body download time is excluded.

Each repetition has a 60-second warm-up followed by a 300-second measured window.

### Measured results

| Config / repetition | Within requirement / denominator | Requirement % | Successful / issued | HTTP errors / timeouts | Drops | p50 | p95 | p99 | PRD result |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 6,000 / 6,000 | 100.0000% | 6,000 / 6,000 | 0 / 0 | 0 | 18.82 | 23.36 | 33.83 | PASS |
| A2 | 6,000 / 6,000 | 100.0000% | 6,000 / 6,000 | 0 / 0 | 0 | 18.57 | 23.00 | 34.83 | PASS |
| A3 | 6,000 / 6,000 | 100.0000% | 6,000 / 6,000 | 0 / 0 | 0 | 18.68 | 23.98 | 47.88 | PASS |
| B1 | 6,000 / 6,000 | 100.0000% | 6,000 / 6,000 | 0 / 0 | 0 | 33.73 | 40.45 | 49.71 | PASS |
| B2 | 6,000 / 6,000 | 100.0000% | 6,000 / 6,000 | 0 / 0 | 0 | 37.81 | 47.00 | 61.40 | PASS |
| B3 | 6,000 / 6,000 | 100.0000% | 6,000 / 6,000 | 0 / 0 | 0 | 37.94 | 46.42 | 58.47 | PASS |

### Warm-up results — not mixed into the measured result

| Config / repetition | Successful / issued | HTTP errors | Timeouts | Drops | p50 | p95 | p99 |
|---|---|---|---|---|---|---|---|
| A1 | 1,200 / 1,200 | 0 | 0 | 0 | 19.79 | 25.16 | 40.91 |
| A2 | 1,200 / 1,200 | 0 | 0 | 0 | 18.95 | 23.55 | 34.03 |
| A3 | 1,200 / 1,200 | 0 | 0 | 0 | 19.18 | 26.28 | 81.48 |
| B1 | 1,134 / 1,200 | 65 | 1 | 0 | 36.56 | 45.29 | 85.64 |
| B2 | 1,118 / 1,200 | 80 | 2 | 0 | 39.74 | 52.15 | 110.32 |
| B3 | 1,128 / 1,200 | 71 | 1 | 0 | 40.10 | 52.04 | 98.97 |

Per-run reports, raw captures, runtime receipts and available telemetry: [NFR evidence folder](https://s3.console.aws.amazon.com/s3/buckets/clip-eval-gen-335523638354-261105?region=ap-south-1&prefix=canonical-results%2F20261106%2Ffull-folder%2Fevidence%2FNFR-01%2F&showversions=false).

## NFR-02 — Search latency

At 10 indexed searches/second, at least 95% of all issued eligible search requests complete within one second. Failures and timeouts remain violations; search relevance is evaluated separately in NFR-04.

Each repetition has a 60-second warm-up followed by a 300-second measured window.

### Measured results

| Config / repetition | Within requirement / denominator | Requirement % | Successful / issued | HTTP errors / timeouts | Drops | p50 | p95 | p99 | PRD result |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 3,000 / 3,000 | 100.0000% | 3,000 / 3,000 | 0 / 0 | 0 | 59.65 | 98.31 | 123.04 | PASS |
| A2 | 3,000 / 3,000 | 100.0000% | 3,000 / 3,000 | 0 / 0 | 0 | 60.08 | 100.62 | 125.72 | PASS |
| A3 | 3,000 / 3,000 | 100.0000% | 3,000 / 3,000 | 0 / 0 | 0 | 59.52 | 99.09 | 131.20 | PASS |
| B1 | 3,000 / 3,000 | 100.0000% | 3,000 / 3,000 | 0 / 0 | 0 | 80.28 | 123.88 | 148.47 | PASS |
| B2 | 3,000 / 3,000 | 100.0000% | 3,000 / 3,000 | 0 / 0 | 0 | 86.56 | 134.79 | 170.12 | PASS |
| B3 | 3,000 / 3,000 | 100.0000% | 3,000 / 3,000 | 0 / 0 | 0 | 82.45 | 129.80 | 157.24 | PASS |

### Warm-up results — not mixed into the measured result

| Config / repetition | Successful / issued | HTTP errors | Timeouts | Drops | p50 | p95 | p99 |
|---|---|---|---|---|---|---|---|
| A1 | 600 / 600 | 0 | 0 | 0 | 61.12 | 100.49 | 147.25 |
| A2 | 600 / 600 | 0 | 0 | 0 | 61.64 | 105.51 | 176.29 |
| A3 | 600 / 600 | 0 | 0 | 0 | 60.53 | 97.74 | 131.56 |
| B1 | 565 / 600 | 31 | 4 | 0 | 83.04 | 126.21 | 1,661.66 |
| B2 | 564 / 600 | 33 | 3 | 0 | 89.55 | 138.65 | 4,009.85 |
| B3 | 567 / 600 | 33 | 0 | 0 | 86.32 | 141.21 | 4,322.55 |

Per-run reports, raw captures, runtime receipts and available telemetry: [NFR evidence folder](https://s3.console.aws.amazon.com/s3/buckets/clip-eval-gen-335523638354-261105?region=ap-south-1&prefix=canonical-results%2F20261106%2Ffull-folder%2Fevidence%2FNFR-02%2F&showversions=false).

## NFR-03 — Peak API behavior

At a controlled 50 requests/second for five minutes, at least 95% of eligible requests succeed. No intentionally abusive requests were scheduled or excluded.

Each run schedules 15,000 measured operations: 4,500 browse, 3,750 Hybrid search, 2,250 detail, 1,500 Wanted reads, 1,500 conversation-list reads, 1,350 Saved reads, **100 sale-listing creations and 50 Wanted creations**. Warm-up schedules 3,000 operations including 20 sale listings and 10 Wanted creations. Photos are prepared before timing. Created sale listings have future availability so they do not change the frozen public browse/search cases. Each write has a unique operation ID.

### Measured results

| Config / repetition | Within requirement / denominator | Requirement % | Successful / issued | HTTP errors / timeouts | Drops | p50 | p95 | p99 | PRD result |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 15,000 / 15,000 | 100.0000% | 15,000 / 15,000 | 0 / 0 | 0 | 20.47 | 104.85 | 280.95 | PASS |
| A2 | 15,000 / 15,000 | 100.0000% | 15,000 / 15,000 | 0 / 0 | 0 | 20.35 | 99.16 | 157.75 | PASS |
| A3 | 15,000 / 15,000 | 100.0000% | 15,000 / 15,000 | 0 / 0 | 0 | 20.30 | 98.96 | 128.78 | PASS |
| B1 | 14,973 / 15,000 | 99.8200% | 14,973 / 15,000 | 27 / 0 | 0 | 36.65 | 128.37 | 202.48 | PASS |
| B2 | 14,980 / 15,000 | 99.8667% | 14,980 / 15,000 | 20 / 0 | 0 | 36.42 | 125.54 | 159.05 | PASS |
| B3 | 14,920 / 15,000 | 99.4667% | 14,920 / 15,000 | 80 / 0 | 0 | 36.75 | 126.64 | 232.98 | PASS |

### Warm-up results — not mixed into the measured result

| Config / repetition | Successful / issued | HTTP errors | Timeouts | Drops | p50 | p95 | p99 |
|---|---|---|---|---|---|---|---|
| A1 | 3,000 / 3,000 | 0 | 0 | 0 | 20.01 | 103.85 | 228.09 |
| A2 | 3,000 / 3,000 | 0 | 0 | 0 | 20.80 | 124.34 | 775.37 |
| A3 | 3,000 / 3,000 | 0 | 0 | 0 | 20.93 | 103.31 | 309.37 |
| B1 | 2,870 / 3,000 | 128 | 2 | 0 | 39.62 | 152.88 | 441.75 |
| B2 | 2,878 / 3,000 | 115 | 7 | 0 | 38.79 | 135.17 | 218.98 |
| B3 | 2,909 / 3,000 | 89 | 2 | 0 | 37.62 | 130.65 | 296.09 |

### Integrated operations, measured phase

| Run | Operation | Correct / issued | Other outcomes | p95 |
|---|---|---|---|---|
| A1 | browse | 4,500 / 4,500 | 0 | 52.79 |
| A1 | conversations | 1,500 / 1,500 | 0 | 35.91 |
| A1 | detail | 2,250 / 2,250 | 0 | 49.03 |
| A1 | listing_create | 100 / 100 | 0 | 44.09 |
| A1 | saved | 1,350 / 1,350 | 0 | 72.95 |
| A1 | search | 3,750 / 3,750 | 0 | 129.01 |
| A1 | wanted | 1,500 / 1,500 | 0 | 51.52 |
| A1 | wanted_create | 50 / 50 | 0 | 38.44 |
| A2 | browse | 4,500 / 4,500 | 0 | 42.64 |
| A2 | conversations | 1,500 / 1,500 | 0 | 33.54 |
| A2 | detail | 2,250 / 2,250 | 0 | 40.58 |
| A2 | listing_create | 100 / 100 | 0 | 47.64 |
| A2 | saved | 1,350 / 1,350 | 0 | 51.79 |
| A2 | search | 3,750 / 3,750 | 0 | 118.15 |
| A2 | wanted | 1,500 / 1,500 | 0 | 49.40 |
| A2 | wanted_create | 50 / 50 | 0 | 136.28 |
| A3 | browse | 4,500 / 4,500 | 0 | 44.32 |
| A3 | conversations | 1,500 / 1,500 | 0 | 33.56 |
| A3 | detail | 2,250 / 2,250 | 0 | 40.18 |
| A3 | listing_create | 100 / 100 | 0 | 35.61 |
| A3 | saved | 1,350 / 1,350 | 0 | 47.87 |
| A3 | search | 3,750 / 3,750 | 0 | 110.74 |
| A3 | wanted | 1,500 / 1,500 | 0 | 49.98 |
| A3 | wanted_create | 50 / 50 | 0 | 38.48 |
| B1 | browse | 4,487 / 4,500 | http_error=13 | 65.93 |
| B1 | conversations | 1,500 / 1,500 | 0 | 33.59 |
| B1 | detail | 2,244 / 2,250 | http_error=6 | 56.99 |
| B1 | listing_create | 100 / 100 | 0 | 96.63 |
| B1 | saved | 1,350 / 1,350 | 0 | 60.86 |
| B1 | search | 3,742 / 3,750 | http_error=8 | 149.81 |
| B1 | wanted | 1,500 / 1,500 | 0 | 52.05 |
| B1 | wanted_create | 50 / 50 | 0 | 78.89 |
| B2 | browse | 4,492 / 4,500 | http_error=8 | 59.56 |
| B2 | conversations | 1,500 / 1,500 | 0 | 30.16 |
| B2 | detail | 2,245 / 2,250 | http_error=5 | 53.90 |
| B2 | listing_create | 100 / 100 | 0 | 70.12 |
| B2 | saved | 1,350 / 1,350 | 0 | 51.61 |
| B2 | search | 3,743 / 3,750 | http_error=7 | 140.98 |
| B2 | wanted | 1,500 / 1,500 | 0 | 45.59 |
| B2 | wanted_create | 50 / 50 | 0 | 47.85 |
| B3 | browse | 4,466 / 4,500 | http_error=34 | 64.65 |
| B3 | conversations | 1,500 / 1,500 | 0 | 35.91 |
| B3 | detail | 2,235 / 2,250 | http_error=15 | 56.99 |
| B3 | listing_create | 99 / 100 | http_error=1 | 88.98 |
| B3 | saved | 1,349 / 1,350 | http_error=1 | 71.75 |
| B3 | search | 3,721 / 3,750 | http_error=29 | 148.95 |
| B3 | wanted | 1,500 / 1,500 | 0 | 53.92 |
| B3 | wanted_create | 50 / 50 | 0 | 41.89 |

All three repetitions meet the PRD requirement for both configurations. The B3 measured 80 errors comprise 78 HTTP 502s on Lambda reads (34 browse, 15 detail, 29 search), one Saved HTTP 503 and one listing-create HTTP 503. AWS recorded 78 Lambda throttles in the corresponding measured minutes. The listing creation failed in ECS Identity authentication after approximately 1,001 ms, before the listing handler; nearby connection acquisitions also stalled. The one-second Identity acquisition deadline is consistent with that failure. Minute-average RDS CPU remained below 48% and API CPU below 8% in this run; these averages do not identify the exact cause of the brief stall.

The rejected listing remains a measured failure. Cleanup found 119 created listings from the 120 warm-up-plus-measured attempts in B3, consistent with rejection before creation; all were marked unavailable. All other runs completed their 120 listing creations. Each run completed all 60 Wanted creations including warm-up. The separate write-reconciliation flag in the original B3 report does not change the PRD percentage result. Owned-write cleanup is confirmed for every run.

Per-run reports, raw captures, runtime receipts and available telemetry: [NFR evidence folder](https://s3.console.aws.amazon.com/s3/buckets/clip-eval-gen-335523638354-261105?region=ap-south-1&prefix=canonical-results%2F20261106%2Ffull-folder%2Fevidence%2FNFR-03%2F&showversions=false).

## NFR-04 — Search usefulness

Requirement: at least 20 representative manually labeled queries, with a relevant result in the first five for at least 80% of queries (Success@5). The same 22-query set and labels are used for A and B. This is a relevance check, not a latency benchmark.

| Configuration | Hits / queries | Success@5 | Retrieval failures | PRD result |
|---|---|---|---|---|
| A | 22 / 22 | 100.0000% | 0 | PASS |
| B | 22 / 22 | 100.0000% | 0 | PASS |

No warm-up phase applies to this fixed-query quality evaluation. Every query outcome and returned top-five IDs are retained in [NFR-04 evidence](https://s3.console.aws.amazon.com/s3/buckets/clip-eval-gen-335523638354-261105?region=ap-south-1&prefix=canonical-results%2F20261106%2Ffull-folder%2Fevidence%2FNFR-04%2F&showversions=false).

## NFR-05 — Active-chat display latency

Requirement: with both conversation pages open, at least 95% of messages become visible to the recipient within five seconds of submission under normal workload. Timing covers the actual sender form submission to the actual recipient display event, observed on one monotonic clock through local browser automation. It does not stop at a successful send response. Chat stays on ECS in both A and B; selected-read background traffic follows each configuration. Each repetition measures 60 messages over five minutes with 10 background reads/second.

| Config / repetition | On time / messages | On-time % | Late / failed / undisplayed / missing | p50 | p95 | p99 | Maximum | Background success / issued | PRD result |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 60 / 60 | 100.0000% | 0 / 0 / 0 / 0 | 1,294.23 | 2,197.06 | 2,243.04 | 2,249.46 | 3,000 / 3,000 | PASS |
| A2 | 60 / 60 | 100.0000% | 0 / 0 / 0 / 0 | 1,265.23 | 2,125.67 | 2,229.51 | 2,298.87 | 3,000 / 3,000 | PASS |
| A3 | 60 / 60 | 100.0000% | 0 / 0 / 0 / 0 | 1,263.60 | 2,142.52 | 2,217.93 | 2,251.16 | 3,000 / 3,000 | PASS |
| B1 | 60 / 60 | 100.0000% | 0 / 0 / 0 / 0 | 1,303.32 | 2,213.57 | 2,242.11 | 2,248.83 | 3,000 / 3,000 | PASS |
| B2 | 60 / 60 | 100.0000% | 0 / 0 / 0 / 0 | 1,359.07 | 2,220.41 | 2,287.65 | 2,341.84 | 3,000 / 3,000 | PASS |
| B3 | 60 / 60 | 100.0000% | 0 / 0 / 0 / 0 | 1,249.19 | 2,135.57 | 2,237.12 | 2,248.46 | 2,965 / 3,000 | PASS |

**Warm-up:** each run keeps both authenticated conversation pages active for 60 seconds before measured sends. No warm-up messages or background workload are scheduled by this browser procedure, so there is no warm-up message-latency distribution to invent or combine with the measured samples.

All 360 measured messages were displayed within five seconds. B3 background traffic returned 2,965 successful responses and 35 HTTP errors from 3,000 issued reads, with no generator drops. Those errors are retained and disclosed; the PRD chat criterion concerns message visibility under the normal offered workload, not a requirement for 100% background-request success. Raw submit/display timestamps and complete background captures are in [NFR-05 evidence](https://s3.console.aws.amazon.com/s3/buckets/clip-eval-gen-335523638354-261105?region=ap-south-1&prefix=canonical-results%2F20261106%2Ffull-folder%2Fevidence%2FNFR-05%2F&showversions=false).

## NFR-06 — Runtime recovery

Requirement: starting with at least two healthy serving instances, forced loss of one runtime restores configured healthy capacity within 240 seconds. Request failures during recovery must be measured. These checks stop one API task on the non-pool host; they do not test loss of an EC2 host or the shared pool. B includes Lambda Listing reads and ECS account reads, without Lambda fallback.

| Configuration / observation | Recovery seconds | Recovery successful / observed | Failures | Drops | Baseline observations / failures | PRD result |
|---|---|---|---|---|---|---|
| A / Nov 5 | 93.240 | 300 / 300 | 0 | 0 | 60 / 0 | PASS |
| A / Nov 6 | 79.279 | 300 / 300 | 0 | 0 | 60 / 0 | PASS |
| B / Nov 5 | 74.240 | 300 / 300 | 0 | 0 | 60 / 0 | PASS |
| B / Nov 6 | 87.266 | 300 / 300 | 0 | 0 | 60 / 0 | PASS |

Each test includes a 60-second pre-fault baseline and up to 300 seconds of post-fault observation at one read/second. This baseline is shown separately from the recovery timer; it is not an API performance warm-up. All checks restored two healthy serving tasks and observed zero recovery request failures. Exact task events and request timestamps: [NFR-06 evidence](https://s3.console.aws.amazon.com/s3/buckets/clip-eval-gen-335523638354-261105?region=ap-south-1&prefix=canonical-results%2F20261106%2Ffull-folder%2Fevidence%2FNFR-06%2F&showversions=false).

## NFR-07 — Database recovery

Requirement: restore the latest available managed backup into a usable isolated test database within 30 minutes. Timing continues through seven integrity checks and normal test-account sign-in/read smoke, not merely the RDS “available” state. This is shared-system evidence because A and B use the same database and restore procedure.

| Observation | Elapsed seconds | Elapsed minutes | Integrity checks | Normal sign-in / reads | Isolated target deleted | PRD result |
|---|---|---|---|---|---|---|
| Nov 5 | 525.592 | 8.760 | 7 / 7 | Verified | Yes | PASS |
| Nov 6 | 549.187 | 9.153 | 7 / 7 | Verified | Yes | PASS |

The seven checks cover the migration head, query execution, validated foreign keys, user–listing and user–Wanted relationships, conversation origin/membership, and conversation-offer relationships. Each check uses that date’s latest available managed snapshot. Both isolated database targets were removed after verification; the source database was preserved. No separate warm-up applies. Full restore timelines and cleanup receipts: [NFR-07 evidence](https://s3.console.aws.amazon.com/s3/buckets/clip-eval-gen-335523638354-261105?region=ap-south-1&prefix=canonical-results%2F20261106%2Ffull-folder%2Fevidence%2FNFR-07%2F&showversions=false).

## NFR-08 — Project cloud spending

Requirement: total cloud spending for implementation and evaluation below USD 200, with declared duration/resource/concurrency limits for load experiments. Credits are reported separately and do not reduce the gross-cost test. The account contains only this project, as confirmed by the project owner.

| Budget item | USD |
|---|---|
| Recorded positive AWS charges | 47.457384 |
| Credits / refunds, separately | 47.457384 |
| Unbilled / retained-resource reserve | 10.000000 |
| Recorded gross plus reserve | 57.457384 |
| Project limit | 200.000000 |
| Headroom after reserve | 142.542616 |

Billing was refreshed at 2026-11-06T11:33:36.474671+00:00. **The recorded spend plus reserve is below the limit. Final settled-billing confirmation remains pending**, because AWS usage is still estimated/delayed and retained resources continue to accrue charges. This is a budget status, not a claim that the final bill has settled. No results S3 data has been deleted. The gross/credit source and per-run cost model are in [cost evidence and calculations](https://s3.console.aws.amazon.com/s3/buckets/clip-eval-gen-335523638354-261105?region=ap-south-1&prefix=canonical-results%2F20261106%2Ffull-folder%2Fanalysis%2Fcost%2F&showversions=false).

## Main experiment — ECS-only versus ECS plus Lambda

### Design and interpretation

Three paired cycles per architecture, each with low (0.2 requests/second), normal (10 requests/second) and burst (50 requests/second) runs: 18 measured runs total. Each has a separate 60-second warm-up and a 300-second measured interval. Burst warm-up runs at 10 requests/second; low and normal warm up at their own rate. The read mix is 50% browse, 30% Hybrid search and 20% listing detail. The order alternates A/B, B/A, A/B across cycles.

The full comparison has no PRD pass/fail label. It compares latency, reliability and whole retained-system cost. Both versions retain both ECS hosts and the shared services. B uses 100% Lambda only for the approved Listing GET routes. The same approved cases, data, model and no-retry policy are used throughout. Fresh runtime resets do not clear shared database/pool or host caches.

### Every measured run

| Run | Correct / issued | Success % | HTTP errors / timeouts | Drops | p50 | p95 | p99 | Correct req/s |
|---|---|---|---|---|---|---|---|---|
| A1 low | 60 / 60 | 100.0000% | 0 / 0 | 0 | 22.34 | 99.28 | 225.51 | 0.2000 |
| A1 normal | 3,000 / 3,000 | 100.0000% | 0 / 0 | 0 | 19.76 | 96.01 | 108.72 | 10.0000 |
| A1 burst | 15,000 / 15,000 | 100.0000% | 0 / 0 | 0 | 24.87 | 104.20 | 225.85 | 50.0000 |
| B1 low | 60 / 60 | 100.0000% | 0 / 0 | 0 | 48.31 | 136.48 | 265.01 | 0.2000 |
| B1 normal | 3,000 / 3,000 | 100.0000% | 0 / 0 | 0 | 37.68 | 120.08 | 131.27 | 10.0000 |
| B1 burst | 14,996 / 15,000 | 99.9733% | 4 / 0 | 0 | 39.60 | 122.34 | 145.52 | 49.9867 |
| B2 low | 60 / 60 | 100.0000% | 0 / 0 | 0 | 45.53 | 124.59 | 208.80 | 0.2000 |
| B2 normal | 3,000 / 3,000 | 100.0000% | 0 / 0 | 0 | 39.29 | 126.19 | 163.96 | 10.0000 |
| B2 burst | 14,995 / 15,000 | 99.9667% | 5 / 0 | 0 | 39.27 | 121.65 | 152.61 | 49.9833 |
| A2 low | 60 / 60 | 100.0000% | 0 / 0 | 0 | 22.64 | 101.52 | 330.53 | 0.2000 |
| A2 normal | 3,000 / 3,000 | 100.0000% | 0 / 0 | 0 | 19.83 | 95.48 | 105.93 | 10.0000 |
| A2 burst | 14,999 / 15,000 | 99.9933% | 1 / 0 | 0 | 24.64 | 104.20 | 151.01 | 49.9967 |
| A3 low | 60 / 60 | 100.0000% | 0 / 0 | 0 | 22.99 | 121.83 | 222.65 | 0.2000 |
| A3 normal | 3,000 / 3,000 | 100.0000% | 0 / 0 | 0 | 19.54 | 95.71 | 109.56 | 10.0000 |
| A3 burst | 15,000 / 15,000 | 100.0000% | 0 / 0 | 0 | 23.99 | 105.52 | 177.42 | 50.0000 |
| B3 low | 60 / 60 | 100.0000% | 0 / 0 | 0 | 47.70 | 141.91 | 261.44 | 0.2000 |
| B3 normal | 3,000 / 3,000 | 100.0000% | 0 / 0 | 0 | 39.52 | 121.23 | 137.46 | 10.0000 |
| B3 burst | 14,986 / 15,000 | 99.9067% | 14 / 0 | 0 | 39.11 | 120.17 | 154.41 | 49.9533 |

### Every warm-up — including startup failures

| Run | Correct / issued | HTTP errors | Timeouts | Drops | p50 | p95 | p99 |
|---|---|---|---|---|---|---|---|
| A1 low | 12 / 12 | 0 | 0 | 0 | 23.06 | 190.45 | 311.16 |
| A1 normal | 600 / 600 | 0 | 0 | 0 | 20.91 | 97.05 | 117.43 |
| A1 burst | 600 / 600 | 0 | 0 | 0 | 21.10 | 95.18 | 104.60 |
| B1 low | 12 / 12 | 0 | 0 | 0 | 62.69 | 1,926.56 | 3,398.43 |
| B1 normal | 561 / 600 | 35 | 4 | 0 | 40.28 | 127.17 | 1,837.85 |
| B1 burst | 567 / 600 | 31 | 2 | 0 | 41.55 | 140.09 | 3,985.76 |
| B2 low | 12 / 12 | 0 | 0 | 0 | 44.54 | 2,051.32 | 3,630.25 |
| B2 normal | 567 / 600 | 32 | 1 | 0 | 41.14 | 127.75 | 4,012.09 |
| B2 burst | 565 / 600 | 32 | 3 | 0 | 43.54 | 131.42 | 3,817.86 |
| A2 low | 12 / 12 | 0 | 0 | 0 | 23.04 | 186.56 | 305.27 |
| A2 normal | 600 / 600 | 0 | 0 | 0 | 21.51 | 97.46 | 262.93 |
| A2 burst | 600 / 600 | 0 | 0 | 0 | 21.22 | 96.34 | 119.19 |
| A3 low | 12 / 12 | 0 | 0 | 0 | 25.63 | 188.60 | 270.68 |
| A3 normal | 600 / 600 | 0 | 0 | 0 | 20.79 | 95.33 | 116.34 |
| A3 burst | 600 / 600 | 0 | 0 | 0 | 21.55 | 94.96 | 128.91 |
| B3 low | 12 / 12 | 0 | 0 | 0 | 77.83 | 2,426.64 | 4,377.55 |
| B3 normal | 568 / 600 | 30 | 2 | 0 | 42.69 | 127.23 | 3,877.04 |
| B3 burst | 570 / 600 | 29 | 1 | 0 | 40.50 | 127.51 | 3,885.88 |

Warm-up differences are substantive results: Lambda incurs visible startup failures even when the later measured normal window is fully successful. They are preserved separately and are not removed from this comparison.

### Across the three measured repetitions

Mean ± SD below is the mean and sample standard deviation of the three run percentiles; it is not a pooled percentile. Scoring instead uses the median of the per-run values.

| Configuration | Load | Correct / issued | p95 mean ± SD | p95 median used for scoring | p99 mean ± SD |
|---|---|---|---|---|---|
| A | low | 180 / 180 | 107.542 ± 12.421 | 101.518 | 259.565 ± 61.479 |
| A | normal | 9,000 / 9,000 | 95.731 ± 0.264 | 95.711 | 108.071 ± 1.898 |
| A | burst | 44,999 / 45,000 | 104.637 ± 0.763 | 104.197 | 184.760 ± 37.951 |
| B | low | 180 / 180 | 134.329 ± 8.856 | 136.485 | 245.083 ± 31.473 |
| B | normal | 9,000 / 9,000 | 122.501 ± 3.246 | 121.233 | 144.231 ± 17.361 |
| B | burst | 44,977 / 45,000 | 121.386 ± 1.108 | 121.647 | 150.848 ± 4.696 |

### Normal-load degradation guard

The approved practical guard allows B’s median per-route p95 to exceed A’s by at most the larger of 50 ms or 10% of A’s value; its median failure share may increase by at most one percentage point.

| Read class | A median p95 | B median p95 | Extra latency | Allowed extra | Guard |
|---|---|---|---|---|---|
| browse | 23.692 | 46.234 | 22.542 | 50.000 | MET |
| search | 103.391 | 129.898 | 26.507 | 50.000 | MET |
| detail | 20.501 | 41.409 | 20.908 | 50.000 | MET |

### Measured failures and infrastructure signals

A had one measured browse HTTP 502 in its second burst repetition. AWS recorded one load-balancer-generated 502 in the matching minute, without a target 5xx increase; the exact underlying connection failure is unconfirmed. B had 4, 5 and 14 measured errors in its burst repetitions. Throttling at ten concurrent Lambda executions is supported by the retained AWS counters; minute aggregates alone do not establish the cause of every individual request. No measured run had a generator drop or a timeout. Successful-request p95 therefore must be read alongside the errors and separate warm-up tables.

Full per-route distributions and infrastructure series remain in each run’s evidence. The CSVs and JSON summaries support calculations without reading other directories. This AWS-region workload does not establish behavior for arbitrary internet paths, a different data size, larger concurrency quotas or a resized topology.

### Whole-system cost per 1,000 correct operations

Costs below are **pre-credit estimates**, not settled invoice allocations. The fixed retained app topology is allocated by phase duration: both EC2 hosts, RDS, NAT, ALB, four retained public IPv4 addresses, 90 GiB retained EC2 disks and 20 GiB database storage. Pool CPU is already on an existing host and is not charged as another host. The separate generator is an evaluation expense in NFR-08, not an application serving resource.

Lambda compute uses actual platform billed GB-seconds and request counts from retained REPORT logs, including completion-tail usage. ALB LCU, NAT processing and log ingestion use historical minute metrics with overlap allocation. The frozen November regional price basis is used; logging is $0.67/GB from the official Price List API. A common $0.005/hour retained ECR/S3/log-storage allowance and a $0.02/GB allowance on observed NAT bytes for possible cross-AZ transfer make residual assumptions explicit. Metric-window boundaries, other same-minute use, cached storage and unmetered regional traffic prevent these estimates from being called exact bills. Full component arithmetic, prices and billed-event hashes are in `analysis/cost/`.

| Run | Measured cost USD | Measured USD / 1,000 correct | Warm-up cost USD | Lambda measured billed GB-s |
|---|---|---|---|---|
| A1 low | 0.02707621 | 0.45127020 | 0.00538657 | 0.000 |
| A1 normal | 0.03293604 | 0.01097868 | 0.00622361 | 0.000 |
| A1 burst | 0.05708064 | 0.00380538 | 0.00685891 | 0.000 |
| B1 low | 0.02720316 | 0.45338601 | 0.00562620 | 8.063 |
| B1 normal | 0.03908656 | 0.01302885 | 0.00981862 | 360.937 |
| B1 burst | 0.09379361 | 0.00625458 | 0.00999948 | 2,130.777 |
| B2 low | 0.02720922 | 0.45348700 | 0.00563901 | 7.779 |
| B2 normal | 0.03972677 | 0.01324226 | 0.00979583 | 386.954 |
| B2 burst | 0.09404629 | 0.00627184 | 0.00986827 | 2,136.782 |
| A2 low | 0.02708224 | 0.45137059 | 0.00541290 | 0.000 |
| A2 normal | 0.03296765 | 0.01098922 | 0.00632218 | 0.000 |
| A2 burst | 0.05662779 | 0.00377544 | 0.00700336 | 0.000 |
| A3 low | 0.02707447 | 0.45124120 | 0.00539209 | 0.000 |
| A3 normal | 0.03309048 | 0.01103016 | 0.00653791 | 0.000 |
| A3 burst | 0.05744340 | 0.00382956 | 0.00655928 | 0.000 |
| B3 low | 0.02722838 | 0.45380625 | 0.00565432 | 8.812 |
| B3 normal | 0.03934339 | 0.01311446 | 0.00948506 | 376.620 |
| B3 burst | 0.09268178 | 0.00618456 | 0.01013770 | 2,126.580 |

The 18 measured windows total **$0.831698 estimated**; their separate warm-ups total **$0.131721 estimated**. Reset/idle intervals, image builds, all NFRs and generator expenses are additional project costs represented in the project ledger, not silently allocated twice into these measured windows.

### Approved weighted scoring

The predeclared weights are burst latency 35%, whole-system cost 30%, normal latency 20% and reliability 15%. The anchors are fixed: burst p95 500–3,000 ms; normal p95 250–1,000 ms; cost $0.005–$0.050 per 1,000 correct operations; failure share 0–5 percentage points. For each input, points = `clamp(100 × (poor − input) / (poor − good), 0, 100)`. Latency and normal cost use medians of the three per-run values. Reliability uses the larger of the normal and burst median failure percentages. Warm-ups remain reported above and are not substituted into this frozen steady-window score.

| Score input | A | B |
|---|---|---|
| Median burst p95, ms | 104.197097600 | 121.647487700 |
| Median normal p95, ms | 95.711453750 | 121.233378500 |
| Median normal USD / 1,000 correct, estimated | 0.010989216127 | 0.013114463560 |
| Reliability input, percentage points | 0.000000000000 | 0.033333333333 |

| Component | Weight | A points | A weighted contribution | B points | B weighted contribution |
|---|---|---|---|---|---|
| burst | 0.35 | 100.000000000 | 35.000000000 | 100.000000000 | 35.000000000 |
| cost | 0.30 | 86.690630829 | 26.007189249 | 81.967858756 | 24.590357627 |
| normal | 0.20 | 100.000000000 | 20.000000000 | 100.000000000 | 20.000000000 |
| reliability | 0.15 | 100.000000000 | 15.000000000 | 99.333333333 | 14.900000000 |

| Architecture | Total / 100 | Interpretation |
|---|---|---|
| A — ECS-only | 96.007189249 | Higher calculated score under the stated cost estimate |
| B — selected reads on Lambda | 94.490357627 | Measured latency anchors met; extra serving cost and burst failures reduce score |

Both latency components reach 100 points because all median p95s are below their “good” anchors; the scoring scale intentionally saturates and does not erase the raw latency difference. The cost component is an estimate-based calculation. **A verified final weighted winner remains conditional on cost-allocation reconciliation and final budget closeout**; the observed latency/reliability comparison and the numerical estimated scores are available now. Full-precision numeric values are retained in `analysis/scores.json`, without rounding inputs before scoring.

### Per-route main-experiment results

| Run | Route | Correct / issued | p50 | p95 | p99 |
|---|---|---|---|---|---|
| A1 low | browse | 30 / 30 | 21.33 | 24.87 | 28.78 |
| A1 low | detail | 12 / 12 | 18.68 | 50.73 | 79.44 |
| A1 low | search | 18 / 18 | 69.45 | 196.96 | 271.64 |
| A1 normal | browse | 1,500 / 1,500 | 18.91 | 23.54 | 36.33 |
| A1 normal | detail | 600 / 600 | 16.37 | 20.50 | 25.40 |
| A1 normal | search | 900 / 900 | 59.53 | 103.82 | 125.94 |
| A1 burst | browse | 7,500 / 7,500 | 18.27 | 40.94 | 145.76 |
| A1 burst | detail | 3,000 / 3,000 | 32.98 | 59.90 | 149.30 |
| A1 burst | search | 4,500 / 4,500 | 92.88 | 123.15 | 281.77 |
| B1 low | browse | 30 / 30 | 47.44 | 50.50 | 52.54 |
| B1 low | detail | 12 / 12 | 43.60 | 105.80 | 163.33 |
| B1 low | search | 18 / 18 | 96.07 | 182.01 | 348.91 |
| B1 normal | browse | 1,500 / 1,500 | 36.48 | 43.17 | 52.75 |
| B1 normal | detail | 600 / 600 | 33.80 | 41.41 | 101.65 |
| B1 normal | search | 900 / 900 | 80.82 | 128.64 | 140.19 |
| B1 burst | browse | 7,499 / 7,500 | 35.19 | 49.07 | 82.79 |
| B1 burst | detail | 3,000 / 3,000 | 46.85 | 65.06 | 92.71 |
| B1 burst | search | 4,497 / 4,500 | 105.93 | 133.58 | 197.45 |
| B2 low | browse | 30 / 30 | 44.43 | 51.54 | 92.21 |
| B2 low | detail | 12 / 12 | 42.85 | 47.02 | 48.83 |
| B2 low | search | 18 / 18 | 91.22 | 160.41 | 286.97 |
| B2 normal | browse | 1,500 / 1,500 | 37.93 | 46.23 | 56.74 |
| B2 normal | detail | 600 / 600 | 35.02 | 42.97 | 62.85 |
| B2 normal | search | 900 / 900 | 84.75 | 148.77 | 252.65 |
| B2 burst | browse | 7,500 / 7,500 | 34.93 | 50.37 | 81.68 |
| B2 burst | detail | 3,000 / 3,000 | 47.10 | 68.96 | 98.11 |
| B2 burst | search | 4,495 / 4,500 | 105.33 | 137.91 | 194.65 |
| A2 low | browse | 30 / 30 | 21.47 | 27.12 | 33.82 |
| A2 low | detail | 12 / 12 | 18.46 | 20.56 | 21.43 |
| A2 low | search | 18 / 18 | 64.76 | 315.15 | 355.39 |
| A2 normal | browse | 1,500 / 1,500 | 18.93 | 24.84 | 48.23 |
| A2 normal | detail | 600 / 600 | 16.07 | 20.74 | 29.49 |
| A2 normal | search | 900 / 900 | 60.13 | 101.06 | 122.14 |
| A2 burst | browse | 7,499 / 7,500 | 17.75 | 37.31 | 86.85 |
| A2 burst | detail | 3,000 / 3,000 | 33.56 | 64.79 | 108.64 |
| A2 burst | search | 4,500 / 4,500 | 93.22 | 126.10 | 197.60 |
| A3 low | browse | 30 / 30 | 22.26 | 72.89 | 152.39 |
| A3 low | detail | 12 / 12 | 19.49 | 23.16 | 23.24 |
| A3 low | search | 18 / 18 | 63.04 | 198.36 | 261.87 |
| A3 normal | browse | 1,500 / 1,500 | 18.79 | 23.69 | 42.48 |
| A3 normal | detail | 600 / 600 | 16.40 | 19.62 | 24.52 |
| A3 normal | search | 900 / 900 | 59.67 | 103.39 | 124.93 |
| A3 burst | browse | 7,500 / 7,500 | 18.00 | 36.71 | 118.11 |
| A3 burst | detail | 3,000 / 3,000 | 32.34 | 63.04 | 123.58 |
| A3 burst | search | 4,500 / 4,500 | 93.25 | 132.03 | 230.36 |
| B3 low | browse | 30 / 30 | 45.86 | 63.52 | 74.85 |
| B3 low | detail | 12 / 12 | 41.44 | 65.40 | 83.57 |
| B3 low | search | 18 / 18 | 96.30 | 220.84 | 327.02 |
| B3 normal | browse | 1,500 / 1,500 | 38.15 | 46.79 | 71.69 |
| B3 normal | detail | 600 / 600 | 34.67 | 41.13 | 48.27 |
| B3 normal | search | 900 / 900 | 82.77 | 129.90 | 176.01 |
| B3 burst | browse | 7,497 / 7,500 | 34.70 | 47.40 | 83.42 |
| B3 burst | detail | 2,994 / 3,000 | 46.38 | 64.30 | 87.77 |
| B3 burst | search | 4,495 / 4,500 | 105.15 | 135.19 | 210.24 |

### Evidence navigation

`evidence/` contains the selected original captures and reports, grouped by NFR then main experiment. `analysis/results.json`, `analysis/run-results.csv`, `analysis/scores.json` and `analysis/cost/allocation.json` contain the derived calculations. `evidence-manifest.json` records SHA-256 values and the S3 object locations for copied evidence. `reference/PRD.pdf` and `reference/frozen-prices.json` retain the requirement and regional price basis. Original captures are not rewritten.

Existing private versioned cloud backups remain at `s3://clip-eval-gen-335523638354-261105/results/cloud-261105/`, `results/repeat-261106/`, `results/final-nfr-261106/` and `results/nfr03-canonical-261106/`. No cloud result objects or bucket settings were deleted or changed while preparing this report.

## Final result

**NFR-01 through NFR-07 meet their measured PRD requirements for the applicable configurations.** NFR-03 passes in every final repetition, including B3 at 99.4667%; its observed failures remain included. Chat displayed every measured message within five seconds. Runtime recovery stayed below 94 seconds in all retained observations; isolated database restore through sign-in/read smoke stayed below ten minutes.

**NFR-08 is below budget on current evidence:** $47.457384 recorded gross plus $10 reserve versus the $200 limit. Final settled-billing confirmation remains open.

**ECS-only is the supported choice for this measured deployment.** It has lower measured normal and burst p95 latency, fewer measured errors and no observed warm-up request failures. Its calculated score is **96.007/100**, versus **94.490/100** for ECS plus Lambda, using the stated cost estimate. Lambda also meets the measured NFR requirements, but adding it without reducing the retained ECS topology did not improve this experiment’s overall trade-off. This conclusion is bounded to the tested source, data, regions, quota, workload and retained topology; it is not a universal ranking of ECS and Lambda.
