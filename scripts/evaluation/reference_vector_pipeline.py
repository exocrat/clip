"""Bounded actual model/operator/worker pipeline production on an injected DB.

Caller owns approved exact target/privileges/connection/helper lifetime. No AWS,
role management, fake vector, provider, reset or background dispatcher is created.
Operator-only diagnostics are not authenticated end-user/HTTP acceptance.
"""

from dataclasses import asdict
from datetime import datetime, UTC
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.domains.listings.embedding_bootstrap import EmbeddingBootstrap  # noqa: E402
from app.domains.listings.embedding_client import (
    SemanticHelper,
    HelperUnavailable,
)  # noqa: E402
from app.domains.listings.embedding_store import EmbeddingStore  # noqa: E402
from app.domains.listings.embedding_worker import EmbeddingWorker  # noqa: E402
from scripts.evaluation.reference_embeddings import require_coverage  # noqa: E402

from app.contracts.domain_types import ListingQuery  # noqa: E402
from app.domains.listings.lexical_expansion import compile_expansion  # noqa: E402
from app.domains.listings.hybrid_read import bind_query, hybrid_statement  # noqa: E402


class VectorHelper(SemanticHelper):
    """One real helper with a strict 2400-model-window production budget."""

    async def encode_listing(self, title, description):
        if self.windows_started + 97 > 2400:
            raise HelperUnavailable("vector_model_window_budget")
        return await super().encode_listing(title, description)

    async def encode_query(self, text):
        if self.windows_started + 1 > 2400:
            raise HelperUnavailable("vector_model_window_budget")
        return await super().encode_query(text)


async def guard_producer(connection, *, owned_socket=None):
    """Bind actual authenticated role/server/transport before pipeline mutation."""
    from scripts.evaluation.reference_admin_inventory import HOST
    from scripts.evaluation.reference_database_setup import DATABASE
    from scripts.evaluation.reference_vector_access import ROLE

    row = await (
        await connection.execute(
            "SELECT current_database() AS db,current_user AS role,session_user AS login,current_setting('server_version_num') AS version"
        )
    ).fetchone()
    if connection.autocommit is not True or row != {
        "db": DATABASE,
        "role": ROLE,
        "login": ROLE,
        "version": "180006",
    }:
        raise ValueError("actual_vector_producer_target_changed")
    if owned_socket is None:
        params = connection.info.get_parameters()
        if (
            connection.info.host != HOST
            or connection.info.port != 5432
            or params.get("hostaddr") != "127.0.0.1"
            or params.get("sslmode") != "verify-full"
            or not connection.pgconn.ssl_in_use
        ):
            raise ValueError("actual_vector_private_tls_required")
    elif (
        not isinstance(owned_socket, Path)
        or not str(owned_socket).startswith("/private/tmp/clip-next06-reference-")
        or owned_socket.name != "pgsocket"
        or owned_socket.is_symlink()
        or connection.info.host != str(owned_socket)
        or connection.info.port != 55438
    ):
        raise ValueError("actual_vector_owned_socket_required")


