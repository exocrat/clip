"""Connect the existing reviewed-label scorer to an injected real search adapter.

The adapter keeps query text in memory, accepts only ordered public listing IDs,
and emits sanitized per-query results. It does not establish human acceptance.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from uuid import UUID

from scripts.evaluation.search import (
    DatasetBinding,
    EvaluationCase,
    Retrieval,
    score_preview,
    validate_labels,
)
from scripts.evaluation.k6.real_target_preflight import (
    check_session_identity,
    inspect_target,
    validate_plan as validate_target_plan,
)

SearchFetch = Callable[[str, Mapping[str, Any]], tuple[int, Any]]
ROOT = Path(__file__).resolve().parents[2]
COOKIE_PATTERN = re.compile(r"__Host-clip_session=[A-Za-z0-9._~+/=-]{1,2048}\Z")
MAX_RESPONSE_BYTES = 2_000_000
MANIFEST_KEYS = {
    "status",
    "nfr_id",
    "run_id",
    "configuration",
    "human_approved_at",
    "execution_permitted",
    "nfr_accepted",
    "dataset_fingerprint",
    "schema_revision",
    "application_revision",
    "search_contract_revision",
    "model_revision",
    "labels_path",
    "labels_sha256",
    "included_query_count",
    "target_origin",
    "api_base_url",
    "session_secret_reference",
    "retrieval_source",
    "target_plan_path",
    "target_plan_sha256",
    "first_page_size",
    "scored_positions",
    "success_rule",
    "failure_and_timeout_denominator",
    "evidence_path",
    "human_review",
}
APPROVAL_KEYS = {
    "format_version",
    "action",
    "run_id",
    "configuration",
    "manifest_sha256",
    "authorized_at",
    "expires_at",
    "review_record",
}


def _page_ids(status: int, body: Any) -> tuple[UUID, ...]:
    """Validate a complete public search page and retain IDs only."""
    if (
        status != 200
        or not isinstance(body, dict)
        or set(body) != {"items", "page", "page_size", "has_next"}
    ):
        raise ValueError("invalid_search_page")
    if (
        body["page"] != 1
        or body["page_size"] != 20
        or type(body["has_next"]) is not bool
    ):
        raise ValueError("invalid_search_page")
    items = body["items"]
    if not isinstance(items, list) or len(items) > 20:
        raise ValueError("invalid_search_page")
    ids = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("listing_id"), str):
            raise ValueError("invalid_search_page")
        try:
            ids.append(UUID(item["listing_id"]))
        except ValueError, TypeError, AttributeError:
            raise ValueError("invalid_search_page") from None
    if len(set(ids)) != len(ids):
        raise ValueError("invalid_search_page")
    return tuple(ids)


def evaluate_retrieval(
    labels_document: Any,
    binding: DatasetBinding,
    fetch: SearchFetch,
    *,
    labels_sha256: str,
    model_revision: str,
    application_revision: str,
    source_kind: str,
) -> dict[str, Any]:
    """Fetch every included reviewed query, then apply the canonical Success@5 scorer.

    `fetch` is a narrow transport seam for a fake service in local preparation
    or the authenticated HTTP adapter in a separately approved deployed run.
    Exceptions are reduced to fixed outcome categories and never expose text.
    """
    for value in (labels_sha256,):
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("invalid_labels_hash")
    for value in (model_revision, application_revision):
        if not isinstance(value, str) or not value or len(value) > 128:
            raise ValueError("invalid_revision")
    if source_kind not in {"local_fixture", "deployed_authenticated"}:
        raise ValueError("invalid_retrieval_source")
    # Reviewed labels require a real, non-preview binding; the validator's
    # binding checks enforce that boundary without a separate mode flag.
    cases = validate_labels(labels_document, binding)
    label_rows = {UUID(row["query_id"]): row for row in labels_document["queries"]}
    results: dict[UUID, Retrieval] = {}
    fetch_errors = 0
    for case in cases:
        if not case.included:
            continue
        row = label_rows[case.query_id]
        try:
            status, body = fetch(row["query_text"], row["context"])
            if status in {401, 403}:
                results[case.query_id] = Retrieval(status="unauthorized")
                fetch_errors += 1
                continue
            if status == 429:
                results[case.query_id] = Retrieval(status="throttled")
                fetch_errors += 1
                continue
            if status in {408, 504}:
                results[case.query_id] = Retrieval(status="timeout")
                fetch_errors += 1
                continue
            ids = _page_ids(status, body)
            if not set(ids).issubset(binding.eligible_ids[case.query_id]):
                raise ValueError("ineligible_search_result")
            results[case.query_id] = Retrieval(ids, "ok")
        except TimeoutError:
            results[case.query_id] = Retrieval(status="timeout")
            fetch_errors += 1
        except PermissionError:
            results[case.query_id] = Retrieval(status="unauthorized")
            fetch_errors += 1
        except Exception:
            results[case.query_id] = Retrieval(status="error")
            fetch_errors += 1
    report = score_preview(cases, results, binding.listing_ids)
    return {
        **report,
        "nfr04_accepted": False,
        "execution_permitted": False,
        "source_kind": source_kind,
        "retrieval_failures": fetch_errors,
        "dataset_fingerprint": binding.logical_data_fingerprint,
        "schema_version": binding.schema_version,
        "application_revision": application_revision,
        "search_contract_revision": binding.search_contract_revision,
        "search_source_revision": binding.source_revision,
        "model_revision": model_revision,
        "labels_sha256": labels_sha256,
        "included_query_count": sum(case.included for case in cases),
    }


def labels_digest(raw_labels: bytes) -> str:
    """Return the source-byte digest without copying label/query content to a report."""
    return hashlib.sha256(raw_labels).hexdigest()


def _read_private_input(path: Path, maximum: int, code: str) -> bytes:
    """Read a bounded regular input without following symlinks or FIFOs."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError(code)
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise ValueError(code)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _new_report_path(path: Path, expected: Path) -> Path:
    """Require the exact absent evidence leaf and a symlink-free repository path."""
    candidate = path if path.is_absolute() else ROOT / path
    target = expected if expected.is_absolute() else ROOT / expected
    if candidate != target or not candidate.is_relative_to(ROOT):
        raise ValueError("nfr04_output_path_mismatch")
    current = ROOT
    for part in candidate.relative_to(ROOT).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("nfr04_output_path_symlink")
    if (
        not candidate.parent.resolve(strict=True).is_relative_to(ROOT.resolve())
        or candidate.exists()
    ):
        raise ValueError("nfr04_output_path_unavailable")
    return candidate


