"""SE-01 development-only native/model calibration and deterministic comparisons.

No app import, production ranking, final labels, DB target discovery or model
installation. Only the opted-in disposable native test invokes measurement;
CLI reanalyzes a captured, strictly bound matrix without running SQL/inference.
"""

import argparse
from dataclasses import dataclass, field
from datetime import datetime, UTC
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys
from typing import Any
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.domains.listings.embedding_client import SemanticHelper
from app.domains.listings.embedding_types import default_pipeline_spec
from app.domains.listings.lexical_expansion import compile_expansion
from app.domains.listings.vocabulary import load_vocabulary
from psycopg import AsyncConnection
from psycopg.pq import TransactionStatus

FIXTURE = ROOT / "data/evaluation/development/hybrid-search-v1.json"
NAMESPACE = UUID("74242d6c-1df7-49fc-babb-35336446df8a")
AGGREGATIONS = ("title", "max", "blend")
THRESHOLDS = (0.25, 0.35, 0.45, 0.55, 0.65)
FUSIONS = ("tiered", "boosted")
CAPS = (None, 3, 5)


class CalibrationError(ValueError):
    """Fixed error codes only; never echo file contents, SQL or vector payloads."""


def fingerprint(value: object) -> str:
    """Hash canonical JSON for exact data/model/vocabulary/evidence binding."""
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Refuse duplicate JSON keys before a later value can mask a binding."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise CalibrationError("duplicate_json_key")
        result[key] = value
    return result


def read_json(path: Path, maximum: int) -> dict[str, Any]:
    """Bound files and parse strictly; hide malformed input from diagnostics."""
    try:
        with path.open("rb") as source:
            raw = source.read(maximum + 1)
        if len(raw) > maximum:
            raise ValueError
        document = json.loads(raw, object_pairs_hook=_pairs)
        if not isinstance(document, dict):
            raise ValueError
        # Also rejects JSON's otherwise accepted NaN/Infinity extension.
        fingerprint(document)
        return document
    except Exception:
        raise CalibrationError("invalid_calibration_json") from None


@dataclass(frozen=True)
class DevelopmentSet:
    """Versioned synthetic fixture intent; never human-reviewed final judgments."""

    document: dict[str, Any] = field(repr=False)

    @property
    def fingerprint(self) -> str:
        """Bind exact source text and fixture-author intent, before measuring."""
        return fingerprint(self.document)

    def listing_id(self, key: str) -> str:
        """Stable UUID tie-break independent of input ordering or result pages."""
        return str(uuid5(NAMESPACE, key))


def development_set(document: dict[str, Any]) -> DevelopmentSet:
    """Accept only bounded, explicitly unreviewed development-format fixtures."""
    try:
        if set(document) != {
            "format_version",
            "purpose",
            "synthetic",
            "human_review_verified",
            "judgment_origin",
            "listings",
            "queries",
        }:
            raise ValueError
        if (
            type(document["format_version"]) is not int
            or document["format_version"] != 1
            or document["purpose"] != "development_calibration"
            or document["synthetic"] is not True
            or document["human_review_verified"] is not False
            or document["judgment_origin"] != "fixture_author_intent"
        ):
            raise ValueError
        rows, queries = document["listings"], document["queries"]
        if (
            not isinstance(rows, list)
            or not 1 <= len(rows) <= 8
            or not isinstance(queries, list)
            or not 1 <= len(queries) <= 11
        ):
            raise ValueError
        listing_keys, query_keys = set(), set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"key", "title", "description"}:
                raise ValueError
            if (
                not isinstance(row["key"], str)
                or not re.fullmatch("[a-z][a-z_]{0,39}", row["key"])
                or row["key"] in listing_keys
            ):
                raise ValueError
            listing_keys.add(row["key"])
            for key, maximum in [("title", 120), ("description", 5000)]:
                if (
                    not isinstance(row[key], str)
                    or not row[key].strip()
                    or len(row[key]) > maximum
                ):
                    raise ValueError
        for query in queries:
            if not isinstance(query, dict) or set(query) != {
                "key",
                "text",
                "relevant_keys",
            }:
                raise ValueError
            key, text, relevant = query["key"], query["text"], query["relevant_keys"]
            if (
                not isinstance(key, str)
                or not re.fullmatch("[a-z][a-z_]{0,39}", key)
                or key in query_keys
            ):
                raise ValueError
            query_keys.add(key)
            if not isinstance(text, str) or not text.strip() or len(text) > 120:
                raise ValueError
            if (
                not isinstance(relevant, list)
                or any(not isinstance(item, str) for item in relevant)
                or len(set(relevant)) != len(relevant)
                or not set(relevant) <= listing_keys
            ):
                raise ValueError
        return DevelopmentSet(document)
    except Exception:
        raise CalibrationError("invalid_development_fixture") from None


