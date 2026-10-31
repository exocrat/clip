"""Snapshot refusals emit no vectors or mutate data; native run proves hash parity."""

from types import SimpleNamespace

import pytest

from scripts.evaluation.reference_freeze_snapshot import vector_index_snapshot


@pytest.mark.parametrize("rows", [[], [("id", "pipeline", "source", "title", 0, [])]])
def test_partial_vectors_refuse_without_other_query_or_write(rows):
    calls = []

    def execute(statement):
        calls.append(statement)
        return SimpleNamespace(fetchall=lambda: rows)

    with pytest.raises(ValueError, match="snapshot_current_vector_scope_changed"):
        vector_index_snapshot(SimpleNamespace(execute=execute))
    assert len(calls) == 1 and calls[0].lstrip().startswith("SELECT")