async def produce(connection, helper, *, record):
    """Publish exactly1000current sources, activate only complete pinned coverage.

    No retry/defer loop. Any worker result other than published stops, preserving
    actual generation state/leases for separately reviewed recovery. Progress is
    aggregate only; listing text/IDs, vectors and SQL errors never enter reports.
    """
    operator = EmbeddingBootstrap(connection)
    before = await operator.status()
    if before.state != "absent" or before.live != 1000 or before.conflicting_serving:
        raise ValueError("fresh_vector_pipeline_required")
    await operator.prepare()
    queued = await operator.queue(1000)
    if queued != 1000:
        raise ValueError("vector_queue_count_changed")
    record(stage="vector_queued", count=queued)
    worker = EmbeddingWorker(EmbeddingStore(connection), helper)
    for index in range(1000):
        outcome = await worker.run_one()
        if outcome != "published":
            record(stage="vector_worker_stopped", published=index, outcome=outcome)
            raise ValueError("vector_worker_not_published")
        if (index + 1) % 100 == 0:
            record(stage="vector_progress", published=index + 1)
    if await worker.run_one() != "idle":
        raise ValueError("unexpected_additional_vector_work")
    coverage = await operator.activate()
    require_coverage(coverage, 1000)
    parts = await (
        await connection.execute(
            "SELECT part_kind,count(*) AS count FROM listings.embedding_chunks GROUP BY part_kind ORDER BY part_kind"
        )
    ).fetchall()
    record(stage="vector_pipeline_serving", ready=coverage.ready)
    # Authenticated operator-only diagnostics use the actual production SQL and
    # typo compiler. They do not manufacture a CallerContext or mount HTTP.
    cases = []
    for query in (
        "cycle",
        "cycel",
        "vehicle",
        "wheeled vehicle",
        "books",
        "office chair",
    ):
        now = datetime.now(UTC)
        encoded = await helper.encode_query(query)
        compiled = await compile_expansion(connection, query)
        eligible = await (
            await connection.execute(
                "SELECT id::text AS id FROM listings.sale_listings WHERE availability='available' AND retired_at IS NULL AND retirement_pending_operation_id IS NULL AND available_from<=%s AND (available_until IS NULL OR available_until>%s)",
                (now, now),
            )
        ).fetchall()
        allowed = {row["id"] for row in eligible}
        keyword = await (
            await connection.execute(
                "SELECT id::text AS id FROM listings.sale_listings WHERE availability='available' AND retired_at IS NULL AND retirement_pending_operation_id IS NULL AND available_from<=%s AND (available_until IS NULL OR available_until>%s) AND search_vector @@ ("
                + compiled.sql
                + ")",
                (now, now, *compiled.parameters),
            )
        ).fetchall()
        keyword_ids = {row["id"] for row in keyword}
        ids = []
        for page in range(1, 12):
            request = ListingQuery(
                q=query,
                search_mode="hybrid",
                sort="relevance",
                page=page,
                page_size=100,
            )
            statement, params = hybrid_statement(
                request,
                now,
                500000,
                bind_query(query, helper.spec, encoded.vector),
                compiled,
                relevance=True,
            )
            row = await (await connection.execute(statement, params)).fetchone()
            if (
                row is None
                or row["ready"] is not True
                or row["category_valid"] is not True
                or row["condition_valid"] is not True
            ):
                raise ValueError("hybrid_snapshot_not_ready")
            items = row["items"]
            ids.extend(str(item["listing_id"]) for item in items[:100])
            if len(items) <= 100:
                break
        else:
            raise ValueError("hybrid_diagnostic_page_budget")
        if (
            not keyword_ids
            or not keyword_ids <= set(ids)
            or not set(ids) <= allowed
            or len(ids) != len(set(ids))
        ):
            raise ValueError("representative_hybrid_union_or_visibility_failed")
        cases.append(
            {
                "query": query,
                "keyword_count": len(keyword_ids),
                "hybrid_count": len(ids),
                "lexical_outcome": compiled.outcome,
                "unique_visible_union_verified": True,
            }
        )
    return {
        "state": "real_pinned_vectors_serving",
        "queued": queued,
        "published": 1000,
        "coverage": asdict(coverage),
        "parts": parts,
        "search_diagnostics": cases,
        "model_windows": helper.windows_started,
        "real_app_auth_media_verified": False,
        "deployed_linux_runtime_verified": False,
        "data_ready": False,
    }


def window_outcome(report):
    """Classify vector window only after verified model/access/resource closeout."""
    attempts = report.get("resource_start_attempts")
    if (
        not isinstance(attempts, dict)
        or set(attempts) != {"rds", "ec2"}
        or any(type(v) is not bool for v in attempts.values())
    ):
        return "cleanup_pending_operator_attention"
    if not any(attempts.values()):
        return "blocked_before_starts"
    cleanup = report.get("cleanup", {})
    if (
        not isinstance(cleanup, dict)
        or cleanup.get("pending")
        or any(
            attempts[k]
            and cleanup.get({"ec2": "host_stopped", "rds": "rds_stopped"}[k])
            is not True
            for k in attempts
        )
    ):
        return "cleanup_pending_operator_attention"
    if report.get("vector_passed") is not True:
        return "vector_window_failed_resources_stopped"
    if any(
        cleanup.get(k) is not True
        for k in (
            "vector_disabled_password_cleared",
            "owned_model_closed",
            "owned_tunnel_exited",
            "owned_session_terminated",
        )
    ):
        return "cleanup_pending_operator_attention"
    result = report.get("vector_result", {})
    coverage = result.get("coverage", {}) if isinstance(result, dict) else {}
    if (
        not isinstance(coverage, dict)
        or coverage.get("state") != "serving"
        or coverage.get("live") != 1000
        or coverage.get("ready") != 1000
        or any(
            coverage.get(k) != 0
            for k in (
                "missing",
                "stale",
                "pending",
                "leased",
                "failed",
                "invalid_parts",
            )
        )
    ):
        return "vector_window_failed_resources_stopped"
    return "vectors_published_resources_stopped"
