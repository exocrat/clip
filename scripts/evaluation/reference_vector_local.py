"""Real worker/model and least-privilege checks in the caller's fresh native DB."""

from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from scripts.evaluation.reference_vector_access import ROLE
from scripts.evaluation.reference_database_setup import DATABASE
from scripts.evaluation.reference_vector_pipeline import (
    VectorHelper,
    produce,
    guard_producer,
)


async def run(cluster, password, *, record):
    """Use actual native SCRAM, real pinned inference and normal worker publication.

    This proves SQL grants/model/data/search mechanics, not actual Identity/S3 or
    cloud permission/runtime behavior. No network listener or AWS client exists.
    """
    root = Path(__file__).resolve().parents[2]
    helper = VectorHelper(
        root / ".tools/semantic/venv/bin/python", root / ".tools/semantic/model"
    )
    try:
        await helper.start()
        async with await psycopg.AsyncConnection.connect(
            host=str(cluster.socket),
            port=55438,
            dbname=DATABASE,
            user=ROLE,
            password=password,
            autocommit=True,
            connect_timeout=3,
            row_factory=dict_row,
            options="-c statement_timeout=5000 -c lock_timeout=1000",
        ) as connection:
            await guard_producer(connection, owned_socket=cluster.socket)
            result = await produce(connection, helper, record=record)
            denied = [
                "UPDATE listings.sale_listings SET title=title",
                "UPDATE listings.sale_listings SET asking_price_paise=asking_price_paise",
                "DELETE FROM listings.sale_listings",
                "DELETE FROM listings.embedding_pipelines",
                "UPDATE listings.embedding_chunks SET ordinal=ordinal",
                "SELECT 1 FROM identity.users LIMIT 1",
                "CREATE TABLE listings.unapproved(id int)",
                "CREATE ROLE unapproved",
            ]
            for statement in denied:
                try:
                    await connection.execute(statement)
                except psycopg.errors.InsufficientPrivilege:
                    pass
                else:
                    raise ValueError("unapproved_vector_privilege_allowed")
            try:
                await connection.execute(
                    "UPDATE listings.sale_listings SET id=gen_random_uuid() WHERE id=(SELECT id FROM listings.sale_listings LIMIT 1)"
                )
            except psycopg.errors.CheckViolation:
                pass
            else:
                raise ValueError("immutable_listing_id_not_protected")
            flags = await (
                await connection.execute(
                    "SELECT has_table_privilege(current_user,'listings.sale_listings','UPDATE') AS full_update,has_column_privilege(current_user,'listings.sale_listings','id','UPDATE') AS id_update"
                )
            ).fetchone()
            if flags != {"full_update": False, "id_update": True}:
                raise ValueError("column_lock_grants_changed")
            result["negative_permission_checks"] = len(denied) + 1
            result["column_only_row_lock_grant_verified"] = True
            result["helper_peak_rss_bytes"] = helper.helper_peak_rss_bytes
            return result
    finally:
        await helper.close()
