# Connection budget for the functional repair

Current proposal: the [PgBouncer plan](pgbouncer-plan.md) supersedes the blocked
managed RDS Proxy plan. Both architectures use one transaction pool with backend
ceilings Identity8/Marketplace24/Conversations4, total36. The existing shared
role limits10/32/4 and instance limit78 remain unchanged. Client connections do
not each reserve a database backend. Verify actual use and drain old direct
clients during activation; especially avoid overlapping all four Conversations
backends with the old direct clients.

Both runtimes keep bounded client pools when routed through PgBouncer. Lambda
keeps at most one Identity, one Listing and one Hybrid client per environment;
checkout detects stale sockets, and PgBouncer expires idle clients after300s.
There are at most160 pool clients in total and36 database backends, even if AWS
freezes extra idle environments. Suraj now selects ten **unreserved** Lambda
slots for the first AWS pilot, after the actual regional quota was found to be
ten. Ten active Lambda environments plus both ECS tasks have a nominal client
maximum 60 (30 + 30). Old environments can temporarily add clients but cannot
bypass the global cap. Exhaustion fails visibly, without direct fallback.
Current authorization/expiry/revocation SQL is unchanged.

The requested quota increase is pending. Before and during each B workload,
verify the actual account and unreserved limits are exactly ten, our function
has no reservation, and no other function exists. Stop and invalidate the run
on drift or failed verification. A later approved quota increase requires a new
reviewed concurrency binding; it must not silently alter a measured run. This
change does not deploy or activate Lambda. Local checks used at most ten copies;
no local concurrency-20 result is claimed.

The following direct-mode analysis is retained for rollback. Its proposed
Identity20/Marketplace40 increases are **not needed or authorized by the current
pooled proposal**. Source credentials and restricted roles remain unchanged.

Observed RDS maximum:78, including3 superuser-reserved. Current shared role
limits are Identity10, Marketplace32 and Conversations4. These are shared by
all clients using each role, not per task. Resource sizes are unchanged.

| Consumer | Per ECS task | Both ECS tasks | Per active Lambda environment |
|---|---:|---:|---:|
| Identity sessions, capabilities, contacts, recipient lookup | 4 | 8 | 1 |
| Listings, Wanted and Saved pool | 6 | 12 | 1 |
| Hybrid retrieval pool | 2 | 4 | 1 |
| Embedding dispatcher | 1 | 2 | 0 |
| Conversations, including notification worker | 2 | 4 | 0 |
| Total configured maximum | 15 | 30 | 3 |

Identity leases wait at most1second with at most64 queued borrowers. Existing
async pool waits remain bounded, now with explicit finite waiting queues. Every
session/account check still queries current state; pooling caches no authorization.
The two-task normal configuration is the same for A and B.

In direct mode Lambda uses bounded null pools that close unused connections rather than retaining
them while AWS freezes an execution environment. Reserved concurrency alone is
not a reliable bound on the number of dormant environments; persistent minimum
connections would otherwise invalidate the budget. Lambda has no notification or
embedding worker and no Conversations pool. Startup safety-audit connections are
closed before serving; recheck transient rollout/initialization use in telemetry.

The preserved `6193ca7` Lambda change shares one physical Identity connection
between the session and account-eligibility transactions within one invocation.
It retains separate current-state SQL/transactions and restricted database roles.
Cleanup joins any outstanding borrower and physically closes the null-pool lease
before the terminal response body is sent. It does not retain connections across
invocations or cache authorization. That Identity connection may remain open while
application scoring runs; the separate Hybrid lease is released before scoring.
The conservative maxima below are unchanged. A normal Lambda Listing read now
opens two physical connections, rather than three; throughput remains measured,
not inferred from that count.

For A and a B smoke at concurrency2, these pools fit the current role limits:
Identity8+2=10, Marketplace18+4=22, Conversations4. This is a maximum of36app
connections, before operator/monitoring sessions. No live capacity result follows.

For a later B pilot at concurrency10, the conservative maxima would be
Identity18, Marketplace38 and Conversations4, total60. The current Identity10
and Marketplace32 caps cannot support that full configuration. Before that pilot,
prepare exact separate approval for Identity20 and Marketplace40 (or select a
smaller reviewed concurrency). Those role caps total64, leaving11nonreserved
connections beyond all application caps and3superuser-reserved. No role-limit
increase is executed by this document or the image rollout.

Before traffic, refresh actual max/reserved settings, role limits, all active
clients, image revisions and Lambda concurrency. Stop on connection rejection,
missing headroom, unexpected clients or any pilot stop condition. Monitor real
query/transaction duration and connection use. This budget is not proof of50rps.

The image-only rollout preserves existing ECS task/host counts and sizes. The
current service allows minimumHealthyPercent0 and maximumPercent100, with fixed
host port18000 and circuit-breaker rollback. Consequently a rollout can temporarily
interrupt serving; no NFR traffic may overlap it. Verify two healthy tasks and
their database connections before functional acceptance or measurements.

## Lunch search request path

The common search now encodes its query before borrowing the Hybrid pool, reads
fresh candidates/readiness and missing immutable vectors, returns that lease,
then scores/sorts in a bounded numerical worker. Scoring does not reopen a DB
connection. Normal session/account checks remain fresh for every request; the
session renewal transaction still locks/updates the session and preserves logout,
revocation and expiry. Saved/Photo browser batching reduces how many such API
requests Discover sends; direct S3 photo bodies do not use database connections.

The historical two-environment local B diagnostic exhausted its serial request-processing
margin at the required selected-read rate. Low-rate trace shows fresh null-pool
connection overhead, which is an intentional tradeoff against frozen Lambda
connections accumulating beyond the budget. The subsequent local check uses four
serial environments, while the AWS proposal at that time reserved ten. Its disposable
role caps are Identity20/Marketplace40/Conversations4, matching the proposed full
pilot budget; no live role or concurrency change follows from local success.
Database connection caps are upper bounds, not throughput or memory guarantees.
