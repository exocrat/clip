# Wanted-response integration notes

SE-02 is marked complete in the [work log](../status/work-log.md). This guide
records the original backend correction and its implementation boundaries; it is
not a pending plan or a claim about current cloud state.

## Contract and behavior

Search owns Wanted Request state and serializes response creation against request
closure. It uses the reviewed public Conversations operations, not private tables
or a shared database session. A live eligible regular caller may open or recover
the unique request/responder conversation; a closed request may only return an
existing pair. Missing/retired requests return safe not-found, self-response is
refused, and unavailable dependencies fail closed. Both successful create and
replay return the typed conversation result. The full contract is in
[Search](../../contracts/search.md) and the
[response-body correction](../decisions/wanted-response-contract-correction.md).

## Implementation map

The Search route/service own caller eligibility and request-state handling;
`wanted_response.py` and the PostgreSQL store provide the bounded origin lock and
state checks. Conversations owns thread creation, membership, and uniqueness.
No new migration or background scheduler is part of the response flow.

The original local verification covered open/closed retries, dependency failures,
row-lock ordering, malformed provider results and retired-request behavior. Those
results are historical; consult the work log for accepted task status and the
[experiment plan](../evaluation/deployment-20261103/plan.md) for any active live
verification gates. A task completion record does not authorize a new database or
cloud operation.