def write_new_report(path: Any, report: Mapping[str, Any]) -> None:
    """Create a separate sanitized report without overwriting prior evidence."""
    payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("nfr04_report_write_failed")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path, 0o400)


def _utc(value: Any, name: str) -> datetime:
    """Parse one explicit timezone-qualified approval timestamp."""
    if not isinstance(value, str):
        raise ValueError(f"invalid_{name}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"invalid_{name}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"invalid_{name}")
    return parsed.astimezone(timezone.utc)


def validate_execution_approval(
    manifest: Mapping[str, Any], manifest_bytes: bytes, approval: Any
) -> None:
    """Bind a separate, expiring action record to this exact NFR-04 plan."""
    if not isinstance(approval, dict) or set(approval) != APPROVAL_KEYS:
        raise ValueError("invalid_nfr04_action_approval")
    if (
        approval["format_version"] != 1
        or type(approval["format_version"]) is not int
        or approval["action"] != "retrieve_nfr04"
        or approval["run_id"] != manifest.get("run_id")
        or approval["configuration"] != manifest.get("configuration")
        or approval["manifest_sha256"] != hashlib.sha256(manifest_bytes).hexdigest()
    ):
        raise ValueError("nfr04_approval_binding_mismatch")
    if (
        not isinstance(approval["review_record"], str)
        or not approval["review_record"].strip()
    ):
        raise ValueError("nfr04_review_record_required")
    authorized = _utc(approval["authorized_at"], "approval_time")
    expires = _utc(approval["expires_at"], "approval_expiry")
    now = datetime.now(timezone.utc)
    if authorized > now or expires <= now or expires <= authorized:
        raise ValueError("nfr04_approval_expired_or_misordered")


