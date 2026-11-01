"""Category-assisted discovery against the guarded disposable PostgreSQL target.

Coordinate vectors isolate SQL tiers; the existing actual-model test separately
checks real inference. Identity here is an explicit eligibility fixture, not
production authentication or cloud/NFR acceptance.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.contracts.domain_types import ListingQuery
from app.core.auth import CallerContext
from app.domains.listings.browse import ListingsBrowseService
from app.domains.listings.browse_store import browse_statement, read_browse_page
from app.domains.listings.hybrid_read import bind_query, read_hybrid_page
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.search.draft_matches import DraftMatchService
from app.domains.search.wanted_models import DraftTitle
from apps.api.tests.domains.listings.test_embedding_postgres import connect, target
from apps.api.tests.domains.listings.test_hybrid_read_postgres import (
    VECTOR,
    activate_math,
    live_listing,
    math_drain,
    parts,
)
from apps.api.tests.domains.search.test_draft_matches_postgres import Identity


def test_native_category_membership_updates_filters_ranking_and_drafts():
    """All writes roll back; only actual SQL supplies membership and ordering."""
    asyncio.run(exercise_category(target()))


async def exercise_category(value):
    """Prove category-only and cross-field matching without rebuilding embeddings."""
    async with await connect(value) as connection:
        async with connection.transaction(force_rollback=True):
            now = datetime.now(UTC)
            outputs = {}
            store, spec, _ = await activate_math(connection, outputs)
            ids = []
            fixtures = (
                ("FX3 quasardraftcategory", "crimson aluminium commuter", "bicycles"),
                ("RC120", "blue aluminium commuter", "bicycles"),
                ("Bicycle", "crimson steel frame", "other"),
                ("Plain object", "unlabelled object", "other"),
                ("Plain object", "unrelated object", "other"),
            )
            base = 1234500
            for index, (title, description, category) in enumerate(fixtures):
                listing = await live_listing(
                    connection,
                    995000 + index,
                    now,
                    title,
                    description,
                    price=base + index * 100,
                )
                await connection.execute(
                    "UPDATE listings.sale_listings SET category_id=(SELECT id FROM listings.categories WHERE code=%s) WHERE id=%s",
                    (category, listing),
                )
                ids.append(listing)
                outputs[listing] = parts(0.9, 0.9) if index == 3 else parts(-1.0, -1.0)
            for index, status in enumerate(
                ("unavailable", "future", "ended", "pending")
            ):
                await live_listing(
                    connection,
                    995010 + index,
                    now,
                    "FX3",
                    "crimson aluminium commuter",
                    price=base,
                    status=status,
                )
            await math_drain(store, spec, outputs)
            await store.set_state(spec, "serving")

            def request(text, **kwargs):
                """Isolate this fixture's price range from earlier committed test rows."""
                return ListingQuery(
                    q=text, min_price_paise=base, max_price_paise=base + 900, **kwargs
                )

            async def keyword(text, **kwargs):
                """Read the real compiler/store, selecting native rank only on request."""
                return await read_browse_page(
                    connection,
                    request(text, **kwargs),
                    now,
                    500000,
                    expanded_search=True,
                    keyword_relevance=kwargs.get("sort") == "relevance",
                )

            async def hybrid(text, **kwargs):
                """Read real hybrid SQL with bound coordinates to isolate lexical tiers."""
                return await read_hybrid_page(
                    connection,
                    request(text, **kwargs),
                    now,
                    500000,
                    bind_query(text, spec, VECTOR),
                    relevance=kwargs.get("sort") == "relevance",
                )

            for text in ("bicycle", "cycle", "bicyle", "vehicle"):
                page = await keyword(text)
                assert {row.listing_id for row in page.items} == set(ids[:3]), text
                assert not page.has_next
                combined = await hybrid(text, sort="relevance")
                assert {row.listing_id for row in combined.items[:3]} == set(
                    ids[:3]
                ), text
                assert combined.items[3].listing_id == ids[3]
                assert len(combined.items) == 4
            assert {
                row.listing_id for row in (await keyword("crimson bicycle")).items
            } == {ids[0], ids[2]}
            assert {row.listing_id for row in (await keyword("blue cycle")).items} == {
                ids[1]
            }
            assert (await keyword("bicycle quantumunseen")).items == ()
            assert (await keyword("the and of")).items == ()
            assert (await keyword("sports_fitness")).items == ()
            assert (await keyword("bicycle", category_code="books")).items == ()
            assert {
                row.listing_id
                for row in (await keyword("bicycle", category_code="bicycles")).items
            } == set(ids[:2])
            assert (await keyword("bicycle", negotiable=True)).items == ()
            assert (await keyword("bicycle", condition_code="fair")).items == ()
            for sort, expected in (
                ("price_asc", ids[:3]),
                ("price_desc", list(reversed(ids[:3]))),
                ("created_desc", sorted(ids[:3], reverse=True)),
            ):
                page = await keyword("bicycle", sort=sort)
                assert [row.listing_id for row in page.items] == expected
            # Both baseline and category branch match the literal Bicycle row;
            # it must occur once, with a stable relevance order across repeated reads.
            first = await keyword("bicycle", sort="relevance")
            assert len(first.items) == len({row.listing_id for row in first.items}) == 3
            assert first == await keyword("bicycle", sort="relevance")
            sql, parameters = browse_statement(request("bicycle"), now, 500000)
            await connection.execute("SET LOCAL enable_seqscan=off")
            try:
                plan = await (
                    await connection.execute("EXPLAIN (FORMAT JSON) " + sql, parameters)
                ).fetchone()
                assert "sale_full_text" in str(plan)
            finally:
                await connection.execute("SET LOCAL enable_seqscan=DEFAULT")

            # Exercise the actual shared provider and DraftMatchService. Only
            # eligibility is scripted; no text matcher or result page is faked.
            actor = (
                await (
                    await connection.execute(
                        "SELECT owner_id FROM listings.sale_listings WHERE id=%s",
                        (ids[0],),
                    )
                ).fetchone()
            )["owner_id"]
            identity = Identity(actor)

            @asynccontextmanager
            async def owned_connection():
                """Keep the public provider within this rollback-only native transaction."""
                yield connection

            provider = ListingsBrowseService(
                PostgresListingsStore(
                    SimpleNamespace(connection=owned_connection), 500000
                ),
                identity,
                clock=lambda: now,
            )
            draft = DraftMatchService(provider, identity)
            matched = await draft.match(
                CallerContext(actor, "regular", now + timedelta(minutes=5)),
                DraftTitle(draft_title="quasardraftcategory bicycle"),
            )
            assert [row.listing_id for row in matched.items] == [ids[0]]
            assert not matched.has_more

            async def generations():
                """Compare real generation identities/state, not just returned page text."""
                return await (
                    await connection.execute(
                        "SELECT listing_id,generation_id,source_fingerprint,state FROM listings.embedding_generations WHERE listing_id=ANY(%s) AND pipeline_id=%s ORDER BY listing_id",
                        (ids, spec.pipeline_id),
                    )
                ).fetchall()

            before = await generations()
            await connection.execute(
                "UPDATE listings.categories SET label='Road commuters' WHERE code='bicycles'"
            )
            assert {
                row.listing_id for row in (await keyword("road commuter")).items
            } == set(ids[:2])
            assert {row.listing_id for row in (await keyword("bicycle")).items} == {
                ids[2]
            }
            assert (await hybrid("bicycle", category_code="bicycles")).items == ()
            await connection.execute(
                "UPDATE listings.categories SET label='Bicycles' WHERE code='bicycles'"
            )
            await connection.execute(
                "UPDATE listings.sale_listings SET category_id=(SELECT id FROM listings.categories WHERE code='books') WHERE id=%s",
                (ids[0],),
            )
            assert {row.listing_id for row in (await keyword("bicycle")).items} == {
                ids[1],
                ids[2],
            }
            assert {row.listing_id for row in (await keyword("book")).items} == {ids[0]}
            assert [
                row.listing_id
                for row in (await hybrid("book", category_code="books")).items
            ] == [ids[0]]
            assert await generations() == before

            # Category-assisted matches span multiple pages without duplicate
            # IDs, even with identical sort timestamps and pending embeddings.
            paged_ids = []
            for index in range(23):
                paged_ids.append(
                    await live_listing(
                        connection,
                        995100 + index,
                        now,
                        "FX3",
                        "categorypagefixture",
                        price=base,
                    )
                )
            collected = []
            for number in (1, 2):
                page = await keyword(
                    "categorypagefixture bicycle", page=number, page_size=20
                )
                collected.extend(row.listing_id for row in page.items)
                assert page.has_next is (number == 1)
            assert collected == sorted(paged_ids, reverse=True)
            assert len(collected) == len(set(collected)) == 23
