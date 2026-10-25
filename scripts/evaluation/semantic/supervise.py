"""Supervise only the owned inference child with real memory/deadline ceilings.

Reads one explicitly identified preview API PID for aggregate local RSS. It never
signals that API or other existing processes. Run needs permission for `ps` on
this sandboxed Mac. No model/network work happens in the parent.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / ".tools/semantic"


def rss(pid):
    """Read resident KiB from the OS; refusal/missing PID is never counted as zero."""
    result = subprocess.run(
        ["/bin/ps", "-p", str(pid), "-o", "rss="],
        capture_output=True,
        text=True,
        timeout=2,
    )
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("Cannot verify process RSS")
    return int(result.stdout.strip()) * 1024


def main():
    """Bound a local probe; retain every run and stop only the owned child on failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-api-pid", type=int, required=True)
    args = parser.parse_args()
    if args.preview_api_pid <= 0:
        parser.error("Expected an explicitly identified positive API PID")
    baseline = rss(args.preview_api_pid)
    run = LOCAL / "probes" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir(parents=True, exist_ok=False)
    env = {
        "PATH": str(LOCAL / "venv/bin") + ":/usr/bin:/bin",
        "PYTHONNOUSERSITE": "1",
        "HF_HUB_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
    }
    # The fixed local helper needs no HOME, tokens, proxy settings or DB/AWS env.
    started = time.monotonic()
    peak = baseline
    status = "failed"
    reason = "incomplete"
    with (
        (run / "events.jsonl").open("w") as output,
        (run / "stderr.txt").open("w") as errors,
    ):
        child = subprocess.Popen(
            [
                str(LOCAL / "venv/bin/python"),
                str(ROOT / "scripts/evaluation/semantic/probe.py"),
            ],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=errors,
        )
        try:
            while child.poll() is None:
                try:
                    aggregate = rss(child.pid) + rss(args.preview_api_pid)
                except RuntimeError:
                    if child.poll() is not None:
                        break
                    raise
                peak = max(peak, aggregate)
                if aggregate >= 512 * 1024 * 1024:
                    raise RuntimeError("aggregate_rss_limit")
                now = time.monotonic()
                if now - started > 600:
                    raise RuntimeError("probe_duration_limit")
                phases = []
                for line in (run / "events.jsonl").read_text().splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if "phase" in event:
                        phases.append(event)
                phase = (
                    phases[-1] if phases else {"phase": "startup", "started": started}
                )
                limit = 5 if phase["phase"] == "inference" else 30
                if now - phase["started"] > limit:
                    raise RuntimeError("phase_deadline")
                time.sleep(0.05)
            if child.returncode:
                raise RuntimeError("probe_child_failed")
            result = json.loads((LOCAL / "probe-result.json").read_text())
            if (LOCAL / "probe-result.json").stat().st_mtime < time.time() - (
                time.monotonic() - started
            ) - 1:
                raise RuntimeError("stale_result")
            if result["peak_helper_rss_bytes"] + baseline >= 512 * 1024 * 1024:
                raise RuntimeError("recorded_peak_rss_limit")
            shutil.copyfile(LOCAL / "probe-result.json", run / "result.json")
            status, reason = "local_probe_complete", None
        except RuntimeError as error:
            reason = str(error)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    summary = {
        "status": status,
        "reason": reason,
        "preview_only": True,
        "nfr04_accepted": False,
        "api_rss_baseline_bytes": baseline,
        "sampled_peak_combined_rss_bytes": peak,
        "elapsed_seconds": time.monotonic() - started,
        "preview_api_pid": args.preview_api_pid,
    }
    (run / "supervisor.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({**summary, "run": str(run.relative_to(ROOT))}))
    return 0 if status == "local_probe_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
