"""Real PostgreSQL browse pagination/visibility check for the disposable runner.

No in-memory query implementation is used. Without the runner-provided local
database this is skipped explicitly, leaving Step 3 SQL acceptance pending.
Fixture writes live in a force-rollback transaction and never reset a database.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from contextlib import asynccontextmanager
from types import SimpleNamespace
import os
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import dict_row
import pytest

from app.contracts.domain_types import ListingQuery
from app.core.errors import PublicError
from app.domains.listings.browse_store import read_browse_page
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.lexical_expansion import compile_expansion
from data.generators.preview import stable_id


def test_postgres_browse_visibility_and_stable_pages():
    """Run only against the runner's pinned migrated Unix-socket test database."""
    conninfo = os.environ.get("LISTINGS_TEST_DATABASE_URL")
    if not conninfo:
        pytest.skip(
            "Run scripts/check_database.py --listings-store for real PostgreSQL"
        )
    asyncio.run(exercise_browse(conninfo))


async def exercise_browse(conninfo: str) -> None:
    """Verify complete pages and boundaries in one fixed, rollback-only SQL state."""
    async with await AsyncConnection.connect(
        conninfo, row_factory=dict_row, autocommit=True
    ) as connection:
        target = await (
            await connection.execute(
                "SELECT current_database() AS name, inet_server_addr() IS NULL AS local_socket"
            )
        ).fetchone()
        assert target == {"name": "clip_test_ci", "local_socket": True}
        async with connection.transaction(force_rollback=True):
            await connection.execute("SET LOCAL statement_timeout = '30s'")
            await connection.execute("SET LOCAL lock_timeout = '5s'")
            await connection.execute(
                "LOCK TABLE listings.sale_listings IN SHARE ROW EXCLUSIVE MODE"
            )
            now = datetime.now(UTC)
            owner_id = UUID(stable_id(81001, "user_placeholder", 1))
            await connection.execute(
                "INSERT INTO identity.users (id, account_class, status, display_name) VALUES (%s,'regular','active','Synthetic browse owner')",
                (owner_id,),
            )
            category = await (
                await connection.execute(
                    "SELECT id FROM listings.categories WHERE code='bicycles'"
                )
            ).fetchone()
            assert category is not None
            visible, hidden = set(), set()
            for index in range(70):
                # Versioned test-only UUIDs make the same fixture reproducible;
                # the outer transaction always rolls back these reserved rows.
                listing_id = UUID(stable_id(81001, "listing_placeholder", index + 1))
                upload_id = UUID(stable_id(81002, "listing_placeholder", index + 1))
                start, end = now, None
                availability = "available"
                pending = None
                created_at = now - timedelta(days=3)
                if index == 65:
                    start = now + timedelta(seconds=1)
                elif index == 66:
                    start, end = now - timedelta(days=2), now
                elif index == 67:
                    availability = "unavailable"
                elif index == 68:
                    pending = UUID(stable_id(81003, "listing_placeholder", index + 1))
                elif index == 69:
                    start, end = now - timedelta(days=200), now - timedelta(days=190)
                    created_at = start
                    availability = "unavailable"
                (visible if index < 65 else hidden).add(listing_id)
                await connection.execute(
                    """INSERT INTO listings.sale_listings
                    (id,owner_id,title,description,category_id,condition_code,asking_price_paise,
                     negotiable,pickup_area,availability,available_from,available_until,created_at,updated_at,
                     retirement_pending_operation_id,retirement_pending_cutoff_utc)
                    VALUES (%s,%s,'Synthetic browse bicycle','Controlled browse fixture',%s,'good',0,false,NULL,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        listing_id,
                        owner_id,
                        category["id"],
                        availability,
                        start,
                        end,
                        created_at,
                        created_at,
                        pending,
                        now if pending else None,
                    ),
                )
                key = f"synthetic-browse/{upload_id}"
                await connection.execute(
                    """INSERT INTO listings.image_uploads
                    (id,owner_id,operation_id,object_key,state,created_at,expires_at,confirmed_at,
                     requested_media_type,requested_size_bytes,confirmed_media_type,confirmed_size_bytes)
                    VALUES (%s,%s,%s,%s,'confirmed',%s,%s,%s,'image/png',1,'image/png',1)""",
                    (
                        upload_id,
                        owner_id,
                        upload_id,
                        key,
                        now,
                        now + timedelta(days=1),
                        now,
                    ),
                )
                await connection.execute(
                    """INSERT INTO listings.images
                    (id,listing_id,upload_id,object_key,position,media_type,size_bytes)
                    VALUES (%s,%s,%s,%s,0,'image/png',1)""",
                    (upload_id, listing_id, upload_id, key),
                )
                if index == 69:
                    # Controlled old fixture: retain no content on the retired row.
                    # No thread/activity/storage side effect exists in this fixture.
                    await connection.execute(
                        "UPDATE listings.images SET retired_at=%s WHERE listing_id=%s",
                        (now, listing_id),
                    )
                    await connection.execute(
                        """UPDATE listings.sale_listings SET retired_at=%s,
                        title=NULL,description=NULL,category_id=NULL,condition_code=NULL,
                        asking_price_paise=NULL,negotiable=NULL,pickup_area=NULL,proof_available=NULL
                        WHERE id=%s""",
                        (now, listing_id),
                    )
            await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            # Independently inspect raw state, then derive visibility/order in
            # Python. This includes any rows from preceding adapter tests, so
            # the check does not depend on test order or erase their fixtures.
            rows: list[dict[str, Any]] = await (
                await connection.execute("""SELECT id,created_at,
                availability,available_from,available_until,retired_at,retirement_pending_operation_id
                FROM listings.sale_listings""")
            ).fetchall()
            expected = sorted(
                (
                    row
                    for row in rows
                    if row["retired_at"] is None
                    and row["retirement_pending_operation_id"] is None
                    and row["availability"] == "available"
                    and row["available_from"] <= now
                    and (row["available_until"] is None or now < row["available_until"])
                ),
                key=lambda row: (row["created_at"], row["id"]),
                reverse=True,
            )
            expected_ids = [row["id"] for row in expected]
            assert visible.issubset(expected_ids)
            assert not hidden.intersection(expected_ids)
            for size in (20, 50, 100):
                actual = []
                for number in range(1, len(expected_ids) // size + 2):
                    page = await read_browse_page(
                        connection,
                        ListingQuery(page=number, page_size=size),
                        now,
                        500000,
                    )
                    actual.extend(row.listing_id for row in page.items)
                    assert page.has_next is (number * size < len(expected_ids))
                assert actual == expected_ids
                assert len(actual) == len(set(actual))
            empty = await read_browse_page(
                connection, ListingQuery(page=len(expected_ids) + 1), now, 500000
            )
            assert empty.items == () and not empty.has_next
            await exercise_native_text(connection, now, visible, hidden)
            await exercise_filters_and_sorts(connection, now, visible)
            await exercise_visibility_transitions(connection, now, visible)
            # Expansion owns the final fixture mutations; earlier matrices use
            # the original se01native marker and independent filter values.
            await exercise_expanded_text(connection, now, visible, hidden)
            # Private keyword rank owns the last fixture mutations. Every older
            # recency/price/expansion matrix is verified first.
            await exercise_keyword_relevance(connection, now, visible, hidden)

            # Public adapter over this exact native connection: no fake ranking.
            # The fixture transaction remains rollback-only and no helper exists.
            @asynccontextmanager
            async def owned_connection():
                yield connection

            store = PostgresListingsStore(
                SimpleNamespace(connection=owned_connection), 500000
            )
            for mode in ("keyword", "hybrid"):
                for size in (20, 50, 100):
                    blank = ListingQuery(search_mode=mode, page_size=size)
                    assert await store.browse_available_listings(
                        blank, now
                    ) == await read_browse_page(
                        connection, blank, now, 500000, expanded_search=True
                    )
            for sort in ("created_desc", "price_asc", "price_desc", "relevance"):
                query = ListingQuery(q="vehicle", sort=sort)
                assert await store.browse_available_listings(
                    query, now
                ) == await read_browse_page(
                    connection,
                    query,
                    now,
                    500000,
                    expanded_search=True,
                    keyword_relevance=sort == "relevance",
                )


async def exercise_native_text(
    connection: AsyncConnection[dict[str, Any]],
    now: datetime,
    visible: set[UUID],
    hidden: set[UUID],
) -> None:
    """Use real generated vectors/GIN for title, description and plain-text checks.

    This runs inside the caller's rollback-only fixture transaction. Index
    eligibility uses a local planner diagnostic, not a latency/performance claim.
    No Python implementation of stemming, text matching or ranking is used.
    """
    before = await read_browse_page(
        connection, ListingQuery(q="se01native"), now, 500000
    )
    assert before.items == ()
    await connection.execute(
        """UPDATE listings.sale_listings SET
        title='Synthetic se01native fixture', description='Controlled se01native content'
        WHERE id=ANY(%s) AND retired_at IS NULL""",
        (list(visible | hidden),),
    )
    ids = sorted(visible, reverse=True)
    changes = (
        (
            ids[0],
            "Synthetic se01native quasar telescope",
            "Controlled optical instrument",
        ),
        (ids[1], "Synthetic se01native instrument", "Quasar telescope with lens"),
        (ids[2], "Synthetic se01native quasar", "No second matching term"),
        (ids[3], "Synthetic se01native running shoes", "Controlled trainer fixture"),
        (ids[4], "Synthetic se01native quasar", "Telescope lens"),
    )
    for listing_id, title, description in changes:
        await connection.execute(
            "UPDATE listings.sale_listings SET title=%s,description=%s WHERE id=%s",
            (title, description, listing_id),
        )
    # Deliberately match hidden rows too; availability must still exclude them.
    await connection.execute(
        """UPDATE listings.sale_listings SET
        title='Synthetic se01native quasar telescope' WHERE id=ANY(%s) AND retired_at IS NULL""",
        (list(hidden),),
    )
    expected_matches = {ids[0], ids[1], ids[4]}
    page = await read_browse_page(
        connection, ListingQuery(q="se01native quasar telescope"), now, 500000
    )
    assert [row.listing_id for row in page.items] == sorted(
        expected_matches, reverse=True
    )
    assert not page.has_next
    stemmed = await read_browse_page(
        connection, ListingQuery(q="se01native runs"), now, 500000
    )
    assert [row.listing_id for row in stemmed.items] == [ids[3]]
    plain = await read_browse_page(
        connection, ListingQuery(q="se01native | quasar"), now, 500000
    )
    assert {row.listing_id for row in plain.items} == {ids[0], ids[1], ids[2], ids[4]}
    for text in ("the and or", "!!!", "se01native nonexistentterm"):
        empty = await read_browse_page(connection, ListingQuery(q=text), now, 500000)
        assert empty.items == () and not empty.has_next
    for size in (20, 50, 100):
        actual = []
        for number in range(1, len(ids) // size + 2):
            page = await read_browse_page(
                connection,
                ListingQuery(page=number, page_size=size, q="se01native"),
                now,
                500000,
            )
            actual.extend(row.listing_id for row in page.items)
            assert page.has_next is (number * size < len(ids))
        assert actual == ids

    vector = await (
        await connection.execute(
            """SELECT attr.attgenerated,
        pg_get_expr(def.adbin,def.adrelid) AS expression
        FROM pg_attribute AS attr JOIN pg_attrdef AS def
          ON def.adrelid=attr.attrelid AND def.adnum=attr.attnum
        WHERE attr.attrelid='listings.sale_listings'::regclass AND attr.attname='search_vector'"""
        )
    ).fetchone()
    assert vector is not None and vector["attgenerated"] == "s"
    assert all(
        term in vector["expression"] for term in ("english", "title", "description")
    )
    index = await (
        await connection.execute(
            """SELECT idx.indisvalid,idx.indisready,am.amname,
        pg_get_indexdef(idx.indexrelid) AS definition
        FROM pg_index AS idx JOIN pg_class AS rel ON rel.oid=idx.indexrelid
        JOIN pg_am AS am ON am.oid=rel.relam
        WHERE idx.indrelid='listings.sale_listings'::regclass AND rel.relname='sale_full_text'"""
        )
    ).fetchone()
    assert index is not None and index["indisvalid"] and index["indisready"]
    assert index["amname"] == "gin" and "search_vector" in index["definition"]
    await connection.execute("SET LOCAL enable_seqscan=off")
    try:
        plan = await (
            await connection.execute(
                """EXPLAIN (FORMAT JSON)
            SELECT id FROM listings.sale_listings
            WHERE search_vector @@ plainto_tsquery('pg_catalog.english',%s)""",
                ("se01native quasar telescope",),
            )
        ).fetchone()
        assert plan is not None
        assert "sale_full_text" in used_indexes(plan["QUERY PLAN"][0]["Plan"])
    finally:
        await connection.execute("SET LOCAL enable_seqscan=DEFAULT")


def used_indexes(plan: dict[str, Any]) -> set[str]:
    """Extract actual index-scan names from PostgreSQL's JSON plan tree."""
    names = {plan["Index Name"]} if "Index Name" in plan else set()
    for child in plan.get("Plans", []):
        names.update(used_indexes(child))
    return names


async def exercise_filters_and_sorts(
    connection: AsyncConnection[dict[str, Any]], now: datetime, visible: set[UUID]
) -> None:
    """Compare real filtered SQL pages with independently specified fixture results.

    All mutations are inside the parent's rollback transaction. Python only
    derives test expectations; it never services a query or replaces PostgreSQL.
    """
    catalogue = await (
        await connection.execute("SELECT code,id FROM listings.categories WHERE active")
    ).fetchall()
    categories = {row["code"]: row["id"] for row in catalogue}
    fixtures = []
    for index, listing_id in enumerate(sorted(visible, reverse=True)):
        category = "books" if (index // 8) % 2 else "bicycles"
        condition = ("new", "like_new", "good", "fair")[(index // 2) % 4]
        price = (index // 2) * 100
        negotiable = bool((index // 16) % 2)
        await connection.execute(
            """UPDATE listings.sale_listings SET category_id=%s,
            condition_code=%s,asking_price_paise=%s,negotiable=%s WHERE id=%s""",
            (categories[category], condition, price, negotiable, listing_id),
        )
        fixtures.append(
            dict(
                id=listing_id,
                category=category,
                condition=condition,
                price=price,
                negotiable=negotiable,
            )
        )
    cases = [
        ({}, lambda row: True),
        ({"category_code": "books"}, lambda row: row["category"] == "books"),
        ({"category_code": "other"}, lambda row: False),
        ({"condition_code": "good"}, lambda row: row["condition"] == "good"),
        ({"min_price_paise": 0, "max_price_paise": 0}, lambda row: row["price"] == 0),
        (
            {"min_price_paise": 100, "max_price_paise": 300},
            lambda row: 100 <= row["price"] <= 300,
        ),
        ({"negotiable": False}, lambda row: row["negotiable"] is False),
        ({"negotiable": True}, lambda row: row["negotiable"] is True),
        (
            {
                "category_code": "books",
                "condition_code": "good",
                "min_price_paise": 0,
                "max_price_paise": 3000,
                "negotiable": False,
            },
            lambda row: row["category"] == "books"
            and row["condition"] == "good"
            and row["price"] <= 3000
            and row["negotiable"] is False,
        ),
        ({"max_price_paise": 10**100}, lambda row: True),
        ({"min_price_paise": 10**100}, lambda row: False),
    ]
    for filters, accept in cases:
        selected = [row for row in fixtures if accept(row)]
        for sort in ("created_desc", "price_asc", "price_desc"):
            expected = sorted(
                selected,
                key=(
                    (lambda row: row["id"])
                    if sort == "created_desc"
                    else (lambda row: (row["price"], row["id"]))
                ),
                reverse=sort != "price_asc",
            )
            expected_ids = [row["id"] for row in expected]
            for size in (20, 50, 100):
                actual = []
                for number in range(1, len(expected_ids) // size + 2):
                    query = ListingQuery(
                        q="se01native",
                        sort=sort,
                        page=number,
                        page_size=size,
                        **filters,
                    )
                    result = await read_browse_page(connection, query, now, 500000)
                    actual.extend(row.listing_id for row in result.items)
                    assert result.has_next is (number * size < len(expected_ids))
                assert actual == expected_ids
                assert len(actual) == len(set(actual))
    for filters in (
        {"category_code": "synthetic-missing"},
        {"condition_code": "synthetic-missing"},
    ):
        with pytest.raises(PublicError) as failure:
            await read_browse_page(connection, ListingQuery(**filters), now, 500000)
        assert failure.value.spec.status == 422
    # Active flags must be read at request time. Roll back these temporary
    # catalogue changes with the same fixture transaction after testing.
    for table, code, field in (
        ("categories", "books", "category_code"),
        ("conditions", "fair", "condition_code"),
    ):
        # table names are fixed test-owned literals, never request input.
        await connection.execute(
            f"UPDATE listings.{table} SET active=false WHERE code=%s", (code,)
        )
        with pytest.raises(PublicError) as failure:
            await read_browse_page(
                connection, ListingQuery(**{field: code}), now, 500000
            )
        assert failure.value.spec.status == 422
        await connection.execute(
            f"UPDATE listings.{table} SET active=true WHERE code=%s", (code,)
        )


async def exercise_visibility_transitions(
    connection: AsyncConnection[dict[str, Any]], now: datetime, visible: set[UUID]
) -> None:
    """Re-read one real listing across availability and clock-boundary transitions.

    No saved provider/API is substituted here. Mutations affect only the native
    test's synthetic rows inside its force-rollback transaction. The separate
    SE-02 saved-reference/read/privacy integration remains pending.
    """
    listing_id = sorted(visible)[0]

    async def present(moment: datetime, text: str | None) -> bool:
        """Read fresh SQL pages; do not reuse an earlier membership/summary result."""
        for number in range(1, 51):
            result = await read_browse_page(
                connection,
                ListingQuery(q=text, page=number, page_size=100),
                moment,
                500000,
            )
            if any(row.listing_id == listing_id for row in result.items):
                return True
            if not result.has_next:
                return False
        raise AssertionError(
            "Disposable visibility fixture exceeded its test row bound"
        )

    for text in (None, "se01native"):
        assert await present(now, text)
    await connection.execute(
        "UPDATE listings.sale_listings SET availability='unavailable' WHERE id=%s",
        (listing_id,),
    )
    for text in (None, "se01native"):
        assert not await present(now, text)
    await connection.execute(
        "UPDATE listings.sale_listings SET availability='available' WHERE id=%s",
        (listing_id,),
    )
    for text in (None, "se01native"):
        assert await present(now, text)
    await connection.execute(
        "UPDATE listings.sale_listings SET available_from=%s,available_until=%s WHERE id=%s",
        (now - timedelta(days=2), now, listing_id),
    )
    for text in (None, "se01native"):
        assert not await present(now, text)
    raw = await (
        await connection.execute(
            "SELECT availability FROM listings.sale_listings WHERE id=%s", (listing_id,)
        )
    ).fetchone()
    assert raw is not None and raw["availability"] == "available"
    await connection.execute(
        "UPDATE listings.sale_listings SET available_from=%s,available_until=NULL WHERE id=%s",
        (now + timedelta(seconds=1), listing_id),
    )
    for text in (None, "se01native"):
        assert not await present(now, text)
        assert await present(now + timedelta(seconds=1), text)
    await connection.execute(
        "UPDATE listings.sale_listings SET available_from=%s WHERE id=%s",
        (now, listing_id),
    )


async def exercise_expanded_text(
    connection: AsyncConnection[dict[str, Any]],
    now: datetime,
    visible: set[UUID],
    hidden: set[UUID],
) -> None:
    """Run real English-normalized expansion against authoritative rows/index.

    Uses the parent's rollback-only fixtures and explicit unactivated store flag.
    Expectations are hand-specified controlled matching cases, not NFR labels.
    """
    ids = sorted(visible, reverse=True)
    await connection.execute(
        "UPDATE listings.sale_listings SET asking_price_paise=0,negotiable=false WHERE id=ANY(%s)",
        (list(visible),),
    )
    descriptions = (
        "red bicycle",
        "blue car",
        "textbook",
        "novel book",
        "red smartphone",
        "blue mobile phone",
        "laptop",
        "paper notebook",
        "washing machine",
        "washing room",
        "bookcase",
        "bicycle helmet",
        "wooden table",
        "drawing tablet",
        "wooden chair",
        "metal chain",
    )
    for listing_id, description in zip(ids, descriptions):
        await connection.execute(
            "UPDATE listings.sale_listings SET title='Synthetic expansionmarker',description=%s WHERE id=%s",
            (description, listing_id),
        )
    await connection.execute(
        "UPDATE listings.sale_listings SET title='Synthetic expansionmarker',description='red bicycle',asking_price_paise=0,negotiable=false WHERE id=ANY(%s) AND retired_at IS NULL",
        (list(hidden),),
    )
    cases = (
        ("vehicle", {ids[0], ids[1], ids[11]}),
        ("cycles", {ids[0], ids[11]}),
        ("books", {ids[2], ids[3]}),
        ("textbook", {ids[2]}),
        ("red mobile phone", {ids[4]}),
        ("notebook computer", {ids[6]}),
        ("notebook", {ids[7]}),
        ("washing machine", {ids[8]}),
        ("bookcase", {ids[10]}),
        ("vehicle helmet", {ids[11]}),
        ("book chair", set()),
        ("bike", set()),
        # Vocabulary-only spelling alternatives: real English normalization,
        # original text preservation, taxonomy direction and AND semantics.
        ("bicyle", {ids[0], ids[11]}),
        ("bycicle", {ids[0], ids[11]}),
        ("vehicel", {ids[0], ids[1], ids[11]}),
        ("red bicyle", {ids[0]}),
        ("bicyle helmet", {ids[11]}),
        ("red mobile phnoe", {ids[4]}),
        ("notbook computer", {ids[6]}),
        ("washing machnie", {ids[8]}),
        ("boook", {ids[2], ids[3]}),
        ("phnoe", {ids[4], ids[5]}),
        ("fone", set()),
        ("tablex", set()),
        ("tabel", {ids[12]}),
        ("tables", {ids[12]}),
        ("tablet", {ids[13]}),
        # A unique close vocabulary spelling is not proof of a typo: preserve
        # the real original chain match as well as the added chair alternative.
        ("chain", {ids[14], ids[15]}),
        ("moblie phnoe", set()),
        ("bicyle boook phnoe", set()),
    )
    for text, expected in cases:
        page = await read_browse_page(
            connection,
            ListingQuery(q="expansionmarker " + text),
            now,
            500000,
            expanded_search=True,
        )
        assert {row.listing_id for row in page.items} == expected, text
        assert not page.has_next
    await connection.execute(
        "UPDATE listings.sale_listings SET description='red bicyle' WHERE id=%s",
        (ids[0],),
    )
    preserved = await read_browse_page(
        connection,
        ListingQuery(q="expansionmarker bicyle"),
        now,
        500000,
        expanded_search=True,
    )
    assert {row.listing_id for row in preserved.items} == {ids[0], ids[11]}
    # The complete original branch retains nonadjacent original words even when
    # the added corrected aliases themselves use phrase semantics.
    await connection.execute(
        "UPDATE listings.sale_listings SET description='mobile red phnoe' WHERE id=%s",
        (ids[4],),
    )
    preserved_phrase = await read_browse_page(
        connection,
        ListingQuery(q="expansionmarker mobile phnoe"),
        now,
        500000,
        expanded_search=True,
    )
    assert {row.listing_id for row in preserved_phrase.items} == {ids[4], ids[5]}
    await connection.execute(
        "UPDATE listings.sale_listings SET asking_price_paise=100 WHERE id=%s",
        (ids[11],),
    )
    filtered = await read_browse_page(
        connection,
        ListingQuery(q="expansionmarker bicyle", max_price_paise=0),
        now,
        500000,
        expanded_search=True,
    )
    assert {row.listing_id for row in filtered.items} == {ids[0]}
    await connection.execute(
        "UPDATE listings.sale_listings SET negotiable=true WHERE id=%s", (ids[0],)
    )
    combined = await read_browse_page(
        connection,
        ListingQuery(q="expansionmarker bicyle", max_price_paise=0, negotiable=False),
        now,
        500000,
        expanded_search=True,
    )
    assert combined.items == ()
    # Ordinary public-store calls remain plain; their test opt-in is absent.
    plain = await read_browse_page(
        connection, ListingQuery(q="expansionmarker vehicle"), now, 500000
    )
    assert plain.items == ()
    # A title/description edit immediately changes the generated native vector.
    await connection.execute(
        "UPDATE listings.sale_listings SET description='red car' WHERE id=%s", (ids[0],)
    )
    after_edit = await read_browse_page(
        connection,
        ListingQuery(q="expansionmarker cycle"),
        now,
        500000,
        expanded_search=True,
    )
    assert {row.listing_id for row in after_edit.items} == {ids[11]}
    # Test all sizes across a broad matching set without deleting any filters.
    await connection.execute(
        "UPDATE listings.sale_listings SET title='Synthetic expansionmarker',description='red bicycle',asking_price_paise=0,negotiable=false WHERE id=ANY(%s)",
        (list(visible),),
    )
    for size in (20, 50, 100):
        actual = []
        for number in range(1, len(ids) // size + 2):
            page = await read_browse_page(
                connection,
                ListingQuery(
                    q="expansionmarker vehicel",
                    page=number,
                    page_size=size,
                    negotiable=False,
                    max_price_paise=0,
                ),
                now,
                500000,
                expanded_search=True,
            )
            actual.extend(row.listing_id for row in page.items)
            assert page.has_next is (number * size < len(ids))
        assert actual == ids
    # Index eligibility diagnostic for the real composed expression, not latency.
    request = ListingQuery(q="expansionmarker vehicel")
    compiled = await compile_expansion(connection, request.q or "")
    # Isolate the compiled text predicate: the full browse query may correctly
    # prefer its recency index for a broad result set with ORDER BY/LIMIT.
    sql = (
        "SELECT listing.id FROM listings.sale_listings AS listing WHERE listing.search_vector @@ "
        + compiled.sql
    )
    parameters = compiled.parameters
    await connection.execute("SET LOCAL enable_seqscan=off")
    try:
        plan = await (
            await connection.execute("EXPLAIN (FORMAT JSON) " + sql, parameters)
        ).fetchone()
        assert plan is not None
        assert "sale_full_text" in used_indexes(plan["QUERY PLAN"][0]["Plan"])
    finally:
        await connection.execute("SET LOCAL enable_seqscan=DEFAULT")


async def exercise_keyword_relevance(connection, now, visible, hidden):
    """Actual native tier/rank/proximity/page behavior without semantic readiness.

    No Python scoring or model fixture supplies ranking. The source fixtures and
    failed-generation simulation are rolled back with the parent's private run.
    """
    ids = sorted(visible, reverse=True)
    await connection.execute(
        "UPDATE listings.sale_listings SET title='Synthetic keywordmarker',description='unrelated quasar',asking_price_paise=0,negotiable=false,condition_code='good' WHERE id=ANY(%s)",
        (list(visible),),
    )
    await connection.execute(
        "UPDATE listings.sale_listings SET title='Synthetic keywordmarker',description='vehicle vehicle vehicle red bicycle',asking_price_paise=0 WHERE id=ANY(%s) AND retired_at IS NULL",
        (list(hidden),),
    )
    for item, text in [
        (ids[0], "vehicle"),
        (ids[1], "bicycle " * 25),
        (ids[2], "vehicle vehicle"),
    ]:
        await connection.execute(
            "UPDATE listings.sale_listings SET description=%s WHERE id=%s", (text, item)
        )

    async def ranked(query, **kwargs):
        return await read_browse_page(
            connection, query, now, 500000, keyword_relevance=True, **kwargs
        )

    request = ListingQuery(q="vehicle")
    result = await ranked(request)
    assert [item.listing_id for item in result.items] == [ids[2], ids[0], ids[1]]
    # Fixture precondition proves a high expanded rank cannot leap the original
    # tier, rather than accidentally getting the right order from raw rank.
    compiled = await compile_expansion(connection, "vehicle")
    original_rank = await (
        await connection.execute(
            "SELECT ts_rank_cd(search_vector,plainto_tsquery('pg_catalog.english',%s),0) AS rank FROM listings.sale_listings WHERE id=%s",
            ("vehicle", ids[0]),
        )
    ).fetchone()
    expanded_rank = await (
        await connection.execute(
            "SELECT ts_rank_cd(search_vector,"
            + compiled.sql
            + ",0) AS rank FROM listings.sale_listings WHERE id=%s",
            (*compiled.parameters, ids[1]),
        )
    ).fetchone()
    assert expanded_rank["rank"] > original_rank["rank"]
    existing = await read_browse_page(
        connection, request, now, 500000, expanded_search=True
    )
    assert {item.listing_id for item in existing.items} == {
        item.listing_id for item in result.items
    }
    assert [item.listing_id for item in existing.items] == sorted(ids[:3], reverse=True)
    await connection.execute(
        "UPDATE listings.sale_listings SET description='vehicel' WHERE id=%s", (ids[0],)
    )
    assert (await ranked(ListingQuery(q="vehicel"))).items[0].listing_id == ids[0]
    for item, text, price in [
        (ids[0], "red bicycle", 100),
        (ids[1], "red " + "ordinary " * 12 + "bicycle", 200),
        (ids[2], "unrelated quasar", 0),
    ]:
        await connection.execute(
            "UPDATE listings.sale_listings SET description=%s,asking_price_paise=%s WHERE id=%s",
            (text, price, item),
        )
    result = await ranked(ListingQuery(q="red bicycle"))
    assert [item.listing_id for item in result.items] == [ids[0], ids[1]]
    assert [
        item.listing_id for item in (await ranked(ListingQuery(q="red bicyle"))).items
    ] == [ids[0], ids[1]]
    assert [
        item.listing_id
        for item in (
            await ranked(ListingQuery(q="red bicycle", max_price_paise=100))
        ).items
    ] == [ids[0]]
    await connection.execute(
        "UPDATE listings.sale_listings SET negotiable=true,condition_code='fair' WHERE id=%s",
        (ids[1],),
    )
    filtered = await ranked(
        ListingQuery(
            q="red bicycle",
            negotiable=False,
            condition_code="good",
            category_code="bicycles",
        )
    )
    assert [item.listing_id for item in filtered.items] == [ids[0]]
    assert (
        await ranked(ListingQuery(q="red bicycle", category_code="books"))
    ).items == ()
    assert (await ranked(ListingQuery(q="the and of"))).items == ()
    assert (await ranked(ListingQuery(q="astrophysics"))).items == ()
    with pytest.raises(PublicError) as raised:
        await ranked(ListingQuery(q=" "))
    assert raised.value.spec.status == 422
    with pytest.raises(PublicError) as raised:
        await ranked(ListingQuery(q="bicycle", category_code="not_a_category"))
    assert raised.value.spec.status == 422
    await connection.execute(
        "UPDATE listings.sale_listings SET description='red bicycle',asking_price_paise=0,negotiable=false,condition_code='good' WHERE id=ANY(%s)",
        (list(visible),),
    )
    expected = sorted(visible)
    for size in (20, 50, 100):
        actual = []
        for number in range(1, len(expected) // size + 2):
            page = await ranked(
                ListingQuery(
                    q="bicycle",
                    page=number,
                    page_size=size,
                    negotiable=False,
                    max_price_paise=0,
                )
            )
            actual.extend(item.listing_id for item in page.items)
            assert page.has_next is (number * size < len(expected))
        assert actual == expected and len(set(actual)) == len(expected)
    assert (await ranked(ListingQuery(q="bicycle", page=10))).items == ()
    # Private semantic metadata is deliberately unusable: no serving pipeline,
    # current source jobs marked failed. Keyword still reads the same65rows.
    from app.domains.listings.embedding_store import EmbeddingStore
    from app.domains.listings.embedding_types import default_pipeline_spec

    async with connection.transaction(force_rollback=True):
        store = EmbeddingStore(connection)
        spec = default_pipeline_spec()
        await store.register(spec)
        await store.set_state(spec, "building")
        assert await store.queue_missing(spec, 150) < 150
        await connection.execute(
            "UPDATE listings.embedding_generations SET state='failed',attempts=5,failure_code='helper_unavailable' WHERE listing_id=ANY(%s) AND pipeline_id=%s AND state='pending'",
            (list(visible), spec.pipeline_id),
        )
        state = await (
            await connection.execute(
                "SELECT (SELECT count(*) FROM listings.embedding_pipelines WHERE state='serving') AS serving,(SELECT count(*) FROM listings.embedding_generations WHERE state='failed' AND pipeline_id=%s) AS failed",
                (spec.pipeline_id,),
            )
        ).fetchone()
        assert state["serving"] == 0 and state["failed"] >= len(visible)
        all_ids = []
        for number in range(1, 5):
            page = await ranked(ListingQuery(q="bicycle", page=number))
            all_ids.extend(item.listing_id for item in page.items)
        assert all_ids == expected
