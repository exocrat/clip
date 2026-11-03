"""SE-01 strict label validation and Success@5 calculation preparation.

No final measurement command exists here yet. CLI checks draft labels or runs
synthetic arithmetic fixtures only. reference_labels.py supplies independently
verified actual dataset/context bindings; final scoring and native retrieval
remain at their original integration checkpoints.
No network, credentials, provider activation or database reads are performed.
"""

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Literal, Mapping
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.contracts.domain_types import ListingQuery  # noqa: E402
from app.core.identifiers import parse_id  # noqa: E402
from app.core.money import validate_paise  # noqa: E402
from app.core.timestamps import format_timestamp, parse_timestamp  # noqa: E402
from data.generators.files import _read_json  # noqa: E402
from data.generators.manifest import canonical_json  # noqa: E402
from data.generators.preview import stable_id  # noqa: E402


class EvaluationError(ValueError):
    """Carry only fixed diagnostic codes, never supplied data or private values."""


@dataclass(frozen=True)
class DatasetBinding:
    """Trusted adapter output, not evidence reconstructed from label claims.

    The actual integration adapter must verify manifest/content/counts/schema,
    accepted revisions and context eligibility before constructing this object.
    CLI deliberately has no way to construct one or claim final acceptance.
    """

    logical_data_fingerprint: str
    manifest_path: str
    schema_version: str
    source_revision: str
    search_contract_revision: str
    listing_ids: frozenset[UUID]
    eligible_ids: Mapping[UUID, frozenset[UUID]]
    preview_only: bool = True


@dataclass(frozen=True)
class EvaluationCase:
    """Frozen calculator input; synthetic cases are not human relevance judgments."""

    query_id: UUID
    relevant_ids: frozenset[UUID]
    included: bool
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class Retrieval:
    """First-page ordered IDs/status from a future real runner or explicit unit script."""

    listing_ids: tuple[UUID, ...] = ()
    status: Literal["ok", "timeout", "error", "unauthorized", "throttled"] = "ok"


def _require(condition: bool, code: str) -> None:
    """Raise a fixed safe diagnostic instead of echoing malformed file content."""
    if not condition:
        raise EvaluationError(code)


def _object(value: object, fields: set[str]) -> dict[str, Any]:
    """Enforce the existing format's exact key set without accepting private extras."""
    if not isinstance(value, dict) or set(value) != fields:
        raise EvaluationError("invalid_document_shape")
    return value


def _identifier(value: object) -> UUID:
    """Use the shared canonical UUIDv4 parser for query/listing references."""
    if not isinstance(value, str):
        raise EvaluationError("invalid_identifier")
    try:
        return parse_id(value)
    except ValueError, TypeError:
        raise EvaluationError("invalid_identifier") from None


def _text(value: object) -> bool:
    """Check nonblank metadata; syntactic text is never proof of human approval."""
    return isinstance(value, str) and bool(value.strip())


def safe_reference(value: str, *, labels: bool = False, exists: bool = False) -> Path:
    """Accept only repository-relative evidence paths, with no symlinks/traversal.

    Labels stay under data/evaluation. Manifest references stay under data/runs
    or docs/evaluation. Referenced manifests are not executed or loaded here.
    """
    _require(
        isinstance(value, str) and "\\" not in value and ":" not in value,
        "unsafe_reference",
    )
    parts = value.split("/")
    _require(all(part not in {"", ".", ".."} for part in parts), "unsafe_reference")
    allowed = ("data/evaluation/",) if labels else ("data/runs/", "docs/evaluation/")
    _require(value.startswith(allowed), "unsafe_reference")
    path = ROOT.joinpath(*parts)
    _require(path.resolve() == path, "unsafe_reference")
    if exists:
        _require(path.is_file(), "referenced_file_missing")
    return path


def _context(value: object, query_text: str) -> None:
    """Check actual public query fields; real eligibility/policy approval is external.

    Identity/actor/token fields are not HTTP query inputs. Empty/default contexts
    still require the separately reviewed inclusion/run policy before scoring.
    First-five evaluation always uses the first page, never a later offset.
    """
    if not isinstance(value, dict):
        raise EvaluationError("invalid_context")
    _require(set(value).issubset(ListingQuery.model_fields), "invalid_context")
    for name in ("min_price_paise", "max_price_paise"):
        if value.get(name) is not None:
            try:
                validate_paise(value[name])
            except ValueError, TypeError:
                raise EvaluationError("invalid_context") from None
    for name in ("page", "page_size"):
        if name in value:
            _require(type(value[name]) is int, "invalid_context")
    if "negotiable" in value and value["negotiable"] is not None:
        _require(type(value["negotiable"]) is bool, "invalid_context")
    try:
        # Apply the public trim-before-limit rule without importing another
        # domain's private HTTP validator. Preserve the supplied context object.
        normalized = dict(value)
        if isinstance(normalized.get("q"), str):
            normalized["q"] = normalized["q"].strip() or None
        query = ListingQuery.model_validate(normalized)
    except ValueError:
        raise EvaluationError("invalid_context") from None
    _require(query.page == 1, "first_page_required")
    _require(
        query.q is None or query.q.strip() == query_text.strip(),
        "conflicting_query_text",
    )
    _require(
        query.min_price_paise is None
        or query.max_price_paise is None
        or query.min_price_paise <= query.max_price_paise,
        "invalid_context",
    )


