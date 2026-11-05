"""Append private, content-free observer evidence before a final report exists."""

from __future__ import annotations
import json
import os
from pathlib import Path
import stat
from typing import Any


def record(plan: dict[str, Any], row: dict[str, Any]) -> None:
    """Preserve timeline/outcomes across provider failures without secret fields."""
    value = plan.get("observation_path")
    if value is None:
        return
    path = Path(value)
    if not path.is_absolute() or path.parent.resolve(strict=True) != path.parent:
        raise ValueError("unsafe_observer_journal_path")
    denied = {
        "cookie",
        "password",
        "csrf_token",
        "authorization",
        "secretstring",
        "tokenvalue",
        "message",
        "body",
        "email",
        "content",
    }

    def check(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or key.lower() in denied:
                    raise ValueError("private_observer_field_refused")
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)

    check(row)
    payload = (json.dumps(row, sort_keys=True, allow_nan=False) + "\n").encode()
    if len(payload) > 32768:
        raise ValueError("observer_row_too_large")
    fd = os.open(
        path,
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_size > 16_000_000
        ):
            raise ValueError("unsafe_observer_journal_file")
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
