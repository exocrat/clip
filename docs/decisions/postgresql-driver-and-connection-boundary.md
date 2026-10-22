# DEC-13 — PostgreSQL runtime driver and connection boundary

**Date:** 2026-10-21

**Origin:** CN-01 retirement API/database integration checkpoint, following
Step 3's contract and schema work. This is a named implementation checkpoint,
not a new numbered CN-01 requirement.

## Question

Which Python PostgreSQL driver and connection pattern should the API use for
the Conversations activity and retirement-marker operations?

## Options considered

- Psycopg 3 async API with its async connection pool and explicit SQL.
- asyncpg, with its asyncio-native PostgreSQL protocol client and pool.
- SQLAlchemy async, adding Core/ORM abstractions and an async driver.

## Selected choice

Use Psycopg 3's asynchronous API, `psycopg_pool.AsyncConnectionPool`, and
explicit parameterized SQL. No ORM is selected. The exact stable package
release and distribution choices are `psycopg[binary]==3.3.6` and the separately
versioned `psycopg-pool==3.3.3`. PyPI metadata identifies both releases as
stable, compatible with Python 3.14, and licensed `LGPL-3.0-only`; the bundled
`psycopg-binary==3.3.6` component has the same declared license. The lockfile
records the resolved artifacts and hashes. The binary extra is selected for a
self-contained client library across the supported local platforms; deployment
image/platform validation remains part of runtime implementation and CI.

## Rationale

The API is async FastAPI, and the PostgreSQL schema uses explicit SQL, row
locking, and trigger-enforced invariants. Psycopg provides native async
connections and a separately installable pool, fitting those needs without
introducing an ORM abstraction. The project supports Python 3.14 and PostgreSQL
18. See the [Psycopg async guide](https://www.psycopg.org/psycopg3/docs/advanced/async.html),
[Psycopg pool guide](https://www.psycopg.org/psycopg3/docs/advanced/pool.html),
and [FastAPI lifespan guidance](https://fastapi.tiangolo.com/advanced/events/)
for shared resource startup and shutdown.

## Implications

- FastAPI lifespan creates and closes an optional process-level pool only when
  `CLIP_DATABASE_DSN` is explicitly supplied. It starts with `min_size=0`,
  `max_size=1`, and `open(wait=False)`: startup makes no database connection.
  The bound is a conservative initial default pending deployment-capacity
  sizing. `/health` remains process liveness, not database readiness.
- Each domain's implementation owns its SQL, transaction, and connection
  acquisition. Cross-domain calls pass only typed contract arguments/results;
  a live connection, cursor, or transaction is never passed between domains.
- The generated `ConversationsPublic` protocol defines the typed injection
  surface; the provider implementation and application composition wiring remain
  future CN-01 work. Do not hand-edit generated `public.py`.
- The runtime dependencies are LGPL-3.0-only; retain their license notices and
  include the relevant license records with any distributed application image.
- `CLIP_DATABASE_DSN` is optional and validated with Psycopg's conninfo parser;
  Pydantic `SecretStr` masks it in representations. No actual DSN value is
  stored or documented.
- The selected SSM path, dedicated application database principal, ECS secret
  mapping, and execution-role permission remain pending; the existing PD-16
  master/probe credentials are not application credentials. No cloud resource
  or IAM policy is changed by this checkpoint.
- Reassess pool sizing against deployment connection capacity before enabling
  a deployed DB-backed service, and define separate readiness behavior then.

## Approver

Rahul (D), user direction recorded 2026-10-21: “use Psycopg 3”.

## Supersedes

None.