def validate_matrix(dataset: DevelopmentSet, matrix: dict[str, Any]) -> None:
    """Require every query/listing pair, exact bindings and finite native scores.

    Binding validation does not independently attest how a supplied file was
    produced; the native runner/evidence source hashes establish that provenance.
    """
    try:
        if set(matrix) != {
            "format_version",
            "fixture_fingerprint",
            "pipeline_id",
            "vocabulary_fingerprint",
            "queries",
        }:
            raise ValueError
        if (
            type(matrix["format_version"]) is not int
            or matrix["format_version"] != 1
            or matrix["fixture_fingerprint"] != dataset.fingerprint
            or matrix["pipeline_id"] != default_pipeline_spec().pipeline_id.hex()
            or matrix["vocabulary_fingerprint"] != load_vocabulary().fingerprint
        ):
            raise ValueError
        expected_queries = {query["key"] for query in dataset.document["queries"]}
        expected_listings = {row["key"] for row in dataset.document["listings"]}
        if not isinstance(matrix["queries"], list) or len(matrix["queries"]) != len(
            expected_queries
        ):
            raise ValueError
        seen_queries = set()
        for query in matrix["queries"]:
            if (
                not isinstance(query, dict)
                or set(query) != {"key", "rows"}
                or query["key"] not in expected_queries
                or query["key"] in seen_queries
            ):
                raise ValueError
            seen_queries.add(query["key"])
            if not isinstance(query["rows"], list) or len(query["rows"]) != len(
                expected_listings
            ):
                raise ValueError
            seen = set()
            for row in query["rows"]:
                if not isinstance(row, dict) or set(row) != {
                    "key",
                    "listing_id",
                    "original",
                    "expanded",
                    "title_score",
                    "description_score",
                }:
                    raise ValueError
                key = row["key"]
                if (
                    key not in expected_listings
                    or key in seen
                    or row["listing_id"] != dataset.listing_id(key)
                ):
                    raise ValueError
                seen.add(key)
                if (
                    type(row["original"]) is not bool
                    or type(row["expanded"]) is not bool
                    or (row["original"] and not row["expanded"])
                ):
                    raise ValueError
                for score in [row["title_score"], row["description_score"]]:
                    if (
                        type(score) not in {int, float}
                        or not math.isfinite(score)
                        or not -1 <= score <= 1
                    ):
                        raise ValueError
    except Exception:
        raise CalibrationError("invalid_score_matrix") from None


def semantic_score(row: dict[str, Any], aggregation: str) -> float:
    """Compare title-only, best complete part, and35/65 title/description blend."""
    if aggregation == "title":
        return float(row["title_score"])
    if aggregation == "max":
        return float(max(row["title_score"], row["description_score"]))
    if aggregation == "blend":
        return float(0.35 * row["title_score"] + 0.65 * row["description_score"])
    raise CalibrationError("invalid_aggregation")


def ranked(
    rows: list[dict[str, Any]],
    aggregation: str,
    threshold: float,
    fusion: str,
    cap: int | None,
    *,
    mode: str = "hybrid",
) -> list[str]:
    """Whole-corpus union before order; caps affect semantic candidates only.

    Tiered guarantees original-term > expanded-only > semantic-only evidence.
    Boosted adds .25 original/.10 expanded-only to similarity; it guarantees no
    such tier dominance. Both preserve keyword membership, even misleading hits.
    UUID is the final deterministic tie. No per-page ranking is performed.
    """
    if (
        aggregation not in AGGREGATIONS
        or threshold not in THRESHOLDS
        or fusion not in FUSIONS
        or (cap is not None and (type(cap) is not int or cap not in (3, 5)))
        or mode not in {"hybrid", "keyword", "expanded"}
    ):
        raise CalibrationError("invalid_comparison_settings")
    scores = {row["key"]: semantic_score(row, aggregation) for row in rows}
    semantic = sorted(
        (row for row in rows if scores[row["key"]] >= threshold),
        key=lambda row: (-scores[row["key"]], row["listing_id"]),
    )
    semantic_keys = {
        row["key"] for row in (semantic if cap is None else semantic[:cap])
    }
    selected = [
        row
        for row in rows
        if row["original"]
        or (mode != "keyword" and row["expanded"])
        or (mode == "hybrid" and row["key"] in semantic_keys)
    ]

    def order(row: dict[str, Any]) -> tuple[float, float, str]:
        """Keep semantic scoring out of the standalone keyword baselines."""
        if mode != "hybrid":
            return (0.0, 0.0, row["listing_id"])
        tier = 2 if row["original"] else 1 if row["expanded"] else 0
        score = scores[row["key"]]
        if fusion == "tiered":
            return (-float(tier), -score, row["listing_id"])
        boost = 0.25 if row["original"] else 0.10 if row["expanded"] else 0.0
        return (-(score + boost), 0.0, row["listing_id"])

    return [row["key"] for row in sorted(selected, key=order)]


