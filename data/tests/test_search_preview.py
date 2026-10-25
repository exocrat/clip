"""Search fixture reproducibility, contract shape and loader refusal checks.

These tests do not substitute for PostgreSQL migration/FK/image/index checks.
No authentication credentials, providers or cloud resources are involved.
"""

from datetime import UTC, datetime
import os
import subprocess
import sys
from unittest.mock import Mock, MagicMock
from uuid import UUID

import pytest

from app.contracts.domain_types import CreateListingRequest
from data.generators import files, search_loader, search_preview

CONFIG = dict(
    seed=42,
    user_count=12,
    listing_count=100,
    logical_time="2026-10-24T09:00:00.000000Z",
)


@pytest.fixture
def corpus():
    """Fresh fixture data prevents corruption tests from sharing mutations."""
    return search_preview.build_corpus(**CONFIG)


def test_reference_counts_reproducibility_and_audit_clock():
    """Reference-sized preview rows remain identical despite different audit times."""
    config = {**CONFIG, "user_count": 5000, "listing_count": 1000}
    first = search_preview.build_corpus(
        **config, generated_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    second = search_preview.build_corpus(
        **config, generated_at=datetime(2026, 2, 1, tzinfo=UTC)
    )
    search_preview.validate_corpus(first)
    search_preview.validate_corpus(second)
    assert first["users"] == second["users"]
    assert first["listings"] == second["listings"]
    assert first["manifest"]["observed_counts"] == {"users": 5000, "listings": 1000}
    assert (
        first["manifest"]["logical_data_fingerprint"]
        == second["manifest"]["logical_data_fingerprint"]
    )
    assert first["manifest"]["preview_only"] is True
    assert first["manifest"]["image_objects_verified"] is False


def test_contract_fields_and_relationships(corpus):
    """Fixture create payloads validate against the actual generated contract."""
    users = {row["id"] for row in corpus["users"]}
    images = set()
    for row in corpus["listings"]:
        assert row["owner_id"] in users
        assert UUID(row["id"]).version == UUID(row["image_id"]).version == 4
        images.add(row["image_id"])
        fields = {
            key: row[key]
            for key in (
                "title",
                "description",
                "category_code",
                "condition_code",
                "asking_price_paise",
                "negotiable",
                "pickup_area",
                "available_from",
                "available_until",
                "proof_available",
            )
        }
        CreateListingRequest.model_validate(
            {**fields, "operation_id": row["id"], "image_upload_ids": [row["image_id"]]}
        )
    assert len(images) == len(corpus["listings"])
    assert {row["category_code"] for row in corpus["listings"]} == {
        topic[0] for topic in search_preview.TOPICS
    }
    assert {row["condition_code"] for row in corpus["listings"]} == set(
        search_preview.CONDITIONS
    )
    assert {row["negotiable"] for row in corpus["listings"]} == {False, True}


def test_availability_scenarios_and_ties(corpus):
    """Controlled times support future, ended, unavailable and stable-tie tests."""
    now = datetime.fromisoformat(CONFIG["logical_time"])
    listings = corpus["listings"]
    assert sum(row["availability"] == "unavailable" for row in listings) == 10
    assert (
        sum(datetime.fromisoformat(row["available_from"]) > now for row in listings)
        == 10
    )
    assert (
        sum(
            row["available_until"] is not None
            and datetime.fromisoformat(row["available_until"]) <= now
            for row in listings
        )
        == 10
    )
    assert listings[0]["created_at"] == listings[1]["created_at"]
    assert listings[0]["asking_price_paise"] == listings[1]["asking_price_paise"] == 0


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["users"][0].update(display_name="Uncontrolled content"),
        lambda b: b["listings"][0].update(owner_id="missing"),
        lambda b: b["listings"][0].update(asking_price_paise=False),
        lambda b: b["listings"][0].update(asking_price_paise=0.0),
        lambda b: b["listings"][0].update(contact="private"),
        lambda b: b["listings"][0].update(image_id=b["listings"][1]["image_id"]),
        lambda b: b["listings"].reverse(),
        lambda b: b["manifest"].update(preview_only=False),
        lambda b: b["manifest"].update(source_fingerprint="stale"),
        lambda b: b["manifest"]["observed_counts"].update(users=5000),
    ],
)
def test_tampered_corpus_rejected(corpus, change):
    """Neither a claimed checksum nor plausible shape authorizes altered fixtures."""
    change(corpus)
    with pytest.raises(ValueError, match="Invalid, altered or stale"):
        search_preview.validate_corpus(corpus)