def validate_manifest(value: Any) -> None:
    """Require the exact NFR-04 schema and its fixed Success@5 procedure."""
    if not isinstance(value, dict) or set(value) != MANIFEST_KEYS:
        raise ValueError("invalid_nfr04_manifest_shape")
    if (
        value["status"] != "approved-executable"
        or value["nfr_id"] != "nfr-04"
        or value["execution_permitted"] is not True
        or value["nfr_accepted"] is not False
        or value["configuration"] not in {"A", "B"}
        or not isinstance(value["run_id"], str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", value["run_id"])
        or value["labels_path"] != "data/evaluation/query-labels.json"
        or value["first_page_size"] != 20
        or type(value["first_page_size"]) is not int
        or value["scored_positions"] != 5
        or type(value["scored_positions"]) is not int
        or value["success_rule"]
        != "at least one human-labeled relevant listing among the first five"
        or value["failure_and_timeout_denominator"] != "all included reviewed queries"
        or value["retrieval_source"] != "deployed_authenticated"
        or value["session_secret_reference"] != "CLIP_NFR04_SESSION_COOKIE"
        or not isinstance(value["target_plan_path"], str)
        or not value["target_plan_path"]
        or not isinstance(value["target_plan_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", value["target_plan_sha256"])
        or not isinstance(value["human_review"], str)
        or not value["human_review"].strip()
        or not isinstance(value["evidence_path"], str)
        or not value["evidence_path"].strip()
    ):
        raise ValueError("invalid_nfr04_manifest_values")
    _utc(value["human_approved_at"], "human_approval_time")
    for key in ("dataset_fingerprint", "labels_sha256"):
        if not isinstance(value[key], str) or not re.fullmatch(
            r"(?:sha256:)?[0-9a-f]{64}", value[key]
        ):
            raise ValueError("invalid_nfr04_fingerprint")
    for key in ("application_revision", "model_revision"):
        if not isinstance(value[key], str) or not re.fullmatch(
            r"[0-9a-f]{40,64}", value[key]
        ):
            raise ValueError("invalid_nfr04_revision")
    for key in ("schema_revision", "search_contract_revision"):
        if not isinstance(value[key], str) or not value[key]:
            raise ValueError("invalid_nfr04_revision")
    if (
        type(value["included_query_count"]) is not int
        or value["included_query_count"] < 20
    ):
        raise ValueError("invalid_nfr04_query_count")
    origin = urlsplit(
        value["target_origin"] if isinstance(value["target_origin"], str) else ""
    )
    api = urlsplit(
        value["api_base_url"] if isinstance(value["api_base_url"], str) else ""
    )
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.username
        or origin.password
        or origin.path
        or origin.query
        or origin.fragment
        or api.scheme != "https"
        or api.netloc != origin.netloc
        or api.path != "/api"
        or api.query
        or api.fragment
        or api.username
        or api.password
    ):
        raise ValueError("nfr04_target_binding_mismatch")
    expected_evidence = (
        Path("docs/evaluation/nfr/nfr-04") / value["run_id"] / "report.json"
    )
    if Path(value["evidence_path"]) != expected_evidence:
        raise ValueError("invalid_nfr04_evidence_path")


class _NoRedirect(HTTPRedirectHandler):
    """Keep a redirected authenticated query from changing its approved target."""

    def redirect_request(
        self,
        request: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        new_url: str,
    ) -> Request | None:
        return None


def _real_fetcher(api_base_url: str, cookie: str) -> SearchFetch:
    """Create a bounded direct HTTPS reader; never follow redirects or log URLs."""
    parts = urlsplit(api_base_url)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.path != "/api"
        or parts.query
        or parts.fragment
    ):
        raise ValueError("invalid_api_base_url")
    opener = build_opener(
        ProxyHandler({}),
        _NoRedirect(),
        HTTPSHandler(context=ssl.create_default_context()),
    )

    def fetch(query_text: str, context: Mapping[str, Any]) -> tuple[int, Any]:
        params = {key: value for key, value in context.items() if value is not None}
        params.update(
            {
                "q": query_text,
                "search_mode": "hybrid",
                "sort": "relevance",
                "page": 1,
                "page_size": 20,
            }
        )
        base = urlsplit(api_base_url)
        url = urlunsplit(
            (
                base.scheme,
                base.netloc,
                f"{base.path}/listings",
                urlencode(params, doseq=True),
                "",
            )
        )
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Cookie": cookie,
                "Cache-Control": "no-cache",
            },
            method="GET",
        )
        try:
            with opener.open(request, timeout=5) as response:
                status = response.status
                if status != 200:
                    return status, None
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError("search_response_too_large")
                try:
                    return status, json.loads(raw)
                except UnicodeDecodeError, json.JSONDecodeError:
                    raise ValueError("invalid_search_response") from None
        except HTTPError as error:
            return error.code, None
        except TimeoutError, socket.timeout:
            raise TimeoutError from None
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                raise TimeoutError from None
            raise OSError("search_transport_failed") from None

    return fetch


