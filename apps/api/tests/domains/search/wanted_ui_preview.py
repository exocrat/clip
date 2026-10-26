"""Opt-in, loopback-only SE-02 UI harness with real Search PostgreSQL writes.

Uses a newly owned cluster and synthetic session/catalogue/saved-state adapters.
Draft matching runs real Listings SQL. Conversations remain unavailable; no fake
conversation success, cloud, existing database target or provider is used.
"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from fastapi import FastAPI, Request  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from psycopg_pool import AsyncConnectionPool  # noqa: E402
import uvicorn  # noqa: E402

from app.contracts.domain_types import (  # noqa: E402
    Category,
    CategoryDisplay,
    ListingSummary,
    SavedListingState,
    SaveTargetResult,
    SessionView,
)
from app.core.auth import CallerContext, require_caller  # noqa: E402
from app.core.errors import ERRORS, error_response, install_error_handlers  # noqa: E402
from app.domains.listings.browse import ListingsBrowseService  # noqa: E402
from app.domains.listings.postgres_store import PostgresListingsStore  # noqa: E402
from app.domains.listings.routes import router as listing_router  # noqa: E402
from app.domains.search.draft_matches import DraftMatchService  # noqa: E402
from app.domains.search.saved import SavedService  # noqa: E402
from app.domains.search.saved_routes import (
    router as saved_router,
    saved_service,
)  # noqa: E402
from app.domains.search.saved_store import PostgresSavedStore  # noqa: E402
from app.domains.search.wanted import WantedService  # noqa: E402
from app.domains.search.wanted_models import WantedCreate  # noqa: E402
from app.domains.search.wanted_routes import (  # noqa: E402
    router as wanted_router,
    wanted_service,
    draft_match_service,
)
from app.domains.search.wanted_store import PostgresWantedStore  # noqa: E402
from apps.api.tests.domains.search.browser_preview import (
    require_preview_settings,
)  # noqa: E402
from apps.api.tests.domains.search.native_preview import NativeCluster  # noqa: E402
from apps.api.tests.domains.listings.test_hybrid_read_postgres import (
    live_listing,
)  # noqa: E402

ACTOR = UUID("62000000-0000-4000-8000-000000000001")
OTHER = UUID("62000000-0000-4000-8000-000000000002")


class PreviewDependencies:
    """Only fixed synthetic actors; catalogue display uses the real local store."""

    def __init__(self, store):
        self.store = store

    async def eligible(self, actor):
        """Reviewed Search eligibility signature, scoped to the two seeded users."""
        return actor in {ACTOR, OTHER}

    async def account_is_eligible(self, actor):
        """Reviewed Listings eligibility signature, never derived from a request."""
        return await self.eligible(actor)

    async def active_categories(self):
        """Project the local active catalogue into the reviewed code/label values."""
        return tuple(
            Category(code=x.code, label=x.label)
            for x in (await self.store.read_catalogue()).categories
        )

    async def category_display(self, codes):
        """Only fixture-used active categories need display in this isolated run."""
        catalogue = await self.active_categories()
        return tuple(
            CategoryDisplay(code=x.code, label=x.label, active=True)
            for x in catalogue
            if x.code in codes
        )


class PreviewSaved:
    """Explicit fixed Listings public snapshots; not acceptance of its real adapter."""

    def __init__(self, states):
        self.states = states

    async def read_save_target(self, caller, listing_id):
        """Only the fixture's available listing can acquire a new saved pair."""
        caller.require_current()
        state = self.states.get(listing_id)
        return SaveTargetResult(
            listing_id=listing_id,
            discoverable=bool(
                state and state.listing and state.listing.availability == "available"
            ),
        )

    async def read_saved_listing_summaries(self, caller, listing_ids):
        """Resolve only requested fixture IDs, retaining unavailable summaries."""
        caller.require_current()
        return tuple(self.states[x] for x in listing_ids if x in self.states)


