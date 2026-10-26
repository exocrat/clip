"""Bounded actual-model pipe probe; no DB/public API/global configuration changes.

Parent supervision reads only its own/owned-helper/explicit preview API PIDs.
Controlled inputs and aggregate metrics only; no source/vector payload is logged.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.domains.listings.embedding_client import SemanticHelper


def rss(pids):
    """Read only declared process identities; no process arguments or environment."""
    result = subprocess.run(
        [
            "/bin/ps",
            "-p",
            ",".join(str(pid) for pid in sorted(pids)),
            "-o",
            "pid=,ppid=,rss=",
        ],
        capture_output=True,
        text=True,
        timeout=2,
    )
    rows = {}
    for line in result.stdout.splitlines():
        pid, parent, size = map(int, line.split())
        rows[pid] = (parent, size * 1024)
    return rows


def dot(left, right):
    """Compare controlled actual vectors without introducing a retrieval engine."""
    return math.fsum(a * b for a, b in zip(left, right))


async def run(preview_pid):
    """Run <=30 windows/10min with RSS watchdog; preserve safe measurements only."""
    client = SemanticHelper(
        ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
    )
    owned = set()
    parent = os.getpid()
    peaks = 0
    simultaneous = 0
    faults = []
    stopped = False
    baseline = rss({parent, preview_pid})
    if parent not in baseline or preview_pid not in baseline:
        raise RuntimeError("Declared process unavailable")
    started = time.monotonic()

    async def monitor():
        """Enforce aggregate sampled512MiB and prevent overlapping owned helpers."""
        nonlocal peaks, simultaneous
        while not stopped:
            if client.pid is not None:
                owned.add(client.pid)
            rows = await asyncio.to_thread(rss, {parent, preview_pid, *owned})
            if parent not in rows or preview_pid not in rows:
                faults.append("process_missing")
                await client.close()
                return
            active = [pid for pid in owned if pid in rows and rows[pid][0] == parent]
            total = (
                rows[parent][1]
                + rows[preview_pid][1]
                + sum(rows[pid][1] for pid in active)
            )
            peaks = max(peaks, total)
            simultaneous = max(simultaneous, len(active))
            if (
                total >= 512 * 1024 * 1024
                or len(active) > 1
                or time.monotonic() - started > 600
            ):
                faults.append("resource_or_duration_bound")
                await client.close()
                return
            await asyncio.sleep(0.05)

    watchdog = asyncio.create_task(monitor())
    try:
        await client.start()
        if client.pid is not None:
            owned.add(client.pid)
        examples = (
            ("Campus bicycle", "A pedal powered bicycle for commuting around campus."),
            (
                "Calculus textbook",
                "A calculus textbook with worked exercises for university students.",
            ),
            (
                "Study desk",
                "A wooden desk and comfortable chair for studying in a room.",
            ),
        )
        listings = [
            await client.encode_listing(title, description)
            for title, description in examples
        ]
        cases = []
        durations = []
        for name, text, expected in (
            ("campus_transport", "something to ride to campus", 0),
            ("calculus_study", "study material for calculus", 1),
            ("study_furniture", "furniture for studying", 2),
        ):
            begin = time.monotonic()
            query = await client.encode_query(text)
            durations.append(time.monotonic() - begin)
            scores = [
                max(dot(query.vector, part.vector) for part in listing.parts)
                for listing in listings
            ]
            top = max(range(len(scores)), key=lambda index: (scores[index], -index))
            cases.append(
                {
                    "scenario": name,
                    "expected_fixture": expected,
                    "top_fixture": top,
                    "expected_top": top == expected,
                    "scores": scores,
                }
            )
        long = await client.encode_listing(
            "Controlled telescope", "ordinary filler " * 300 + " collectible telescope"
        )
        assert long.ranges[-1][1] == long.description_tokens and len(long.ranges) > 1
        first = await client.encode_query("something to ride to campus")
        parallel = await asyncio.gather(
            client.encode_query("something to ride to campus"),
            client.encode_query("study material for calculus"),
        )
        assert first.vector == parallel[0].vector and client.starts == 1
        old = client.pid
        assert old is not None
        # Fault injection targets only the exact child created/owned by this client.
        os.kill(old, signal.SIGKILL)
        async with asyncio.timeout(1):
            while client.pid == old:
                await asyncio.sleep(0.001)
        recovered = await client.encode_query("something to ride to campus")
        if client.pid is not None:
            owned.add(client.pid)
        assert (
            recovered.vector == first.vector
            and client.starts == 2
            and client.pid != old
        )
        assert client.windows_started <= 30
        if faults:
            raise RuntimeError("Watchdog rejected run")
        result = {
            "captured_at": datetime.now(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
            "preview_only": True,
            "nfr04_accepted": False,
            "human_review_verified": False,
            "controlled_cases": cases,
            "query_round_trip_seconds": durations,
            "long_description_tokens": long.description_tokens,
            "long_description_chunks": len(long.ranges),
            "full_token_coverage": True,
            "repeatability_exact": True,
            "concurrent_calls_serialized": True,
            "starts": client.starts,
            "windows_started": client.windows_started,
            "crash_recovery_same_vectors": True,
            "helper_peak_rss_bytes": client.helper_peak_rss_bytes,
        }
    finally:
        await client.close()
        stopped = True
        await watchdog
    remaining = rss({parent, preview_pid, *owned})
    assert all(pid not in remaining for pid in owned)
    assert not faults
    result.update(
        {
            "sampled_peak_combined_rss_bytes": peaks,
            "max_simultaneous_owned_helpers": simultaneous,
            "all_owned_helpers_reaped": True,
            "elapsed_seconds": time.monotonic() - started,
        }
    )
    folder = (
        ROOT
        / ".tools/semantic/ipc-probes"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "local_ipc_probe_complete",
                "windows": result["windows_started"],
                "helper_starts": result["starts"],
                "peak_combined_bytes": peaks,
                "run": str(folder.relative_to(ROOT)),
            }
        )
    )


def main():
    """Require explicit local-probe opt-in and an already identified preview PID."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated-helper-probe", action="store_true", required=True)
    parser.add_argument("--preview-api-pid", type=int, required=True)
    args = parser.parse_args()
    if args.preview_api_pid <= 0:
        parser.error("Expected explicitly identified PID")
    asyncio.run(asyncio.wait_for(run(args.preview_api_pid), 600))


if __name__ == "__main__":
    main()
