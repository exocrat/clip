"""Transactional Search-owned wanted persistence; never joins upstream tables."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from psycopg import AsyncConnection, Error as DatabaseError
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import WantedRequestOwnerView
from app.core.errors import ERRORS, PublicError
from app.core.money import MAX_LISTING_PRICE_PAISE
from app.core.timestamps import as_utc
from app.domains.search.wanted_models import WantedDiscoveryPage, WantedPage, owner_view
from app.domains.search.wanted_retirement import PendingWantedRetirement
from app.domains.search.wanted_response import WantedResponseOrigin

LabelResolver = Callable[[str, bool], Awaitable[str]]
Kind = Literal["create", "edit", "state"]
_MAX_BUDGET_PAISE = MAX_LISTING_PRICE_PAISE
_COLUMNS = "id,author_id,title,description,category_code,budget_paise,status,created_at,updated_at,revision,retired_at,retirement_pending_operation_id"
_PATCH_FIELDS = ("title", "description", "category_code", "budget_paise")


class PostgresWantedStore:
    """Use an injected existing pool; each write and receipt commit atomically."""

    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]]):
        """Own no new pool or credentials; composition owns lifecycle/target."""
        self.pool = pool

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncConnection[dict[str, Any]]]:
        """Bound SQL/lock waits and map database failures to fixed safe503."""
        try:
            async with self.pool.connection(timeout=5) as connection:
                async with connection.transaction():
                    await connection.execute("SET LOCAL statement_timeout='5s'")
                    await connection.execute("SET LOCAL lock_timeout='1s'")
                    yield connection
        except DatabaseError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None

    async def listing(
        self, owner: UUID | None, page: WantedPage | WantedDiscoveryPage
    ) -> tuple[list[dict[str, Any]], bool]:
        """Filter visibility/ownership before stable ordering and limit+one."""
        predicate = (
            "status='open' AND retirement_pending_operation_id IS NULL"
            if owner is None
            else "author_id=%s"
        )
        params: list[object] = [] if owner is None else [owner]
        if owner is None and isinstance(page, WantedDiscoveryPage):
            if page.q is not None:
                statement_filter = (
                    " AND to_tsvector('pg_catalog.english', "
                    "coalesce(title, '') || ' ' || coalesce(description, '')) "
                    "@@ plainto_tsquery('pg_catalog.english', %s)"
                )
                params.append(page.q)
            else:
                statement_filter = ""
            if page.category_code:
                statement_filter += " AND category_code = ANY(%s)"
                params.append(page.category_code)
            if page.min_budget_paise is not None or page.max_budget_paise is not None:
                statement_filter += " AND budget_paise IS NOT NULL"
            if page.min_budget_paise is not None:
                if page.min_budget_paise > _MAX_BUDGET_PAISE:
                    statement_filter += " AND FALSE"
                else:
                    statement_filter += " AND budget_paise >= %s"
                    params.append(page.min_budget_paise)
            if (
                page.max_budget_paise is not None
                and page.max_budget_paise < _MAX_BUDGET_PAISE
            ):
                statement_filter += " AND budget_paise <= %s"
                params.append(page.max_budget_paise)
        else:
            statement_filter = ""
        async with self.connection() as connection:
            rows = await (
                await connection.execute(
                    "SELECT "
                    + _COLUMNS
                    + " FROM search.wanted_requests WHERE retired_at IS NULL AND "
                    + predicate
                    + statement_filter
                    + " ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s",
                    (*params, page.page_size + 1, (page.page - 1) * page.page_size),
                )
            ).fetchall()
        return rows[: page.page_size], len(rows) > page.page_size

    async def read(self, identifier: UUID, actor: UUID) -> dict[str, Any]:
        """Hide unavailable/pending rows from nonowners and retired rows from all."""
        async with self.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT "
                    + _COLUMNS
                    + " FROM search.wanted_requests WHERE id=%s AND retired_at IS NULL "
                    "AND (author_id=%s OR (status='open' AND retirement_pending_operation_id IS NULL))",
                    (identifier, actor),
                )
            ).fetchone()
        if row is None:
            raise PublicError(ERRORS[404])
        return row

    async def write(
        self,
        actor: UUID,
        kind: Kind,
        operation: UUID,
        target: UUID | None,
        payload: dict[str, Any],
        resolve_label: LabelResolver,
    ) -> WantedRequestOwnerView:
        """Serialize retries and row revisions, preserving the original response.

        Create keys are actor/operation; edit/state keys add target and kind.
        The callback receives only code/assignment intent, never a DB session.
        Public catalogue calls are separately deadline-bounded by the service.
        No automatic write retry follows an ambiguous commit; the same key can
        be resubmitted safely. Retirement/pending checks precede receipt replay.
        """
        scope = actor if kind == "create" else target
        assert scope is not None
        async with self.connection() as connection:
            await connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,17))",
                (f"{actor}/{scope}/{kind}/{operation}",),
            )
            receipt = await (
                await connection.execute(
                    "SELECT request_id,request_payload,result_payload FROM search.wanted_command_results "
                    "WHERE author_id=%s AND scope_id=%s AND command_kind=%s AND operation_id=%s",
                    (actor, scope, kind, operation),
                )
            ).fetchone()
            identifier = receipt["request_id"] if receipt else target
            row = None
            if identifier is not None:
                row = await (
                    await connection.execute(
                        "SELECT "
                        + _COLUMNS
                        + " FROM search.wanted_requests WHERE id=%s FOR UPDATE",
                        (identifier,),
                    )
                ).fetchone()
                if row is None or row["author_id"] != actor:
                    raise PublicError(ERRORS[404])
                if (
                    row["retired_at"] is not None
                    or row["retirement_pending_operation_id"] is not None
                ):
                    raise PublicError(ERRORS[409])
            if receipt:
                if (
                    receipt["request_payload"] != payload
                    or receipt["result_payload"] is None
                ):
                    raise PublicError(ERRORS[409])
                return WantedRequestOwnerView.model_validate(receipt["result_payload"])
            if kind == "create":
                label = await resolve_label(payload["category_code"], True)
                row = await (
                    await connection.execute(
                        "INSERT INTO search.wanted_requests(id,author_id,title,description,category_code,budget_paise,status) "
                        "VALUES(%s,%s,%s,%s,%s,%s,'open') RETURNING " + _COLUMNS,
                        (
                            uuid4(),
                            actor,
                            payload["title"],
                            payload["description"],
                            payload["category_code"],
                            payload["budget_paise"],
                        ),
                    )
                ).fetchone()
            else:
                assert row is not None
                if payload["expected_revision"] != row["revision"]:
                    raise PublicError(ERRORS[409])
                fields = (
                    {name: payload[name] for name in _PATCH_FIELDS if name in payload}
                    if kind == "edit"
                    else (
                        {"status": payload["state"]}
                        if row["status"] != payload["state"]
                        else {}
                    )
                )
                code = fields.get("category_code", row["category_code"])
                label = await resolve_label(code, "category_code" in fields)
                if fields:
                    # Column names come exclusively from the code-owned allowlist.
                    assignments = ",".join(name + "=%s" for name in fields)
                    row = await (
                        await connection.execute(
                            "UPDATE search.wanted_requests SET "
                            + assignments
                            + ",revision=revision+1,updated_at=clock_timestamp() WHERE id=%s RETURNING "
                            + _COLUMNS,
                            (*fields.values(), identifier),
                        )
                    ).fetchone()
            assert row is not None
            result = owner_view(row, label)
            await connection.execute(
                "INSERT INTO search.wanted_command_results(author_id,scope_id,command_kind,operation_id,request_id,request_payload,result_payload) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    actor,
                    scope,
                    kind,
                    operation,
                    row["id"],
                    Jsonb(payload),
                    Jsonb(result.model_dump(mode="json")),
                ),
            )
            return result

    async def begin_retirement(
        self, identifier: UUID, now: datetime
    ) -> PendingWantedRetirement | None:
        """Commit a server-generated pair after locking/rechecking local eligibility.

        closed_at is continuous unavailability. A resumed attempt keeps its exact
        ID/cutoff; no content or user-visible revision changes during this stage.
        """
        now = as_utc(now)
        async with self.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT status,closed_at,retired_at,retirement_pending_operation_id,retirement_pending_cutoff_utc "
                    "FROM search.wanted_requests WHERE id=%s FOR UPDATE",
                    (identifier,),
                )
            ).fetchone()
            if (
                row is None
                or row["retired_at"] is not None
                or row["status"] != "unavailable"
                or row["closed_at"] is None
                or row["closed_at"] > now - timedelta(days=180)
            ):
                return None
            if row["retirement_pending_operation_id"] is not None:
                return PendingWantedRetirement(
                    row["retirement_pending_operation_id"],
                    row["retirement_pending_cutoff_utc"],
                )
            pending = PendingWantedRetirement(uuid4(), now - timedelta(days=90))
            await connection.execute(
                "UPDATE search.wanted_requests SET retirement_pending_operation_id=%s,retirement_pending_cutoff_utc=%s WHERE id=%s",
                (pending.operation_id, pending.cutoff_utc, identifier),
            )
            return pending

    async def clear_retirement(
        self, identifier: UUID, pending: PendingWantedRetirement
    ) -> None:
        """Fence both fields so an older blocked attempt cannot clear a newer one."""
        async with self.connection() as connection:
            cursor = await connection.execute(
                "UPDATE search.wanted_requests SET retirement_pending_operation_id=NULL,retirement_pending_cutoff_utc=NULL "
                "WHERE id=%s AND retired_at IS NULL AND retirement_pending_operation_id=%s AND retirement_pending_cutoff_utc=%s",
                (identifier, pending.operation_id, pending.cutoff_utc),
            )
            if cursor.rowcount != 1:
                raise PublicError(ERRORS[409])

    async def finalize_retirement(
        self, identifier: UUID, pending: PendingWantedRetirement, now: datetime
    ) -> None:
        """Scrub receipt copies first, then origin in one fenced local transaction.

        Retain UUID/key/lifecycle references. A failed origin update rolls back
        receipt clearing too, leaving the previously committed pending pair for
        identical Conversations replay. No other domain or object is deleted.
        """
        now = as_utc(now)
        async with self.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT status,closed_at,retired_at,retirement_pending_operation_id,retirement_pending_cutoff_utc "
                    "FROM search.wanted_requests WHERE id=%s FOR UPDATE",
                    (identifier,),
                )
            ).fetchone()
            if row is None:
                raise PublicError(ERRORS[404])
            if row["retired_at"] is not None:
                return
            if (
                pending.cutoff_utc > now - timedelta(days=90)
                or row["retirement_pending_operation_id"] != pending.operation_id
                or row["retirement_pending_cutoff_utc"] != pending.cutoff_utc
                or row["status"] != "unavailable"
                or row["closed_at"] is None
                or row["closed_at"] > now - timedelta(days=180)
            ):
                raise PublicError(ERRORS[409])
            await connection.execute(
                "UPDATE search.wanted_command_results SET request_payload=NULL,result_payload=NULL WHERE request_id=%s AND request_payload IS NOT NULL",
                (identifier,),
            )
            await connection.execute(
                "UPDATE search.wanted_requests SET title=NULL,description=NULL,category_code=NULL,budget_paise=NULL,status='unavailable',"
                "retired_at=%s,updated_at=%s,revision=revision+1,retirement_pending_operation_id=NULL,retirement_pending_cutoff_utc=NULL WHERE id=%s",
                (now, now, identifier),
            )

    @asynccontextmanager
    async def response_guard(
        self, identifier: UUID
    ) -> AsyncIterator[WantedResponseOrigin | None]:
        """Hold a non-key-changing origin lock through the bounded public call.

        NO KEY UPDATE blocks owner state changes/retirement, while a separate
        Conversations transaction can take the FK key-share lock to insert its
        thread. FOR UPDATE would block that FK check while awaiting its commit.
        The database session remains Search-owned and is never passed upstream.
        """
        async with self.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT author_id,status,retired_at,retirement_pending_operation_id FROM search.wanted_requests WHERE id=%s FOR NO KEY UPDATE",
                    (identifier,),
                )
            ).fetchone()
            yield (
                None
                if row is None
                else WantedResponseOrigin(
                    author_id=row["author_id"],
                    state=row["status"],
                    retired=row["retired_at"] is not None,
                    pending=row["retirement_pending_operation_id"] is not None,
                )
            )