def summarize(
    dataset: DevelopmentSet,
    matrix: dict[str, Any],
    settings: dict[str, Any],
    *,
    mode: str = "hybrid",
) -> dict[str, Any]:
    """Report all11 cases including empty judgments; never claim final Success@5."""
    expected = {
        query["key"]: set(query["relevant_keys"])
        for query in dataset.document["queries"]
    }
    details = []
    tp = predicted_count = relevant_count = hits = positive_queries = empty_correct = (
        empty_queries
    ) = top1 = 0
    for query in matrix["queries"]:
        keys = ranked(query["rows"], **settings, mode=mode)
        relevant = expected[query["key"]]
        selected = set(keys)
        tp += len(selected & relevant)
        predicted_count += len(selected)
        relevant_count += len(relevant)
        hit = bool(relevant.intersection(keys[:5]))
        hits += hit
        positive_queries += bool(relevant)
        top1 += bool(keys and keys[0] in relevant)
        empty_queries += not relevant
        empty_correct += not relevant and not selected
        details.append(
            {
                "key": query["key"],
                "returned": keys,
                "hit_at5": hit,
                "missing": sorted(relevant - selected),
                "unexpected": sorted(selected - relevant),
            }
        )
    return {
        "settings": settings | {"mode": mode},
        "candidate_precision": tp / predicted_count if predicted_count else 0.0,
        "candidate_recall": tp / relevant_count if relevant_count else 0.0,
        "true_positive_pairs": tp,
        "returned_pairs": predicted_count,
        "expected_pairs": relevant_count,
        "all_query_count": len(details),
        "development_hits_at5": hits,
        "positive_query_count": positive_queries,
        "positive_top1": top1,
        "empty_query_count": empty_queries,
        "empty_queries_correct": empty_correct,
        "queries": details,
    }


def analyze(dataset: DevelopmentSet, matrix: dict[str, Any]) -> dict[str, Any]:
    """Compare a predeclared90-setting grid; do not auto-freeze a winning policy."""
    validate_matrix(dataset, matrix)
    baseline = {
        "aggregation": "max",
        "threshold": 0.45,
        "fusion": "tiered",
        "cap": None,
    }
    comparisons = [
        summarize(
            dataset,
            matrix,
            {
                "aggregation": aggregation,
                "threshold": threshold,
                "fusion": fusion,
                "cap": cap,
            },
        )
        for aggregation, threshold, fusion, cap in itertools.product(
            AGGREGATIONS, THRESHOLDS, FUSIONS, CAPS
        )
    ]
    return {
        "purpose": "development_only",
        "policy_frozen": False,
        "human_review_verified": False,
        "final_labels_used": False,
        "nfr_accepted": False,
        "fixture_fingerprint": dataset.fingerprint,
        "matrix_fingerprint": fingerprint(matrix),
        "keyword": summarize(dataset, matrix, baseline, mode="keyword"),
        "expanded_keyword": summarize(dataset, matrix, baseline, mode="expanded"),
        "comparisons": comparisons,
    }