@pytest.mark.parametrize(
    "config",
    [
        {"user_count": 0},
        {"seed": True},
        {"user_count": -1},
        {"listing_count": 100001},
        {"logical_time": "2026-10-24T09:00:00"},
        {"logical_time": "2026-10-24T09:00:00+00:00"},
    ],
)
def test_invalid_inputs(config):
    """Reject invalid counts, ownerless listings and ambiguous logical clocks."""
    with pytest.raises(ValueError):
        search_preview.build_corpus(**{**CONFIG, **config})


def test_configuration_changes_fingerprint(corpus):
    """Seed and logical time are meaningful corpus inputs, not audit metadata."""
    original = corpus["manifest"]["logical_data_fingerprint"]
    for override in ({"seed": 43}, {"logical_time": "2026-10-25T09:00:00.000000Z"}):
        assert (
            search_preview.build_corpus(**{**CONFIG, **override})["manifest"][
                "logical_data_fingerprint"
            ]
            != original
        )


def test_private_named_runs_and_stale_manifest(tmp_path, monkeypatch):
    """Named local files round-trip; existing runs and corrupt manifests fail."""
    monkeypatch.setattr(files, "RUNS_ROOT", tmp_path / "runs")
    search_preview.write_corpus(name="fixture", **CONFIG)
    assert search_preview.read_corpus("fixture")["manifest"]["preview_only"]
    with pytest.raises(FileExistsError):
        search_preview.write_corpus(name="fixture", **CONFIG)
    manifest = files.RUNS_ROOT / "fixture/manifest.json"
    manifest.write_text("{}")
    with pytest.raises(ValueError, match="manifest does not match"):
        search_preview.read_corpus("fixture")
    with pytest.raises(ValueError):
        search_preview.read_corpus("../escape")
    (files.RUNS_ROOT / "link").symlink_to(files.RUNS_ROOT / "fixture")
    with pytest.raises(ValueError):
        search_preview.read_corpus("link")


def test_cross_process_hash_seed(tmp_path):
    """Process hash randomization cannot perturb corpus records or fingerprints."""
    script = f"from data.generators.search_preview import build_corpus; print(build_corpus(**{CONFIG!r})['manifest']['logical_data_fingerprint'])"
    results = [
        subprocess.run(
            [sys.executable, "-c", script],
            env={"PATH": os.defpath, "HOME": str(tmp_path), "PYTHONHASHSEED": seed},
            check=True,
            capture_output=True,
            timeout=20,
        ).stdout
        for seed in ("1", "987")
    ]
    assert results[0] == results[1]