def create_app(cluster):
    """Own cluster/pool lifecycle and mount real domain routers with explicit adapters."""

    @asynccontextmanager
    async def lifespan(app):
        pool = None
        try:
            await asyncio.to_thread(cluster.start)
            pool = AsyncConnectionPool(
                cluster.url,
                kwargs={"row_factory": dict_row},
                min_size=1,
                max_size=6,
                open=False,
            )
            await pool.open()
            await pool.wait(timeout=5)
            store = PostgresListingsStore(pool, 500000)
            dependencies = PreviewDependencies(store)
            expires = datetime.now(UTC) + timedelta(minutes=30)
            caller = CallerContext(ACTOR, "regular", expires)
            async with pool.connection() as connection:
                await connection.execute(
                    "INSERT INTO identity.users(id,account_class,status) VALUES(%s,'regular','active'),(%s,'regular','active')",
                    (ACTOR, OTHER),
                )
                listing_id = await live_listing(
                    connection,
                    96200,
                    datetime.now(UTC),
                    "Campus bicycle",
                    "A bicycle for campus trips",
                )
            wanted = WantedService(PostgresWantedStore(pool), dependencies)
            other = CallerContext(OTHER, "regular", expires)
            await wanted.create(
                other,
                WantedCreate(
                    title="Bicycle wanted",
                    description="Synthetic public request for campus travel.",
                    category_code="bicycles",
                    operation_id=uuid4(),
                ),
            )
            await wanted.create(
                caller,
                WantedCreate(
                    title="Books wanted",
                    description="Synthetic owner request; try edit and mark unavailable.",
                    category_code="books",
                    operation_id=uuid4(),
                ),
            )
            query = ListingsBrowseService(store, dependencies)
            from app.contracts.domain_types import AvailableListingQuery

            available = await query.query_available_listings(
                caller, AvailableListingQuery(page=1, page_size=20)
            )
            summary = next(x for x in available.items if x.listing_id == listing_id)
            async with pool.connection() as connection:
                # Reuse the immutable origin seed helper for a genuine unavailable FK target.
                from apps.api.tests.domains.listings.test_embedding_postgres import (
                    seed_listing,
                )

                unavailable_id = await seed_listing(connection, 96201)
            unavailable = ListingSummary.model_validate(
                {
                    **summary.model_dump(),
                    "listing_id": unavailable_id,
                    "title": "Unavailable synthetic bicycle",
                    "availability": "unavailable",
                }
            )
            snapshots = PreviewSaved(
                {
                    listing_id: SavedListingState(
                        listing_id=listing_id, listing=summary, retired=False
                    ),
                    unavailable_id: SavedListingState(
                        listing_id=unavailable_id, listing=unavailable, retired=False
                    ),
                }
            )
            saved_store = PostgresSavedStore(pool)
            # Seed only this newly owned cluster's two private references.
            async with pool.connection() as connection:
                await connection.execute(
                    "INSERT INTO search.saved_listings(user_id,listing_id) VALUES(%s,%s),(%s,%s)",
                    (ACTOR, listing_id, ACTOR, unavailable_id),
                )
            app.state.listings_store = store
            app.state.listings_identity = dependencies
            app.state.listings_browse_identity = dependencies
            app.state.wanted_store = wanted.store
            app.dependency_overrides[require_caller] = lambda: caller
            app.dependency_overrides[wanted_service] = lambda: wanted
            app.dependency_overrides[saved_service] = lambda: SavedService(
                saved_store, snapshots, dependencies
            )
            app.dependency_overrides[draft_match_service] = lambda: DraftMatchService(
                query, dependencies
            )
            app.state.preview_session = SessionView(
                user_id=ACTOR,
                account_class="regular",
                valid_until=expires,
                display_name="Synthetic Search author",
            )
            print(
                "SE-02 isolated preview ready: real Search SQL/draft query; synthetic Identity/saved snapshots; Conversations unavailable. 30-minute session.",
                flush=True,
            )
            yield
        finally:
            if pool is not None:
                await pool.close()
            await asyncio.to_thread(cluster.stop)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    install_error_handlers(app)
    from apps.api.tests.domains.identity.browser_csrf_fixtures import install_demo_csrf

    install_demo_csrf(app, "")
    app.include_router(listing_router)
    app.include_router(wanted_router)
    app.include_router(saved_router)

    @app.middleware("http")
    async def gate(request: Request, call_next):
        """Limit to loopback/same-origin; reads/writes expire together and never cache."""
        if (
            request.client is None
            or request.client.host not in {"127.0.0.1", "::1", "testclient"}
            or request.headers.get("origin") not in {None, "http://127.0.0.1:5173"}
            or request.headers.get("host")
            not in {"127.0.0.1:8000", "127.0.0.1:5173", "testserver"}
        ):
            return error_response(request, ERRORS[403])
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Clip-Preview"] = "search-wanted-native-synthetic-identity"
        return response

    @app.get("/me", response_model=SessionView)
    async def session():
        """Reviewed session projection only; no arbitrary actor/account selector."""
        return app.state.preview_session

    return app


def main():
    """Require explicit test-only activation; never accept connection/host arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated-wanted-ui", action="store_true", required=True)
    args = parser.parse_args()
    require_preview_settings(args.isolated_wanted_ui)
    cluster = NativeCluster()
    print(f"Owned cluster retained at {cluster.directory}", flush=True)
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(cluster), host="127.0.0.1", port=8000, access_log=False
        )
    )

    async def bounded_server():
        """Stop after30minutes or Ctrl+C; the application lifespan closes pool/cluster."""
        running = asyncio.create_task(server.serve())
        try:
            await asyncio.wait({running}, timeout=1800)
        finally:
            server.should_exit = True
            await running

    asyncio.run(bounded_server())


if __name__ == "__main__":
    main()
