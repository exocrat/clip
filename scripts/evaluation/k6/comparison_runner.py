"""Run a bounded k6 preparation against the local synthetic inspection app.

The inspection login issues a synthetic session through the real local Identity
routes. This runner keeps it in memory, accepts no external targets or cookies,
and checks responses against supplied expected cases without claiming performance
or independently reviewed final-reference evidence.
"""

import argparse
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SCENARIO = ROOT / "scripts/evaluation/k6/comparison_smoke.js"


def inspection_session(port: int) -> str:
    """Obtain the inspection launcher's synthetic buyer session without storing it."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request(
            "POST",
            "/__inspection/login/buyer",
            headers={"Origin": f"http://127.0.0.1:{port}"},
        )
        response = connection.getresponse()
        headers = response.getheaders()
        response.read()
        if response.status != 303:
            raise ValueError("Synthetic inspection login failed")
        cookies = [
            value.split(";", 1)[0]
            for key, value in headers
            if key.lower() == "set-cookie" and value.startswith("clip_session_dev=")
        ]
        if len(cookies) != 1 or not cookies[0].split("=", 1)[1]:
            raise ValueError("Synthetic session unavailable")
        return cookies[0]
    finally:
        connection.close()


def run(port: int, cases: list, binary: Path) -> dict:
    """Run at most ten local cases and return sanitized correctness outcomes."""
    if type(port) is not int or port not in (5174, 5175, 5176):
        raise ValueError("Use a documented inspection port")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 10:
        raise ValueError("Expected one to ten cases")
    encoded = json.dumps(cases, separators=(",", ":"))
    if len(encoded.encode()) > 16384:
        raise ValueError("Cases exceed input cap")
    if (
        not binary.is_absolute()
        or not binary.is_file()
        or not os.access(binary, os.X_OK)
    ):
        raise ValueError("An absolute executable k6 path is required")
    with tempfile.TemporaryDirectory(prefix="clip-comparison-smoke-") as directory:
        output = Path(directory) / "metrics.jsonl"
        config = Path(directory) / "config.json"
        config.write_text("{}\n")
        env = {
            "PATH": "/usr/bin:/bin",
            "K6_NO_USAGE_REPORT": "true",
            "CLIP_COMPARISON_LOCAL_TARGET": f"http://127.0.0.1:{port}/api",
            # Inspect executes scenario initialization only; the placeholder is
            # never sent and invalid cases fail before session creation.
            "CLIP_COMPARISON_LOCAL_COOKIE": "inspection-preflight-placeholder",
            "CLIP_COMPARISON_LOCAL_CASES": encoded,
        }
        preflight = subprocess.run(
            [
                str(binary),
                "inspect",
                "--include-system-env-vars",
                "--config",
                str(config),
                str(SCENARIO),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            timeout=15,
            check=False,
        )
        if preflight.returncode != 0:
            raise ValueError("Invalid scenario or cases")
        env["CLIP_COMPARISON_LOCAL_COOKIE"] = inspection_session(port)
        result = subprocess.run(
            [
                str(binary),
                "run",
                "--quiet",
                "--no-color",
                "--address",
                "",
                "--config",
                str(config),
                "--out",
                f"json={output}",
                str(SCENARIO),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            timeout=75,
            check=False,
        )
        if result.returncode != 0 or not output.is_file():
            raise ValueError("k6 preparation failed; no results accepted")
        if output.stat().st_size > 2_000_000:
            raise ValueError("k6 output exceeds local limit")
        statuses = {}
        outcomes = {}
        for line in output.read_text().splitlines():
            point = json.loads(line)
            if point.get("type") == "Point" and point.get("metric") == "http_reqs":
                tags = point["data"]["tags"]
                index = tags.get("case_index")
                if index in statuses:
                    raise ValueError("Duplicate case request")
                statuses[index] = {
                    "kind": tags.get("kind"),
                    "status": tags.get("status"),
                }
            if (
                point.get("type") == "Point"
                and point.get("metric") == "clip_comparison_preparation_response"
            ):
                tags = point["data"]["tags"]
                index = tags.get("case_index")
                if index in outcomes:
                    raise ValueError("Duplicate case outcome")
                outcomes[index] = {
                    "kind": tags.get("kind"),
                    "outcome": tags.get("outcome"),
                }
        expected_indices = {str(i) for i in range(len(cases))}
        if set(statuses) != expected_indices or set(outcomes) != expected_indices:
            raise ValueError("Incomplete request count")
        requests = []
        for i in range(len(cases)):
            status = statuses[str(i)]
            outcome = outcomes[str(i)]
            if status["kind"] != outcome["kind"] or outcome["outcome"] not in {
                "correct",
                "incorrect",
                "transport_error",
            }:
                raise ValueError("Invalid case outcome")
            requests.append({**status, "outcome": outcome["outcome"]})
        return {
            "measurement": False,
            "correct": all(item["outcome"] == "correct" for item in requests),
            "requests": requests,
        }


def main() -> int:
    """Read case JSON from stdin and print sanitized preparation outcomes only."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, type=int, choices=(5174, 5175, 5176))
    parser.add_argument("--k6", required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = sys.stdin.read(16385)
        if len(raw.encode()) > 16384:
            raise ValueError("Cases exceed input cap")
        result = run(args.port, json.loads(raw), args.k6)
        print(json.dumps(result))
        return 0 if result["correct"] else 1
    except OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError:
        print(
            "Local preparation failed; check inputs and inspection app", file=sys.stderr
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