def test_loader_requires_explicit_local_test_mode(tmp_path, monkeypatch):
    """No opt-in or ambient production/database settings may reach a connection."""
    path = tmp_path.resolve()
    monkeypatch.setenv("CLIP_ENVIRONMENT", "production")
    with pytest.raises(ValueError):
        search_loader.require_local_preview(str(path), True)
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.delenv("CLIP_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError):
        search_loader.require_local_preview(str(path), False)
    assert search_loader.require_local_preview(str(path), True) == path
    monkeypatch.setenv("DATABASE_URL", "synthetic-not-a-url")
    with pytest.raises(ValueError):
        search_loader.require_local_preview(str(path), True)


@pytest.mark.parametrize(
    "target",
    [
        ("clip_test_other", search_loader.ROLE, None),
        (search_loader.DATABASE, "other_role", None),
        (search_loader.DATABASE, search_loader.ROLE, "127.0.0.1"),
    ],
)
def test_loader_checks_server_target_before_lock_or_writes(corpus, target):
    """A fixed client request alone cannot establish a safe server target."""
    connection = Mock()
    connection.transaction.return_value.__enter__ = Mock()
    connection.transaction.return_value.__exit__ = Mock(return_value=False)
    connection.execute.return_value.fetchone.return_value = target
    with pytest.raises(ValueError, match="non-preview"):
        search_loader.load_corpus(connection, corpus)
    assert not any(
        "LOCK TABLE" in call.args[0] or "INSERT" in call.args[0]
        for call in connection.execute.call_args_list
    )
    connection.cursor.assert_not_called()


def test_loader_refuses_nonempty_database(corpus):
    """Do not overwrite or merge application data into an existing test target."""
    connection = Mock()
    connection.transaction.return_value.__enter__ = Mock()
    connection.transaction.return_value.__exit__ = Mock(return_value=False)
    target = Mock()
    target.fetchone.return_value = (search_loader.DATABASE, search_loader.ROLE, None)
    counts = Mock()
    counts.fetchone.return_value = (1, 0, 0, 0)
    connection.execute.side_effect = [Mock(), Mock(), Mock(), target, Mock(), counts]
    with pytest.raises(ValueError, match="not empty"):
        search_loader.load_corpus(connection, corpus)
    connection.cursor.assert_not_called()


def test_loader_validation_happens_before_database_access(corpus):
    """Untrusted records must be refused even if a caller skips the file reader."""
    connection = Mock()
    corpus["listings"][0]["asking_price_paise"] = -100
    with pytest.raises(ValueError):
        search_loader.load_corpus(connection, corpus)
    connection.transaction.assert_not_called()


def test_loader_rejects_ambient_redirect_before_connect(tmp_path, monkeypatch, corpus):
    """A libpq redirect must not reach a connection even with valid test opt-in."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.delenv("CLIP_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PGHOSTADDR", "synthetic-redirect")
    monkeypatch.setattr(search_loader, "read_corpus", lambda name: corpus)
    connect = Mock()
    monkeypatch.setattr(search_loader.psycopg, "connect", connect)
    with pytest.raises(SystemExit) as failure:
        search_loader.main(
            [
                "--name",
                "fixture",
                "--socket-dir",
                str(tmp_path.resolve()),
                "--isolated-preview",
            ]
        )
    assert failure.value.code == 2
    connect.assert_not_called()


def test_loader_refuses_migration_mismatch(corpus):
    """An empty database with the wrong migration set is still unsafe to load."""
    connection = Mock()
    connection.transaction.return_value.__enter__ = Mock()
    connection.transaction.return_value.__exit__ = Mock(return_value=False)
    target = Mock()
    target.fetchone.return_value = (search_loader.DATABASE, search_loader.ROLE, None)
    counts = Mock()
    counts.fetchone.return_value = (0, 0, 0, 0)
    versions = Mock()
    versions.fetchall.return_value = [("unrelated_version",)]
    connection.execute.side_effect = [
        Mock(),
        Mock(),
        Mock(),
        target,
        Mock(),
        counts,
        versions,
    ]
    with pytest.raises(ValueError, match="migrations do not match"):
        search_loader.load_corpus(connection, corpus)
    connection.cursor.assert_not_called()


def test_loader_upload_metadata_is_current_not_historical():
    """The image-binding trigger rejects expired uploads despite valid listing dates.

    Inspect only parameter construction through a recording connection; this
    does not establish that the SQL or database constraints actually pass.
    """
    corpus = search_preview.build_corpus(
        **{**CONFIG, "user_count": 1, "listing_count": 1}
    )
    connection = MagicMock()
    target, counts, versions, categories, conditions, final_counts = (
        Mock() for _ in range(6)
    )
    target.fetchone.return_value = (search_loader.DATABASE, search_loader.ROLE, None)
    counts.fetchone.return_value = (0, 0, 0, 0)
    versions.fetchall.return_value = [
        (path.name.split("_", 1)[0],)
        for path in (search_loader.ROOT / "database/migrations").glob("*.sql")
    ]
    category = corpus["listings"][0]["category_code"]
    categories.fetchall.return_value = [(category, "synthetic-category-id")]
    conditions.fetchall.return_value = [(corpus["listings"][0]["condition_code"],)]
    final_counts.fetchone.return_value = (1, 1, 1)
    connection.execute.side_effect = [
        Mock(),
        Mock(),
        Mock(),
        target,
        Mock(),
        counts,
        versions,
        categories,
        conditions,
        Mock(),
        final_counts,
    ]
    before = datetime.now(UTC)
    search_loader.load_corpus(connection, corpus)
    cursor = connection.cursor.return_value.__enter__.return_value
    upload = next(
        call
        for call in cursor.execute.call_args_list
        if "INSERT INTO listings.image_uploads" in call.args[0]
    )
    created, expiry_base, confirmed = upload.args[1][-3:]
    assert before <= created <= datetime.now(UTC)
    assert created == expiry_base == confirmed
    assert created != datetime.fromisoformat(corpus["listings"][0]["created_at"])