async def measure(
    connection: AsyncConnection[dict[str, Any]],
    helper: SemanticHelper,
    dataset: DevelopmentSet,
) -> dict[str, Any]:
    """Measure fixed synthetic rows using real local embeddings/native SQL.

    Only an idle dedicated runner connection is accepted. Temporary tables exist
    in this owned session; no base listing/user/job records are read or changed.
    Model text never enters retained matrix output; vectors remain memory/temp.
    """
    socket = Path(connection.info.host)
    if (
        not connection.autocommit
        or connection.info.transaction_status != TransactionStatus.IDLE
        or connection.info.dbname != "clip_test_ci"
        or connection.info.user != "clip_ci"
        or socket.name != "pgsocket"
        or not socket.parent.name.startswith("clip-listings-test-")
        or str(socket.parent.parent) not in {"/tmp", "/private/tmp"}
        or connection.info.port not in {5432, 55438}
        or helper.spec != default_pipeline_spec()
    ):
        raise CalibrationError("disposable_idle_target_required")
    identity = await (
        await connection.execute(
            "SELECT current_database() AS name,inet_server_addr() IS NULL AS local_socket"
        )
    ).fetchone()
    if identity != {"name": "clip_test_ci", "local_socket": True}:
        raise CalibrationError("disposable_idle_target_required")
    # No table is dropped to make space for a collision with another session user.
    await connection.execute(
        "CREATE TEMPORARY TABLE calibration_listings(id uuid PRIMARY KEY,key text UNIQUE NOT NULL,title text NOT NULL,description text NOT NULL,search_vector tsvector GENERATED ALWAYS AS (to_tsvector('pg_catalog.english'::regconfig,title || ' ' || description)) STORED)"
    )
    chunks_created = False
    try:
        await connection.execute(
            "CREATE TEMPORARY TABLE calibration_chunks(listing_id uuid NOT NULL,part_kind text NOT NULL,ordinal integer NOT NULL,vector real[] NOT NULL,PRIMARY KEY(listing_id,part_kind,ordinal))"
        )
        chunks_created = True
        for listing in dataset.document["listings"]:
            output = await helper.encode_listing(
                listing["title"], listing["description"]
            )
            if helper.windows_started > 30:
                raise CalibrationError("model_window_budget")
            async with connection.transaction():
                await connection.execute(
                    "INSERT INTO pg_temp.calibration_listings(id,key,title,description) VALUES (%s,%s,%s,%s)",
                    (
                        dataset.listing_id(listing["key"]),
                        listing["key"],
                        listing["title"],
                        listing["description"],
                    ),
                )
                async with connection.cursor() as cursor:
                    await cursor.executemany(
                        "INSERT INTO pg_temp.calibration_chunks VALUES (%s,%s,%s,%s)",
                        [
                            (
                                dataset.listing_id(listing["key"]),
                                part.kind,
                                part.ordinal,
                                list(part.vector),
                            )
                            for part in output.parts
                        ],
                    )
        queries = []
        for query in dataset.document["queries"]:
            vector = await helper.encode_query(query["text"])
            if helper.windows_started > 30:
                raise CalibrationError("model_window_budget")
            expanded = await compile_expansion(connection, query["text"])
            # Exactly the preserved native FTS predicate, plus real compiler and
            # exact native cosine, over every fixture row before any comparison cap.
            statement = (
                """WITH input AS (SELECT %s::real[] AS vector,
                plainto_tsquery('pg_catalog.english', %s) AS original, """
                + expanded.sql
                + """ AS expanded)
                SELECT listing.key,listing.id::text AS listing_id,
                listing.search_vector @@ input.original AS original,
                listing.search_vector @@ input.expanded AS expanded,
                scores.title_score,scores.description_score
                FROM pg_temp.calibration_listings AS listing CROSS JOIN input
                CROSS JOIN LATERAL (SELECT
                  max(listings.embedding_cosine(chunk.vector,input.vector)) FILTER (WHERE part_kind='title') AS title_score,
                  max(listings.embedding_cosine(chunk.vector,input.vector)) FILTER (WHERE part_kind='description') AS description_score
                  FROM pg_temp.calibration_chunks AS chunk WHERE chunk.listing_id=listing.id) AS scores
                ORDER BY listing.id"""
            )
            async with connection.transaction():
                await connection.execute("SET LOCAL statement_timeout='3s'")
                await connection.execute("SET LOCAL lock_timeout='1s'")
                rows = await (
                    await connection.execute(
                        statement,
                        (list(vector.vector), query["text"], *expanded.parameters),
                    )
                ).fetchall()
            queries.append({"key": query["key"], "rows": rows})
        matrix = {
            "format_version": 1,
            "fixture_fingerprint": dataset.fingerprint,
            "pipeline_id": helper.spec.pipeline_id.hex(),
            "vocabulary_fingerprint": load_vocabulary().fingerprint,
            "queries": queries,
        }
        validate_matrix(dataset, matrix)
        return matrix
    finally:
        # Only these freshly-created session-local fixture tables are removed.
        if chunks_created:
            await connection.execute("DROP TABLE pg_temp.calibration_chunks")
        await connection.execute("DROP TABLE pg_temp.calibration_listings")


def main() -> None:
    """Reanalyze safe bound matrix only; no DB/model CLI or arbitrary output target."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze", type=Path, required=True)
    args = parser.parse_args()
    try:
        dataset = development_set(read_json(FIXTURE, 65536))
        result = analyze(dataset, read_json(args.analyze, 2 * 1024 * 1024))
        folder = (
            ROOT
            / ".tools/semantic/calibration-analysis"
            / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        )
        folder.mkdir(parents=True, exist_ok=False)
        (folder / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "status": "development_analysis_only",
                    "comparisons": len(result["comparisons"]),
                    "run": str(folder.relative_to(ROOT)),
                    "policy_frozen": False,
                }
            )
        )
    except CalibrationError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
