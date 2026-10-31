"""Local-loader target/media safety; SQL/application acceptance uses the opt-in native run."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from data.generators import reference_load as loader
from data.tests.test_reference import inputs, build, png
from scripts.evaluation.reference_local import require_local


class Cursor:
    """Return explicit guard rows only; never emulate successful DML or schema acceptance."""

    def __init__(self, row=None, rows=()):
        self.row, self.rows = row, rows

    def fetchone(self):
        return self.row

    def __iter__(self):
        return iter(self.rows)


class GuardConnection:
    """Control negative target/empty checks, recording that no insertion occurs."""

    def __init__(self, objects, bundle, target=None, nonempty=False):
        self.info = SimpleNamespace(
            host=str(objects.root.parent / "pgsocket"), port=55438
        )
        self.target = target or (loader.DATABASE, loader.ROLE, None, "180006")
        self.versions = bundle["manifest"]["source_binding"]["migration_versions"]
        self.nonempty = nonempty
        self.calls = []

    def execute(self, statement, *args):
        self.calls.append(statement)
        if "current_database()" in statement:
            return Cursor(row=self.target)
        if "SELECT version" in statement:
            return Cursor(rows=[(v,) for v in self.versions])
        if "SELECT (SELECT count(*)" in statement:
            return Cursor(row=(1, 0, 0, 0) if self.nonempty else (0, 0, 0, 0))
        return Cursor()

    def transaction(self):
        return nullcontext()


def test_objects_are_real_immutable_owned_copies_and_all_keys_verify(inputs, tmp_path):
    root = inputs[0]
    bundle = build(root)
    objects = loader.LocalObjects(tmp_path / "media")
    before = {p: p.read_bytes() for p in root.rglob("*.png")}
    receipt = objects.materialize(bundle, root)
    assert receipt["verified_local_objects"] == 1000
    assert len(list((objects.root / "blobs").iterdir())) == 45
    assert len(list((objects.root / "objects").iterdir())) == 1000
    assert all(p.read_bytes() == data for p, data in before.items())
    image = bundle["image_plan"][0]
    key = objects.object_key_for(image["upload_id"])
    assert objects.read(key) == (root / image["source_relative_path"]).read_bytes()
    assert (
        objects.path(key).stat().st_ino
        != (root / image["source_relative_path"]).stat().st_ino
    )
    with pytest.raises(FileExistsError):
        objects.put(key, png(1), "image/png")
    with pytest.raises(ValueError):
        loader.LocalObjects(objects.root)
    with pytest.raises(ValueError):
        objects.path("../outside")
    objects.path(key).unlink()
    objects.path(key).symlink_to(root / image["source_relative_path"])
    with pytest.raises(ValueError, match="symlinks"):
        objects.verify(bundle)


@pytest.mark.parametrize(
    "kind", ["database", "role", "tcp", "version", "socket", "port", "migrations"]
)
def test_unreviewed_connection_fails_before_insert(inputs, tmp_path, kind):
    bundle = build(inputs[0])
    objects = loader.LocalObjects(tmp_path / "media")
    connection = GuardConnection(objects, bundle)
    row = list(connection.target)
    if kind == "database":
        row[0] = "existing_shared_database"
    if kind == "role":
        row[1] = "shared_admin"
    if kind == "tcp":
        row[2] = "127.0.0.1"
    if kind == "version":
        row[3] = "170000"
    if kind == "socket":
        connection.info.host = "/unowned/socket"
    if kind == "port":
        connection.info.port = 5432
    if kind == "migrations":
        connection.versions = []
    connection.target = tuple(row)
    with pytest.raises(ValueError):
        loader.guard_target(connection, objects, bundle)
    assert not any("INSERT" in statement for statement in connection.calls)


def test_nonempty_target_never_inserts_or_overwrites(inputs, tmp_path):
    root = inputs[0]
    bundle = build(root)
    objects = loader.LocalObjects(tmp_path / "media")
    objects.materialize(bundle, root)
    connection = GuardConnection(objects, bundle, nonempty=True)
    with pytest.raises(ValueError, match="not empty"):
        loader.load_local(connection, bundle, objects, root)
    assert not any("INSERT" in statement for statement in connection.calls)
    assert any("ACCESS EXCLUSIVE" in statement for statement in connection.calls)


@pytest.mark.parametrize(
    "override", ["CLIP_DATABASE_URL", "DATABASE_URL", "PGHOST", "AWS_PROFILE"]
)
def test_local_opt_in_refuses_ambient_targets(monkeypatch, override):
    for key in tuple(__import__("os").environ):
        if key.startswith(("CLIP_", "AWS_", "PG")) or key == "DATABASE_URL":
            monkeypatch.delenv(key)
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.setenv(override, "synthetic-unapproved-target")
    with pytest.raises(ValueError, match="ambient"):
        require_local(True)


def test_local_opt_in_and_disk_caps_are_required(monkeypatch):
    for key in tuple(__import__("os").environ):
        if key.startswith(("CLIP_", "AWS_", "PG")) or key == "DATABASE_URL":
            monkeypatch.delenv(key)
    with pytest.raises(ValueError):
        require_local(False)
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.setattr(
        "scripts.evaluation.reference_local.shutil.disk_usage",
        lambda _: SimpleNamespace(free=1),
    )
    with pytest.raises(ValueError, match="2GiB"):
        require_local(True)