def validate_labels(
    document: dict[str, Any], binding: DatasetBinding | None = None
) -> tuple[EvaluationCase, ...]:
    """Validate canonical label format and binding, without attesting human review.

    Draft rows must keep judgments/inclusion null; they cannot be scored.
    Reviewed rows require a trusted final-data/context binding, at least twenty
    included cases and completed metadata. Valid metadata still is not approval.
    """
    doc = _object(
        document,
        {
            "format_version",
            "status",
            "dataset",
            "search_contract_revision",
            "review",
            "queries",
        },
    )
    _require(
        doc["format_version"] == "1" and doc["status"] in {"draft", "reviewed"},
        "unsupported_label_format",
    )
    dataset = _object(
        doc["dataset"],
        {
            "logical_data_fingerprint",
            "manifest_path",
            "schema_version",
            "source_revision",
        },
    )
    review = _object(doc["review"], {"reviewer", "reviewed_at", "inclusion_policy"})
    _require(isinstance(doc["queries"], list), "invalid_queries")
    draft = doc["status"] == "draft"
    if draft:
        _require(
            all(value is None for value in dataset.values())
            and all(value is None for value in review.values())
            and doc["search_contract_revision"] is None,
            "draft_metadata_must_remain_unreviewed",
        )
    else:
        _require(
            all(_text(value) for value in dataset.values())
            and all(_text(value) for value in review.values()),
            "review_metadata_incomplete",
        )
        _require(
            bool(
                re.fullmatch(
                    r"sha256:[0-9a-f]{64}", dataset["logical_data_fingerprint"]
                )
            ),
            "invalid_dataset_fingerprint",
        )
        for revision in (dataset["source_revision"], doc["search_contract_revision"]):
            _require(
                isinstance(revision, str)
                and bool(re.fullmatch(r"[0-9a-f]{40}", revision)),
                "invalid_revision",
            )
        try:
            _require(
                format_timestamp(parse_timestamp(review["reviewed_at"]))
                == review["reviewed_at"],
                "invalid_review_time",
            )
        except ValueError, TypeError:
            raise EvaluationError("invalid_review_time") from None
        safe_reference(dataset["manifest_path"])
        _require(
            binding is not None and not binding.preview_only,
            "final_dataset_binding_required",
        )
        assert binding is not None
        _require(
            "preview" not in dataset["schema_version"].lower(),
            "preview_dataset_not_final",
        )
        _require(
            all(dataset[key] == getattr(binding, key) for key in dataset)
            and doc["search_contract_revision"] == binding.search_contract_revision,
            "dataset_or_contract_mismatch",
        )
        safe_reference(binding.manifest_path, exists=True)
    seen: set[UUID] = set()
    cases = []
    for value in doc["queries"]:
        row = _object(
            value,
            {
                "query_id",
                "query_text",
                "context",
                "relevant_listing_ids",
                "include_in_nfr04",
                "exclusion_reason",
            },
        )
        query_id = _identifier(row["query_id"])
        _require(query_id not in seen, "duplicate_query_id")
        seen.add(query_id)
        _require(
            _text(row["query_text"]) and len(row["query_text"].strip()) <= 120,
            "invalid_query_text",
        )
        _context(row["context"], row["query_text"])
        if draft:
            _require(
                row["relevant_listing_ids"] is None
                and row["include_in_nfr04"] is None
                and row["exclusion_reason"] is None,
                "draft_judgments_unreviewed",
            )
            continue
        relevant = row["relevant_listing_ids"]
        _require(
            isinstance(relevant, list) and type(row["include_in_nfr04"]) is bool,
            "review_incomplete",
        )
        ids = [_identifier(item) for item in relevant]
        _require(len(set(ids)) == len(ids), "duplicate_relevant_id")
        assert binding is not None
        _require(
            query_id in binding.eligible_ids
            and set(ids).issubset(binding.listing_ids)
            and set(ids).issubset(binding.eligible_ids[query_id]),
            "relevance_reference_not_eligible",
        )
        included = row["include_in_nfr04"]
        reason = row["exclusion_reason"]
        _require(
            (included and reason is None) or (not included and _text(reason)),
            "invalid_exclusion",
        )
        cases.append(EvaluationCase(query_id, frozenset(ids), included, reason))
    if not draft:
        _require(
            sum(case.included for case in cases) >= 20,
            "twenty_included_queries_required",
        )
    return tuple(cases)


