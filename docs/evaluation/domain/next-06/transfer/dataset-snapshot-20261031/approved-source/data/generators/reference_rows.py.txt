"""Schema-aware reference rows shared by guarded local and cloud adapters.

Callers must validate input, exact target and actual object bytes before insertion.
This module never connects, uploads, chooses a target or bypasses constraints.
"""

from datetime import timedelta
from .manifest import _utc_timestamp
from .reference import digest


def insert_rows(connection, bundle, *, object_key_for, audit):
    """Atomically insert a complete empty-target batch and verify its projections.

    A final locked emptiness check closes the preflight/upload race. Actual object
    confirmation metadata uses the supplied audit time; normal constraints remain.
    """
    with connection.transaction():
        connection.execute("SET LOCAL statement_timeout='60s'")
        connection.execute("SET LOCAL lock_timeout='5s'")
        connection.execute("SET LOCAL TIME ZONE 'UTC'")
        connection.execute(
            "LOCK TABLE identity.users,listings.sale_listings,listings.image_uploads,listings.images IN ACCESS EXCLUSIVE MODE"
        )
        counts = connection.execute(
            "SELECT (SELECT count(*) FROM identity.users),(SELECT count(*) FROM listings.sale_listings),(SELECT count(*) FROM listings.image_uploads),(SELECT count(*) FROM listings.images)"
        ).fetchone()
        if counts != (0, 0, 0, 0):
            raise ValueError(
                "Reference target is not empty; overwrite/reset is unsupported"
            )
        categories = {
            r[0]: (r[1], r[2])
            for r in connection.execute(
                "SELECT code,id,sensitive_category FROM listings.categories WHERE active"
            )
        }
        conditions = {
            r[0]: r[1]
            for r in connection.execute(
                "SELECT code,label FROM listings.conditions WHERE active"
            )
        }
        expected_categories = set(bundle["manifest"]["observed_counts"]["categories"])
        if set(categories) != expected_categories or conditions != {
            "new": "New / Unused",
            "like_new": "Like New",
            "good": "Good",
            "fair": "Fair",
        }:
            raise ValueError("Active catalogue differs from the approved recipe")
        if {c for c, v in categories.items() if v[1]} != {"mobile_phone", "laptop"}:
            raise ValueError("Sensitive category policy differs")
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO identity.users(id,account_class,status,display_name,handle_ready,created_at,activated_at,expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        u["id"],
                        u["account_class"],
                        u["status"],
                        u["display_name"],
                        u["handle_ready"],
                        u["created_at"],
                        u["activated_at"],
                        u["expires_at"],
                    )
                    for u in bundle["users"]
                ],
            )
            for row, image in zip(
                bundle["listings"], bundle["image_plan"], strict=True
            ):
                if (
                    image["listing_id"] != row["id"]
                    or image["owner_id"] != row["owner_id"]
                ):
                    raise ValueError("Image/owner plan mismatch")
                cursor.execute(
                    """INSERT INTO listings.sale_listings(id,owner_id,title,description,category_id,condition_code,asking_price_paise,negotiable,pickup_area,proof_available,availability,available_from,available_until,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        row["id"],
                        row["owner_id"],
                        row["title"],
                        row["description"],
                        categories[row["category_code"]][0],
                        row["condition_code"],
                        row["asking_price_paise"],
                        row["negotiable"],
                        row["pickup_area"],
                        row.get("proof_available"),
                        row["availability"],
                        row["available_from"],
                        row["available_until"],
                        row["created_at"],
                        row["updated_at"],
                    ),
                )
                key = object_key_for(image["upload_id"])
                cursor.execute(
                    """INSERT INTO listings.image_uploads(id,owner_id,operation_id,object_key,state,created_at,expires_at,confirmed_at,requested_media_type,requested_size_bytes,confirmed_media_type,confirmed_size_bytes) VALUES(%s,%s,%s,%s,'confirmed',%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        image["upload_id"],
                        image["owner_id"],
                        image["operation_id"],
                        key,
                        audit,
                        audit + timedelta(hours=24),
                        audit,
                        image["media_type"],
                        image["size_bytes"],
                        image["media_type"],
                        image["size_bytes"],
                    ),
                )
                cursor.execute(
                    "INSERT INTO listings.images(id,listing_id,upload_id,object_key,position,media_type,size_bytes,created_at) VALUES(%s,%s,%s,%s,0,%s,%s,%s)",
                    (
                        image["image_id"],
                        row["id"],
                        image["upload_id"],
                        key,
                        image["media_type"],
                        image["size_bytes"],
                        row["created_at"],
                    ),
                )
        connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
        validation = validate_rows(connection, bundle, object_key_for=object_key_for)
    return validation


