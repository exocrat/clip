"""Destructive local rebuild must refuse unowned/mismatched state before dropdb."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from scripts.evaluation.reference_local import OwnedCluster, DATABASE, ROLE


@pytest.mark.parametrize(
    "failure", ["stopped", "uncreated", "paths", "database", "socket"]
)
def test_reset_refuses_before_any_process_or_drop(tmp_path, failure):
    # Explicit negative guard fixture; never emulate a successful reset/migration.
    cluster = object.__new__(OwnedCluster)
    cluster.root = tmp_path
    cluster.cluster = tmp_path / "cluster"
    cluster.socket = tmp_path / "pgsocket"
    cluster.started = failure != "stopped"
    cluster._reference_created = failure != "uncreated"
    if failure == "paths":
        cluster.cluster = tmp_path.parent / "someone-else"
    row = (
        ("existing_shared_database", ROLE, None)
        if failure == "database"
        else (DATABASE, ROLE, None)
    )
    connection = SimpleNamespace(
        info=SimpleNamespace(
            host="other/socket" if failure == "socket" else str(cluster.socket)
        ),
        execute=lambda statement: SimpleNamespace(fetchone=lambda: row),
    )
    cluster.connection = lambda: nullcontext(connection)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unowned reset launched a process")

    cluster.run = forbidden
    with pytest.raises(ValueError):
        cluster.rebuild_reference()