def score_preview(
    cases: tuple[EvaluationCase, ...],
    results: Mapping[UUID, Retrieval],
    corpus_ids: frozenset[UUID],
) -> dict[str, Any]:
    """Calculate Success@5 with explicit failures/exclusions; always preview-only.

    Every included case stays in the denominator, including empty relevance sets,
    missing results and failed/invalid retrieval. Only the first five ordered IDs
    can hit. Duplicate/unknown/oversized result pages are failures, never scores
    hidden by dropping a query. No matching/ranking engine is implemented here.
    """
    query_ids = {case.query_id for case in cases}
    _require(
        len(query_ids) == len(cases) and set(results).issubset(query_ids),
        "query_result_mismatch",
    )
    _require(
        all(case.relevant_ids.issubset(corpus_ids) for case in cases),
        "unknown_relevant_listing",
    )
    rows: list[dict[str, Any]] = []
    hits = failures = included = 0
    for case in cases:
        if not case.included:
            _require(_text(case.exclusion_reason), "invalid_exclusion")
            rows.append(
                {
                    "query_id": str(case.query_id),
                    "outcome": "excluded",
                    "reason": case.exclusion_reason,
                }
            )
            continue
        _require(case.exclusion_reason is None, "invalid_exclusion")
        included += 1
        result = results.get(case.query_id)
        outcome: str = "missing" if result is None else result.status
        valid = result is not None and result.status == "ok"
        if valid and result is not None:
            valid = (
                len(result.listing_ids) <= 100
                and len(set(result.listing_ids)) == len(result.listing_ids)
                and set(result.listing_ids).issubset(corpus_ids)
            )
            if not valid:
                outcome = "invalid"
        top = result.listing_ids[:5] if valid and result is not None else ()
        hit = bool(case.relevant_ids.intersection(top))
        hits += hit
        failures += not valid
        rows.append(
            {
                "query_id": str(case.query_id),
                "outcome": ("hit" if hit else "miss") if valid else outcome,
                "hit_at_5": hit,
                "top_five_listing_ids": [str(item) for item in top],
            }
        )
    _require(included > 0, "no_included_queries")
    return {
        "preview_only": True,
        "nfr04_accepted": False,
        "human_review_verified": False,
        "included_queries": included,
        "hits_at_5": hits,
        "success_at_5": hits / included,
        "fixture_target_met": hits * 5 >= included * 4,
        "retrieval_failures": failures,
        "queries": rows,
    }


def self_check() -> dict[str, Any]:
    """Exercise arithmetic with synthetic judgments, never a labeled corpus/run."""
    query_ids = [
        UUID(stable_id(91001, "listing_placeholder", index)) for index in range(1, 6)
    ]
    listing_ids = tuple(
        UUID(stable_id(91002, "listing_placeholder", index)) for index in range(1, 7)
    )
    cases = tuple(
        EvaluationCase(
            query_ids[index],
            frozenset({listing_ids[-1]}) if index != 2 else frozenset(),
            index != 4,
            "Synthetic excluded fixture" if index == 4 else None,
        )
        for index in range(5)
    )
    results = {
        query_ids[0]: Retrieval((listing_ids[-1],)),
        query_ids[1]: Retrieval(listing_ids),
        query_ids[2]: Retrieval(()),
        query_ids[3]: Retrieval(status="timeout"),
    }
    report = score_preview(cases, results, frozenset(listing_ids))
    _require(
        report["success_at_5"] == 0.25 and report["included_queries"] == 4,
        "self_check_failed",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    """Expose safe format/self-check commands; final scoring intentionally unavailable."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("validate-labels", "self-check"))
    parser.add_argument(
        "--labels", default="data/evaluation/query-labels.template.json"
    )
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        parser.error(
            "Unknown options; no target, credential or final-scoring mode exists"
        )
    try:
        if args.action == "self-check":
            report = self_check()
        else:
            path = safe_reference(args.labels, labels=True, exists=True)
            document = _read_json(path)
            validate_labels(document)
            report = {
                "format_valid": True,
                "label_status": document["status"],
                "scoring_allowed": False,
                "human_review_verified": False,
                "labels_fingerprint": "sha256:"
                + hashlib.sha256(canonical_json(document)).hexdigest(),
            }
        report["evaluator_fingerprint"] = (
            "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        )
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 0
    except EvaluationError, ValueError, OSError, TypeError:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "invalid_input_or_final_binding_missing",
                    "scoring_allowed": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