def validate_rows(connection, bundle, *, object_key_for):
    """Compare all logical row projections, FK joins, active counts and search indexes."""
    users = connection.execute(
        "SELECT id::text,account_class,status,display_name,handle_ready,created_at,activated_at,expires_at FROM identity.users ORDER BY id"
    ).fetchall()
    actual_users = [
        (
            a,
            b,
            c,
            d,
            e,
            _utc_timestamp(f),
            _utc_timestamp(g) if g else None,
            _utc_timestamp(h) if h else None,
        )
        for a, b, c, d, e, f, g, h in users
    ]
    expected_users = sorted(
        [
            (
                u["id"],
                u["account_class"],
                u["status"],
                u["display_name"],
                u["handle_ready"],
                u["created_at"],
                u["activated_at"],
                u["expires_at"],
            )
            for u in bundle["users"]
        ]
    )
    if actual_users != expected_users:
        raise ValueError("Loaded user projection differs")
    rows = connection.execute(
        """SELECT l.id::text,l.owner_id::text,l.title,l.description,c.code,l.condition_code,l.asking_price_paise,l.negotiable,l.pickup_area,l.proof_available,l.availability,l.available_from,l.available_until,l.created_at,l.updated_at FROM listings.sale_listings l JOIN listings.categories c ON c.id=l.category_id ORDER BY l.id"""
    ).fetchall()
    actual = [tuple(r[:11]) + tuple(_utc_timestamp(v) for v in r[11:]) for r in rows]
    fields = (
        "id",
        "owner_id",
        "title",
        "description",
        "category_code",
        "condition_code",
        "asking_price_paise",
        "negotiable",
        "pickup_area",
        "proof_available",
        "availability",
        "available_from",
        "available_until",
        "created_at",
        "updated_at",
    )
    expected = sorted(tuple(r.get(k) for k in fields) for r in bundle["listings"])
    if actual != expected:
        raise ValueError("Loaded listing projection differs")
    counts = connection.execute(
        "SELECT (SELECT count(*) FROM listings.image_uploads WHERE state='confirmed'),(SELECT count(*) FROM listings.images),(SELECT count(DISTINCT owner_id) FROM listings.sale_listings),(SELECT count(*) FROM listings.sale_listings WHERE search_vector=to_tsvector('pg_catalog.english',coalesce(title,'')||' '||coalesce(description,'')))"
    ).fetchone()
    if counts != (1000, 1000, 1000, 1000):
        raise ValueError("Image/owner/vector counts differ")
    image_rows = connection.execute(
        """SELECT i.id::text,i.listing_id::text,i.upload_id::text,u.owner_id::text,i.object_key,i.media_type,i.size_bytes FROM listings.images i JOIN listings.image_uploads u ON u.id=i.upload_id JOIN listings.sale_listings l ON l.id=i.listing_id AND l.owner_id=u.owner_id ORDER BY i.id"""
    ).fetchall()
    image_expected = sorted(
        (
            i["image_id"],
            i["listing_id"],
            i["upload_id"],
            i["owner_id"],
            object_key_for(i["upload_id"]),
            i["media_type"],
            i["size_bytes"],
        )
        for i in bundle["image_plan"]
    )
    if image_rows != image_expected:
        raise ValueError("Loaded image binding differs")
    instant = bundle["manifest"]["measurement_window"]["from"]
    available = connection.execute(
        "SELECT count(*) FROM listings.sale_listings WHERE availability='available' AND retired_at IS NULL AND available_from<=%s AND (available_until IS NULL OR available_until>%s)",
        (instant, instant),
    ).fetchone()[0]
    if available != 800:
        raise ValueError("Expected800current discoverable records")
    indexes = [
        r[0]
        for r in connection.execute(
            "SELECT indexdef FROM pg_indexes WHERE schemaname='listings' AND indexdef ILIKE '%USING gin%' AND indexdef LIKE '%search_vector%'"
        )
    ]
    if not indexes:
        raise ValueError("Expected actual GIN text-search index")
    return {
        "users_verified": 5000,
        "listings_verified": 1000,
        "images_verified": 1000,
        "regular_owners_verified": 1000,
        "available_verified": 800,
        "logical_projection_digest": digest(
            {"users": actual_users, "listings": actual, "images": image_rows}
        ),
        "text_vectors_verified": 1000,
        "text_search_indexes": indexes,
    }
