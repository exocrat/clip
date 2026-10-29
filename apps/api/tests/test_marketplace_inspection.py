"""Safety checks for the explicitly isolated full-app human inspection launcher."""

import os
from pathlib import Path
import subprocess
import sys

from scripts.marketplace_inspection import inspection_photo


def test_inspection_refuses_production_before_database_or_listener():
    """A missing test opt-in cannot create test identities or touch Docker."""
    result = subprocess.run(
        [sys.executable, "scripts/marketplace_inspection.py", "--synthetic-inspection"],
        cwd=Path(__file__).resolve().parents[3],
        env={key: os.environ[key] for key in ("HOME", "PATH")}
        | {"CLIP_ENVIRONMENT": "production"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 2
    assert "CLIP_ENVIRONMENT=test is required" in result.stderr
    assert result.stdout == ""


def test_inspection_photo_is_a_valid_bounded_png():
    """Fixtures have deterministic real image bytes and a useful visible size."""
    import struct
    import zlib

    photo = inspection_photo()
    assert photo.startswith(b"\x89PNG\r\n\x1a\n")
    assert struct.unpack(">II", photo[16:24]) == (360, 220)
    offset = 8
    pixels = b""
    while offset < len(photo):
        size = int.from_bytes(photo[offset : offset + 4], "big")
        kind = photo[offset + 4 : offset + 8]
        body = photo[offset + 8 : offset + 8 + size]
        assert zlib.crc32(kind + body) == int.from_bytes(
            photo[offset + 8 + size : offset + 12 + size], "big"
        )
        if kind == b"IDAT":
            pixels += zlib.decompress(body)
        offset += size + 12
    assert len(pixels) == (360 * 3 + 1) * 220
    assert len(photo) < 100000
