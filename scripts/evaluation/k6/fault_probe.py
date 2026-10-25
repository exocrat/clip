"""Explicit local k6 fault checks; no database/model/cloud/auth dependency.

Short fixture profiles stay inside approved pilot caps. These HTTP scripts prove
failure accounting only, never endpoint functionality or search relevance.
"""

from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

from scripts.evaluation.k6.install import ROOT
from scripts.evaluation.k6.runner import execute


def run() -> Path:
    """Start/stop owned ephemeral loopback fixtures and preserve invalid-run evidence."""
    directory = (
        ROOT / ".tools/k6/fault-checks" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    directory.mkdir(parents=True)
    base = json.loads(
        (ROOT / "data/evaluation/workloads/local-search-pilot-v1.json").read_text()
    )
    outcomes = []
    for kind in ("wrong-response", "unauthorized", "timeout", "shortfall"):
        profile = {
            **base,
            "id": f"fault-{kind}",
            "warmup_seconds": 0,
            "measured_seconds": 2,
            "timeout_seconds": 2 if kind == "shortfall" else 0.25,
            "max_vus": 1 if kind == "shortfall" else 2,
            "cases": [base["cases"][0]],
        }
        profile_path = directory / f"{kind}.json"
        profile_path.write_text(json.dumps(profile))
        row = {
            "listing_id": base["cases"][0]["expected_ids"][0],
            "title": "Controlled bicycle",
            "description": "Synthetic transport fixture",
            "category_code": "bicycles",
            "category_label": "Bicycles",
            "condition_code": "good",
            "condition_label": "Good",
            "asking_price_paise": 0,
            "negotiable": False,
            "pickup_area": None,
            "available_from": "2026-01-01T00:00:00.000000Z",
            "available_until": None,
            "availability": "available",
            "sensitive_purchase": False,
            "image_ids": [],
        }

        class Handler(BaseHTTPRequestHandler):
            """Fixed non-personal outcomes; never implement search, identity or auth."""

            def do_GET(self):
                if kind == "timeout":
                    time.sleep(0.7)
                elif kind == "shortfall":
                    time.sleep(1.1)
                status = 401 if kind == "unauthorized" else 200
                data = (
                    {
                        "error": {
                            "code": "unauthenticated",
                            "message": "Synthetic failure",
                        }
                    }
                    if status == 401
                    else {
                        "items": [] if kind == "wrong-response" else [row],
                        "page": 1,
                        "page_size": 20,
                        "has_next": False,
                    }
                )
                payload = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "private, no-store")
                self.send_header("X-Clip-Preview", "search-load-fault-fixtures")
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except BrokenPipeError, ConnectionResetError:
                    pass

            def log_message(self, *_args):
                """No request/response data or query text is logged by fixtures."""

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = execute(
                profile_path,
                server.server_port,
                directory / kind,
                target_kind="fault-fixtures",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            assert not thread.is_alive()
        assert not result["valid_preparation_run"] and not result["nfr_accepted"]
        measured = result["measured"]
        if kind == "shortfall":
            assert (
                measured["generator_drops"] > 0 and measured["generator_shortfall"] > 0
            )
            assert (
                measured["outcomes"].get("ok", 0) > 0
                and measured["outcomes"].get("timeout", 0) == 0
            )
        else:
            outcome = {
                "wrong-response": "invalid",
                "unauthorized": "unauthorized",
                "timeout": "timeout",
            }[kind]
            assert measured["outcomes"].get(outcome, 0) > 0, result
        outcomes.append({"fixture": kind, "detected": True, "measured": measured})
    (directory / "result.json").write_text(
        json.dumps(
            {
                "preview_only": True,
                "nfr_accepted": False,
                "failure_checks_passed": True,
                "cases": outcomes,
            },
            indent=2,
        )
        + "\n"
    )
    return directory


if __name__ == "__main__":
    print(run())
