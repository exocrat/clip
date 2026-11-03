# Connection budget for the functional repair

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

Lambda uses bounded null pools that close unused connections rather than retaining
them while AWS freezes an execution environment. Reserved concurrency alone is
not a reliable bound on the number of dormant environments; persistent minimum
connections would otherwise invalidate the budget. Lambda has no notification or
embedding worker and no Conversations pool. Startup safety-audit connections are
closed before serving; recheck transient rollout/initialization use in telemetry.

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
