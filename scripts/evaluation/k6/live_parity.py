"""Capture bounded authenticated deployed read checks, then compare A/B receipts.

The two configurations may be deployed sequentially. Only canonical response
hashes and correctness decisions leave memory. Search equality establishes
response parity; NFR-04 independently measures relevance.
"""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import stat
import time
from pathlib import Path
import ssl
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import (
    Request,
    build_opener,
    HTTPSHandler,
    ProxyHandler,
    HTTPRedirectHandler,
)
from scripts.evaluation.k6.real_target_preflight import (
    validate_plan,
    inspect_target,
    check_session_identity,
)

ROOT = Path(__file__).resolve().parents[3]


class NoRedirect(HTTPRedirectHandler):
    """Keep sessions on the exact reviewed HTTPS target."""

    def redirect_request(
        self, req: Any, fp: Any, code: Any, msg: Any, headers: Any, newurl: Any
    ) -> None:
        return None


def read_bound(path: str, digest: str) -> Any:
    """Read a bounded repository input and verify its approved bytes."""
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe_input_path")
    source = ROOT / relative
    if (
        source.is_symlink()
        or not source.resolve().is_relative_to(ROOT)
        or source.stat().st_size > 5_000_000
    ):
        raise ValueError("unsafe_input_file")
    for parent in (source, *source.parents):
        if parent == ROOT:
            break
        if parent.is_symlink():
            raise ValueError("symlink_input")
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 5_000_000:
            raise ValueError("unsafe_input_file")
        raw = os.read(descriptor, 5_000_001)
    finally:
        os.close(descriptor)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("input_hash_mismatch")
    return json.loads(raw)


