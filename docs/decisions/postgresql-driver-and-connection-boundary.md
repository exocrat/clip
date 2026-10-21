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
release, distribution extras, and lockfile change remain a separate dependency
step; verify the package artifact and its LGPL-3.0-only license before adding
it to runtime dependencies.

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

- A future FastAPI lifespan implementation will create and close the
  process-level pool. The existing `/health` remains process liveness, not a
  database-readiness claim.
- Each domain's implementation owns its SQL, transaction, and connection
  acquisition. Cross-domain calls pass only typed contract arguments/results;
  a live connection, cursor, or transaction is never passed between domains.
- Conversations' generated declaration-only callables still need an approved
  runtime binding/injection pattern. Do not hand-edit generated `public.py`.
- No driver package, database setting, credential, pool, readiness endpoint,
  or database operation is added by this decision record.
- Before runtime implementation, choose and lock an exact stable package
  release/extras, review its license, add validated non-secret settings and
  secret delivery, size the pool against deployment connection capacity, and
  define separate readiness behavior and tests.

## Approver

Rahul (D), user direction recorded 2026-10-21: “use Psycopg 3”.

## Supersedes

None.