def _read_target_plan(relative_path: Any, expected_hash: Any) -> dict[str, Any]:
    """Load and hash-check the repository target plan before AWS preflight."""
    if (
        not isinstance(relative_path, str)
        or not relative_path
        or Path(relative_path).is_absolute()
        or ".." in Path(relative_path).parts
        or not isinstance(expected_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
    ):
        raise ValueError("invalid_nfr04_target_plan_reference")
    path = ROOT / relative_path
    current = ROOT
    for part in Path(relative_path).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("nfr04_target_plan_symlink")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError("nfr04_target_plan_outside_repository")
    descriptor = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 100_000:
            raise ValueError("nfr04_target_plan_invalid_file")
        raw = os.read(descriptor, 100_001)
    finally:
        os.close(descriptor)
    if len(raw) > 100_000 or hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError("nfr04_target_plan_hash_mismatch")
    return validate_target_plan(json.loads(raw))


def main() -> int:
    """Run reviewed-label retrieval only with a human-approved exact manifest."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument(
        "--execute", action="store_true", help="run the explicitly approved retrieval"
    )
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest_bytes = _read_private_input(
            args.manifest, 100_000, "nfr04_manifest_too_large"
        )
        manifest = json.loads(manifest_bytes)
        validate_manifest(manifest)
        expected_output = ROOT / manifest["evidence_path"]
        selected_output = _new_report_path(args.output, expected_output)
        if not args.execute:
            raise ValueError("explicit_nfr04_execute_required")
        approval_bytes = _read_private_input(
            args.approval, 20_000, "nfr04_approval_too_large"
        )
        validate_execution_approval(
            manifest, manifest_bytes, json.loads(approval_bytes)
        )
        from scripts.evaluation.reference_labels import LABELS, materialize

        labels_path = ROOT / LABELS
        raw_labels = labels_path.read_bytes()
        labels = json.loads(raw_labels)
        expected_labels, _binding_evidence, binding = materialize(
            args.image_root
        )  # type: ignore[no-untyped-call]  # Legacy adapter has no public type contract.
        if json.dumps(labels, sort_keys=True, separators=(",", ":")) != json.dumps(
            expected_labels, sort_keys=True, separators=(",", ":")
        ):
            raise ValueError("reviewed_labels_binding_mismatch")
        label_hash = hashlib.sha256(raw_labels).hexdigest()
        if (
            manifest.get("labels_path") != LABELS
            or manifest.get("labels_sha256") != label_hash
        ):
            raise ValueError("nfr04_label_hash_mismatch")
        if (
            manifest.get("dataset_fingerprint") != binding.logical_data_fingerprint
            or manifest.get("schema_revision") != binding.schema_version
            or manifest.get("search_contract_revision")
            != binding.search_contract_revision
        ):
            raise ValueError("nfr04_data_or_contract_binding_mismatch")
        included = sum(row.get("include_in_nfr04") is True for row in labels["queries"])
        if manifest.get("included_query_count") != included or included < 20:
            raise ValueError("nfr04_included_query_count_mismatch")
        cookie = os.environ.get("CLIP_NFR04_SESSION_COOKIE", "")
        if not COOKIE_PATTERN.fullmatch(cookie):
            raise ValueError("nfr04_session_missing_or_invalid")
        target = _read_target_plan(
            manifest["target_plan_path"], manifest["target_plan_sha256"]
        )
        if (
            target["run_id"] != manifest["run_id"]
            or target["configuration"] != manifest["configuration"]
            or target["api_origin"] != manifest["target_origin"]
            or manifest["api_base_url"]
            != manifest["target_origin"].rstrip("/") + "/api"
            or target["revisions"]["application_revision"]
            != manifest["application_revision"]
            or target["revisions"]["dataset_fingerprint"].removeprefix("sha256:")
            != manifest["dataset_fingerprint"].removeprefix("sha256:")
            or target["revisions"]["model_revision"] != manifest["model_revision"]
        ):
            raise ValueError("nfr04_target_plan_binding_mismatch")
        inspect_target(target)
        check_session_identity(target, cookie, needs_csrf=False)
        app_revision = manifest.get("application_revision")
        model_revision = manifest.get("model_revision")
        if not isinstance(app_revision, str) or not re.fullmatch(
            r"[0-9a-f]{40}", app_revision
        ):
            raise ValueError("invalid_application_revision")
        if not isinstance(model_revision, str) or not re.fullmatch(
            r"[0-9a-f]{40,64}", model_revision
        ):
            raise ValueError("invalid_model_revision")
        target_origin = manifest.get("target_origin")
        api_base_url = manifest.get("api_base_url")
        if not isinstance(target_origin, str) or not isinstance(api_base_url, str):
            raise ValueError("nfr04_target_missing")
        origin = urlsplit(target_origin)
        api = urlsplit(api_base_url)
        if (
            origin.scheme != "https"
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.path
            or origin.query
            or origin.fragment
            or api.scheme != origin.scheme
            or api.netloc != origin.netloc
        ):
            raise ValueError("nfr04_target_binding_mismatch")
        fetch = _real_fetcher(api_base_url, cookie)
        report = evaluate_retrieval(
            labels,
            binding,
            fetch,
            labels_sha256=label_hash,
            model_revision=model_revision,
            application_revision=app_revision,
            source_kind="deployed_authenticated",
        )
        report["configuration"] = manifest["configuration"]
        report["run_id"] = manifest.get("run_id")
        report["target_origin"] = target_origin
        report["api_base_url"] = api_base_url
        write_new_report(args.output, report)
        print(
            json.dumps(
                {
                    "nfr_id": "nfr-04",
                    "configuration": manifest["configuration"],
                    "run_id": manifest.get("run_id"),
                    "included_queries": report["included_query_count"],
                    "retrieval_failures": report["retrieval_failures"],
                    "nfr04_accepted": False,
                    "report": str(args.output),
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as error:
        code = (
            str(error)
            if isinstance(error, ValueError)
            and re.fullmatch(r"[a-z_]{1,80}", str(error))
            else "invalid_input_or_retrieval_failure"
        )
        print(
            json.dumps(
                {"state": "nfr04_retrieval_failed", "code": code}, sort_keys=True
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