def bridge(cases: list[Any], responses: list[Any] | None = None) -> Any:
    """Reuse the existing contract/correctness checks without storing bodies."""
    payload: dict[str, Any] = {"cases": cases}
    if responses is not None:
        payload["responses"] = responses
    result = subprocess.run(
        ["node", str(ROOT / "scripts/evaluation/k6/live_parity_check.mjs")],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        raise ValueError("parity_cases_or_response_invalid")
    return json.loads(result.stdout)


def fetch(origin: str, path: str, cookie: str | None) -> dict[str, Any]:
    """One bounded GET without retries, redirects, proxies or body logging."""
    headers = {"Accept": "application/json", "Cache-Control": "no-cache"}
    if cookie:
        headers["Cookie"] = cookie
    opener = build_opener(
        ProxyHandler({}),
        NoRedirect(),
        HTTPSHandler(context=ssl.create_default_context()),
    )
    try:
        try:
            response = opener.open(Request(origin + path, headers=headers), timeout=5)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                return {"status": response.code, "body": None}
            try:
                body = json.loads(raw)
            except ValueError, UnicodeDecodeError:
                body = None
            return {"status": response.code, "body": body}
    except URLError, TimeoutError, OSError:
        return {"status": 0, "body": None}


def capture(
    manifest: dict[str, Any], approval: dict[str, Any], manifest_hash: str, cookie: str
) -> dict[str, Any]:
    """Validate exact approval and local cases before target/session/network use."""
    if (
        set(manifest)
        != {
            "format_version",
            "run_id",
            "configuration",
            "target_plan_path",
            "target_plan_sha256",
            "corpus_path",
            "corpus_sha256",
            "hidden_listing_id",
        }
        or manifest["format_version"] != 1
    ):
        raise ValueError("invalid_smoke_manifest")

    if not isinstance(manifest["hidden_listing_id"], str) or not re.fullmatch(
        r"[0-9a-f-]{36}", manifest["hidden_listing_id"]
    ):
        raise ValueError("hidden_listing_fixture_required")
    if (
        set(approval)
        != {"action", "manifest_sha256", "authorized_at", "expires_at", "review_record"}
        or approval["action"] != "capture_live_parity"
        or approval["manifest_sha256"] != manifest_hash
        or not isinstance(approval["review_record"], str)
        or not approval["review_record"].strip()
        or not isinstance(approval["authorized_at"], str)
        or not isinstance(approval["expires_at"], str)
    ):
        raise ValueError("exact_smoke_approval_required")
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(approval["authorized_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(approval["expires_at"].replace("Z", "+00:00"))
    if start.tzinfo is None or end.tzinfo is None or not start <= now < end:
        raise ValueError("smoke_approval_expired")
    target = validate_plan(
        read_bound(manifest["target_plan_path"], manifest["target_plan_sha256"])
    )
    if (
        target["run_id"] != manifest["run_id"]
        or target["configuration"] != manifest["configuration"]
    ):
        raise ValueError("smoke_target_mismatch")
    corpus = read_bound(manifest["corpus_path"], manifest["corpus_sha256"])
    cases = corpus["cases"]
    paths = bridge(cases)["paths"]
    if len({c["case_id"] for c in cases}) != 10:
        raise ValueError("duplicate_cases")
    inspect_target(target)
    check_session_identity(target, cookie)
    responses = []
    request_timings_ms = []
    for path in paths:
        started = time.monotonic_ns()
        responses.append(fetch(target["api_origin"], "/api" + path, cookie))
        request_timings_ms.append((time.monotonic_ns() - started) / 1_000_000)
    checked = bridge(cases, responses)["cases"]
    negative = [
        fetch(target["api_origin"], "/api" + paths[0], None)["status"],
        fetch(
            target["api_origin"],
            "/api/listings/" + manifest["hidden_listing_id"],
            cookie,
        )["status"],
    ]
    return {
        "format_version": 1,
        "run_id": target["run_id"],
        "configuration": target["configuration"],
        "manifest_sha256": manifest_hash,
        "corpus_sha256": manifest["corpus_sha256"],
        "target_plan_sha256": manifest["target_plan_sha256"],
        "revisions": target["revisions"],
        "observed_at_utc": now.isoformat(),
        "cases": checked,
        "request_timings_ms": request_timings_ms,
        "timing_boundary": "monotonic before HTTP call through full body read",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "anonymous_status": negative[0],
        "hidden_status": negative[1],
        "hidden_listing_id_sha256": hashlib.sha256(
            manifest["hidden_listing_id"].encode()
        ).hexdigest(),
        "smoke_passed": all(c["correct"] for c in checked) and negative == [401, 404],
        "backend_attribution": "target-plan and aggregate telemetry require separate review",
        "measurement_authorized": False,
    }


def compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Require both successful captures and the same reviewed cases/revisions."""
    same_revisions = all(
        a["revisions"][key] == b["revisions"][key]
        for key in (
            "application_revision",
            "dataset_fingerprint",
            "model_revision",
            "ecs_image_uri",
        )
    )
    for receipt in (a, b):
        cases = receipt.get("cases")
        if (
            not isinstance(cases, list)
            or len(cases) != 10
            or len({item["case_id"] for item in cases}) != 10
            or any(
                item.get("correct") is not True or item.get("status") != 200
                for item in cases
            )
            or receipt.get("anonymous_status") != 401
            or receipt.get("hidden_status") != 404
        ):
            return {
                "response_parity_passed": False,
                "reason": "incomplete_or_failed_capture",
                "measurement_authorized": False,
            }
    matched = a["cases"] == b["cases"]
    passed = (
        a["configuration"] == "A"
        and b["configuration"] == "B"
        and a["smoke_passed"] is True
        and b["smoke_passed"] is True
        and a["corpus_sha256"] == b["corpus_sha256"]
        and a["hidden_listing_id_sha256"] == b["hidden_listing_id_sha256"]
        and same_revisions
        and matched
    )
    return {
        "response_parity_passed": passed,
        "a_run_id": a["run_id"],
        "b_run_id": b["run_id"],
        "same_revisions": same_revisions,
        "all_case_results_equal": matched,
        "routing_telemetry_review_required": True,
        "measurement_authorized": False,
    }


def main() -> None:
    """Capture one approved target or compare two immutable sanitized receipts."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture")
    cap.add_argument("manifest", type=Path)
    cap.add_argument("approval", type=Path)
    cap.add_argument("--execute", action="store_true", required=True)
    cap.add_argument("--output", type=Path, required=True)
    pair = sub.add_parser("compare")
    pair.add_argument("a", type=Path)
    pair.add_argument("b", type=Path)
    pair.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("output_must_be_new")
        if args.command == "capture":
            raw = args.manifest.read_bytes()
            result = capture(
                json.loads(raw),
                json.loads(args.approval.read_bytes()),
                hashlib.sha256(raw).hexdigest(),
                os.environ.get("CLIP_SMOKE_SESSION", ""),
            )
        else:
            a_bytes, b_bytes = args.a.read_bytes(), args.b.read_bytes()
            result = compare(json.loads(a_bytes), json.loads(b_bytes))
            result["a_receipt_sha256"] = hashlib.sha256(a_bytes).hexdigest()
            result["b_receipt_sha256"] = hashlib.sha256(b_bytes).hexdigest()
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump(result, output, sort_keys=True, indent=2)
            output.write("\n")
        if not result.get("smoke_passed", result.get("response_parity_passed", False)):
            parser.exit(2, "Live parity failed; receipt preserved\n")
    except OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError:
        parser.exit(2, "Live parity inputs or execution failed\n")


if __name__ == "__main__":
    main()
