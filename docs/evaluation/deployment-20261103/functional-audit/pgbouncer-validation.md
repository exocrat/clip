# PgBouncer release evidence — 2026-11-04

All capacity runs below are local diagnostics with ten-second warm-up and sixty-second measurement, not deployed NFR acceptance. Raw output remains unchanged. The full profile rates, reviewed cases and failure denominators remain unchanged. Exact private evidence root:

`/home/suraj/src/.clip-private/pgbouncer-20261104/`

## Isolated repeat checks

`capacity-09/result.json` records completion, source hashes, timing binary receipt and removal of owned local resources. Two ECS processes; no Lambda copies or competing regression/build jobs during these runs. Each row issued exactly 3,000 measured operations at 50/s.

| Run/report basename | Correct / issued | Drops | p95 | Mean DB CPU, two-core quota |
|---|---:|---:|---:|---:|
| `lunch-a-exp-05-9033d1.report` | 3000/3000 | 0 | 102.98 ms | 32.74% |
| `lunch-a-nfr-03-25106b.report` | 3000/3000 | 0 | Per-route values in report | 25.83% |
| `lunch-a-exp-05-290b41.report` | 3000/3000 | 0 | 78.46 ms | 26.55% |
| `lunch-a-nfr-03-c98d08.report` | 3000/3000 | 0 | Per-route values in report | 27.17% |

Both mixed-workload repetitions reconciled their controlled writes and met the short diagnostic threshold. Read-burst p95 is not an NFR-01/02 verdict. CPU averages cover the captured run interval including warm-up/drain, not a claim about the AWS instance.

## Browse/search checks

`capacity-08/`: ten simulated Lambda environments, two ECS processes and the actual bounded pool; no competing regression test.

| Run/report basename | Issued | Outcomes | Drops | p95 |
|---|---:|---|---:|---:|
| `lunch-a-nfr-01-8e96fb.report` | 1200 | {'correct': 1200} | 0 | 17.95 ms |
| `lunch-a-nfr-02-b2adc6.report` | 600 | {'completed': 600} | 0 | 105.69 ms |
| `lunch-b-nfr-01-3be7d8.report` | 1200 | {'correct': 1200} | 0 | 18.14 ms |
| `lunch-b-nfr-02-3297e9.report` | 600 | {'completed': 600} | 0 | 108.51 ms |

All four met their own short diagnostic thresholds. The reports deliberately retain `nfr_accepted=false`; the local wrapper binds the custom monotonic binary separately from the preview report.

## Failures and qualifications retained

- `capacity-01`: first half-core pool A run had 2,968 correct / 2,977 issued, nine errors and 24 generator drops.
- `capacity-02`: incomplete due to a Decimal serialization bug in newly added diagnostic tooling; fixed, original evidence retained.
- `capacity-03`: half-core pool CPU throttling during B; four-environment serialized dispatch was also limiting.
- `capacity-04`: one-core pool, four Lambda copies, fresh clients. A 3,000/3,000 correct, p95 122.88 ms; B incomplete and failed. DB averaged 0.615 of two cores, while the pool averaged 0.602 of one core.
- `capacity-05`: incomplete due to a new harness NameError; fixed, original evidence retained.
- `capacity-06`: retained clients and ten Lambda copies. A burst 3,000/3,000 correct; B burst 2,946/3,000 correct with 54 local concurrency throttles. Subsequent A mixed workload failed severely. Its exact cause is unresolved.
- `capacity-07`: A mixed workload 3,000/3,000 correct; B 2,972/3,000 correct with 28 local throttles. Part of this run overlapped a regression suite, which was stopped. Do not treat it as an isolated capacity measurement.
- `capacity-09` did not reproduce the earlier A failure, but two clean repetitions do not establish its cause or guarantee AWS performance.
- No local concurrency-20 run: twenty copies would overcommit the 8-GiB machine. Local 429 denotes exhaustion of the simulator, not an assertion about the exact ALB error mapping.

## AWS decision and checks

Read-only AWS inventory at 14:13 UTC found account concurrency 10, unreserved 10 and no functions. Suraj reports requesting 1,000 through the console (the console refused smaller requests); approval is pending. Suraj now selects the existing ten slots in unreserved mode. The runner must verify only one function and exact quota ten before and during B, stop on drift/read failure and retain the incomplete result. A quota increase must not silently change a measured run.

Native release-image tests: 38 passed, including transaction/role isolation, queue timeout, stale/dead connection replacement, real verified TLS on both legs, insecure-client rejection and actual telemetry serialization. `native-release-final.log` holds the output. Original Terraform suite: 30 passed. Two new unreserved cases plus existing Lambda cases: 16 passed after correcting missing task-size mock inputs; original failed fixture log retained. Full Python regression: 2,494 passed, 186 skipped, one certificate-inventory failure (old test allowed only the three RDS roots). The corrected test separately pins the pool CA; the final affected suite passed 23 with three opt-in image skips. Full original log is retained; no clean full rerun is claimed. CI parity, boundaries, contracts, strict types, format (495 files) and Gitleaks source scan passed. No commit, image publication, merge, new pool deployment or pilot has been performed.
