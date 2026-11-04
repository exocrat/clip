"""Bounded immutable numerical caching; native equivalence lives in real PG tests."""

import base64
import struct
from uuid import uuid4

import numpy as np
import pytest

from app.core.errors import PublicError
from app.domains.listings.hybrid_snapshot import HybridVectorCache, decode_generations


def rows(identifier=None):
    """Encode the exact documented PostgreSQL real[] binary layout, not SQL math."""
    identifier = str(identifier or uuid4())
    vector = struct.pack("!iiIii", 1, 0, 700, 384, 1)
    vector += b"".join(
        struct.pack("!if", 4, 1.0 if index == 0 else 0.0) for index in range(384)
    )
    return [
        [identifier, kind, 0, base64.b64encode(vector).decode()]
        for kind in ("title", "description")
    ]


def test_cache_is_bounded_pipeline_scoped_and_expiring_without_mutating_snapshots():
    clock = [0.0]
    cache = HybridVectorCache(max_parts=2, clock=lambda: clock[0])
    pipeline = b"a" * 32
    first = decode_generations(rows(), cache)
    cache.store(pipeline, first)
    original = cache.snapshot(pipeline)
    assert set(original) == set(first) and not cache.snapshot(b"b" * 32)
    matrix = next(iter(original.values())).matrix
    assert np.array_equal(matrix[:, 0], [1.0, 1.0])
    with pytest.raises(ValueError):
        matrix[0, 0] = 0.5
    cache.store(pipeline, decode_generations(rows(), cache))
    assert set(cache.snapshot(pipeline)) != set(original)
    assert matrix[0, 0] == 1.0
    clock[0] = 301
    assert cache.snapshot(pipeline) == {}


@pytest.mark.parametrize("fault", ["duplicate", "missing", "binary", "nonfinite"])
def test_invalid_vectors_never_enter_cache(fault):
    cache = HybridVectorCache()
    values = rows()
    if fault == "duplicate":
        values.append(values[0])
    elif fault == "missing":
        values.pop()
    elif fault == "binary":
        values[0][3] = base64.b64encode(b"bad").decode()
    else:
        raw = bytearray(base64.b64decode(values[0][3]))
        raw[24:28] = struct.pack("!f", float("nan"))
        values[0][3] = base64.b64encode(raw).decode()
    with pytest.raises((ValueError, TypeError)):
        decode_generations(values, cache)
    assert cache.snapshot(b"a" * 32) == {}
