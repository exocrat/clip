"""Temporary Windows sleep prevention for a WSL-owned campaign process.

No power-plan settings are edited. Windows releases the execution-state request
when its helper exits; closing the parent's private stdin pipe ends that helper.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from pathlib import Path
import selectors
import subprocess
from typing import Iterator, Any


@contextmanager
def keep_awake() -> Iterator[dict[str, Any]]:
    """Keep the system awake, allowing the display to sleep, only during this scope."""
    executable = Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
    if not executable.is_file():
        yield {"available": False, "reason": "windows_helper_not_available"}
        return
    script = """Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class ClipCampaignPower { [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags); }';
$state = [ClipCampaignPower]::SetThreadExecutionState([uint32]2147483649);
if ($state -eq 0) { exit 2 };
[Console]::Out.WriteLine("ready"); [Console]::Out.Flush();
try { [void][Console]::In.ReadToEnd() } finally { [void][ClipCampaignPower]::SetThreadExecutionState([uint32]2147483648) }
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    process = subprocess.Popen(
        [str(executable), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert process.stdout is not None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            ready = (
                bool(selector.select(10))
                and process.stdout.readline().strip() == b"ready"
            )
        yield {
            "available": ready,
            "mode": "system_required_display_may_sleep",
            "pid": process.pid,
        }
    finally:
        if process.stdin:
            process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
