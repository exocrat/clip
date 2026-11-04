# Requests traced for the lunch capacity batch

All measured requests use an established session. Microsoft/password login,
signup, OTP, password hashing and encryption-key setup happen before measurement.
The browser chat procedure still measures real submission through real display;
a successful server acknowledgement alone does not satisfy NFR-05.

Every API request first runs Identity's current session/account transaction. It
locks in account-before-session order, checks revocation/expiry and updates idle
time. Domain eligibility reads remain fresh. Pooling reuses connections; it does
not reuse an old authorization decision. Each lease is exclusive, and waits and
queues are bounded. A shared test session's row locks can serialize concurrent
requests, so connections are not the only possible limit.

| Operation | NFR-03 issued/s | Main burst issued/s | Subsequent work after session authentication |
|---|---:|---:|---|
| Browse Listing collection | 15 | 25 | Current eligibility; one Listings SQL page with filters/order/lookahead and image IDs; public response serialization. |
| Hybrid search | 12.5 | 15 | Current eligibility; query encoding/cache without a DB lease; one Hybrid transaction for expansion/current eligibility/coverage/candidates/missing vectors; return lease; bounded numerical scoring/sort/page and serialization. |
| Listing detail | 7.5 | 10 | Current eligibility; one authorized detail lookup and public response. |
| Wanted public page | 5 | 0 | Current eligibility; Search-owned page SQL; Listings-owned historical category labels; public page serialization. |
| Conversation list | 5 | 0 | Participant-scoped Conversations SQL, offers/unread/current profile join and summary serialization; message bodies are not loaded. |
| Saved list | 4.5 | 0 | Current eligibility; caller's saved references; bounded Listings summary lookup with its current authorization; ownership/retirement/result-shape validation. |
| Controlled Wanted create | 0.5 | 0 | CSRF/origin/session; eligibility/category validation; unique-operation transaction and receipt; reconcile all issued writes after timing. |

The dedicated NFR-01 profile sends20browse requests/s. NFR-02 sends10Hybrid
searches/s. All three profiles have60seconds warm-up,300seconds measurement,
no retries and the designed drain/deadline. A and B receive identical cases and
operation order. B only splits approved Listing GET collection/detail reads;
Wanted, Saved, Conversations and every write stay on ECS. Failed/throttled Lambda
requests are failures; there is no automatic ECS fallback.

## Work outside these API profiles

Discover now coalesces image links and Saved membership into bounded page batches.
A20-card page therefore does not need20separate photo-link session checks plus
per-card full Saved pagination. S3 image bodies are still separate browser loads;
they use neither an API database lease nor the numerical scorer. Their functional
success must be checked on the deployed rendered site. NFR-01 excludes photo-body
download time, and these API profiles do not simulate every browser photo download.

Two ECS processes retain their embedding and notification dispatchers. Their
configured connections are counted even when idle. The static required profiles
have no new Listing indexing job; Wanted writes do not edit the Listing corpus.
The local harness leaves dispatchers enabled and uses a real indexed dataset,
but does not invent mail events or contact real providers. New Listing readiness
and permitted worker publication have separate integration checks. Before live
traffic the proposed narrow worker grants must actually be approved/applied and
all required visible sources must be ready.

NFR-05 adds two actual browser clients, their normal polling and10background
read requests/s. Its actual display/message timing remains a deployed check.
NFR-06 uses two healthy ECS tasks and separately approved task loss, including
B's Lambda-read behavior. NFR-07 requires the exact isolated restore and integrity/
application-smoke procedure. NFR-08 records total project spending and delayed/
retained charges. Search arithmetic tests do not prove any of these outcomes.

## How capacity is interpreted

For a stage, average simultaneous work is issued rate multiplied by its average
holding/service time. The same equation applies separately to database leases,
serial Lambda environments and CPU-seconds. CPU, memory, queues, a shared-session
row lock, new connection setup, model cold work and the generator can each limit
capacity. More connections do not create more CPU.

Use observed CPU deltas and pool usage/queue counters across the measured window,
with raw HTTP latency/outcomes/accounting beside them. The local two-environment
B failure and four-environment100%Lambda high-CPU result are retained. They are
reasons to inspect the approved weight candidates, not to hide failures or assume
that a larger-memory database automatically adds CPU cores.

Local quotas do not recreate AWS processors, managed-RDS memory overhead, network,
TLS/ALB, storage, CPU credits or Lambda scaling/cold starts. Adding a fixed network
allowance to a local unloaded p95 cannot prove a loaded cloud p95. Any slower-CPU/
extra-latency calculation is a conditional sensitivity estimate. Final capacity,
routing, correctness, headroom and costs still require the bounded deployed pilot.
