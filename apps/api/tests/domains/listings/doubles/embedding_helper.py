"""Test-only pipe fault injector. Never imported/selected by application code.

Synthetic coordinate vectors test frame handling, not model inference/relevance.
Only controlled test arguments choose faults; no production flag selects this.
"""

import json
import os
from pathlib import Path
import sys
import time

mode, pipeline_id, marker = sys.argv[1:4]


def send(value):
    """Flush a controlled test frame without source text or raw error messages."""
    print(json.dumps(value, separators=(",", ":")), flush=True)


ready = {
    "v": 1,
    "kind": "ready",
    "pipeline_id": pipeline_id,
    "pid": os.getpid(),
    "python_minor": "3.13",
    "runtime": {"numpy": "2.5.4", "onnxruntime": "1.23.2", "tokenizers": "0.23.3"},
    "threads": 1,
    "offline": True,
    "peak_rss_bytes": 1,
}
if mode == "startup_hang":
    time.sleep(60)
if mode == "wrong_ready":
    ready["pipeline_id"] = "0" * 64
send(ready)
for line in sys.stdin:
    request = json.loads(line)
    if mode == "crash_once" and not Path(marker).exists():
        Path(marker).touch()
        raise SystemExit(2)
    binding = {"v": 1, "request_id": request["request_id"], "pipeline_id": pipeline_id}
    if mode == "bad_json":
        print("{bad", flush=True)
        continue
    if mode == "duplicate":
        print('{"v":1,"v":1}', flush=True)
        continue
    if mode == "oversize":
        print("x" * (2 * 1024 * 1024 + 1), flush=True)
        continue
    kinds = (
        [("query", 0)]
        if request["operation"] == "query"
        else [("title", 0), ("description", 0)]
    )
    for kind, index in kinds:
        send(
            {
                **binding,
                "kind": "progress",
                "part_kind": kind,
                "ordinal": index,
                "peak_rss_bytes": 1,
            }
        )
    if mode == "error_timeout":
        send({**binding, "kind": "error", "code": "timeout"})
        continue
    if mode == "hang":
        time.sleep(60)
    if mode == "slow":
        time.sleep(0.1)
    value = {
        **binding,
        "kind": "result",
        "operation": request["operation"],
        "parts": [
            {"kind": kind, "ordinal": ordinal, "vector": [1.0] + [0.0] * 383}
            for kind, ordinal in kinds
        ],
        "title_tokens": None if request["operation"] == "query" else 1,
        "description_tokens": None if request["operation"] == "query" else 1,
        "query_tokens": 1 if request["operation"] == "query" else None,
        "ranges": [[0, 1]],
        "peak_rss_bytes": 1,
    }
    if mode == "wrong_id":
        value["request_id"] = "00000000-0000-4000-8000-000000000000"
    if mode == "private_extra":
        value["contact"] = "Synthetic forbidden extra"
    if mode == "nan":
        value["parts"][0]["vector"][0] = float("nan")
    if mode == "bad_coverage":
        value["ranges"] = [[0, 2]]
    if mode == "bool_coverage":
        value["ranges"] = [[False, True]]
    send(value)
