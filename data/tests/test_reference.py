"""Final-recipe invariants, provenance and IO safety; no database/cloud/photos required."""

from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import struct
import zlib

import pytest

from data.generators import files, reference
from data.generators.manifest import canonical_json
from data.generators.preview import stable_id

T = "2026-10-30T00:00:00.000000Z"


def png(index):
    """Encode a tiny, valid, distinct RGB PNG fixture without installing an image library."""

    def chunk(kind, content):
        return (
            struct.pack(">I", len(content))
            + kind
            + content
            + struct.pack(">I", zlib.crc32(kind + content))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes([0, index, 0, 0])))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    """Supply45explicit test source photos through the same private inventory boundary."""
    root = tmp_path / "images"
    root.mkdir()
    document = json.loads(reference.IMAGE_INVENTORY.read_text())
    for index, image in enumerate(document["images"]):
        relative = f"{image['category_code']}/{image['topic_slug']}.png"
        path = root / relative
        path.parent.mkdir(exist_ok=True)
        content = png(index)
        path.write_bytes(content)
        image.update(
            source_relative_path=relative,
            media_type="image/png",
            size_bytes=len(content),
            width=1,
            height=1,
            sha256=hashlib.sha256(content).hexdigest(),
        )
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps(document))
    monkeypatch.setattr(reference, "IMAGE_INVENTORY", inventory)
    monkeypatch.setattr(files, "RUNS_ROOT", tmp_path / "runs")
    return root, inventory, document


def build(root, audit=2030):
    """Use a fixed logical day and separately varied audit time."""
    return reference.build_reference(
        logical_time=T,
        image_root=root,
        sensitive_threshold_paise=500000,
        generated_at=datetime(audit, 1, 2, tzinfo=UTC),
    )


def test_exact_independent_distributions_and_all45topics(inputs):
    root, _, _ = inputs
    bundle = build(root)
    users, listings = bundle["users"], bundle["listings"]
    assert bundle["manifest"]["requested_counts"] == {
        "users": 5000,
        "listings": 1000,
        "planned_images": 1000,
    }
    counts = bundle["manifest"]["observed_counts"]
    assert (
        counts["users"] == 5000
        and counts["listings"] == counts["planned_images"] == 1000
    )
    assert counts["user_classes"] == {"regular": 5000}
    expected_categories = {
        key: 111
        for key in (
            "mobile_phone",
            "laptop",
            "electronics",
            "furniture",
            "books",
            "bicycles",
            "appliances",
            "sports_fitness",
            "other",
        )
    }
    expected_categories["mobile_phone"] = 112
    assert counts["categories"] == expected_categories
    assert counts["conditions"] == {
        key: 250 for key in ("new", "like_new", "good", "fair")
    }
    assert counts["prices_paise"] == {
        str(n * 100): 100
        for n in (0, 250, 500, 1000, 2000, 3000, 5000, 8000, 12000, 20000)
    }
    assert counts["proof"] == {"omitted": 334, "true": 333, "false": 333}
    assert counts["negotiable"] == {"true": 500, "false": 500}
    assert counts["availability_scenarios"] == {
        "available": 800,
        "unavailable": 100,
        "future": 50,
        "expired": 50,
    }
    assert set(counts["pickup_areas"].values()) == {250}
    assert len(counts["topics"]) == 45 and set(counts["topics"].values()) <= {22, 23}
    assert len({u["display_name"].lower() for u in users}) == 5000 and all(
        u["handle_ready"] for u in users
    )
    assert counts["distinct_regular_owners"] == 1000
    # Assignments must not accidentally couple condition with price or category.
    assert all(
        len({r["condition_code"] for r in listings if r["asking_price_paise"] == p})
        == 4
        for p in (0, 25000, 2000000)
    )
    assert all(
        len(r["title"]) <= 120 and len(r["description"]) <= 5000 for r in listings
    )


def test_hash_assignment_and_owner_order_match_the_recipe(inputs):
    bundle = build(inputs[0])
    listings = {r["id"]: r for r in bundle["listings"]}
    key = lambda tag, identifier: (
        hashlib.sha256(f"42:{tag}:{identifier}".encode()).digest(),
        identifier,
    )
    ordered = sorted(listings, key=lambda i: key("category", i))
    assert all(listings[i]["category_code"] == "mobile_phone" for i in ordered[:112])
    assert all(listings[i]["category_code"] == "laptop" for i in ordered[112:223])
    selected = sorted(
        [stable_id(42, "user_placeholder", n) for n in range(1, 5001)],
        key=lambda i: key("owner", i),
    )[:1000]
    assert [
        listings[i]["owner_id"]
        for i in sorted(listings, key=lambda i: key("listing-owner", i))
    ] == selected


def test_lifecycle_windows_and_only_current800match(inputs):
    bundle = build(inputs[0])
    moment = datetime.fromisoformat(T)
    query_time = moment + timedelta(hours=1)
    for u in bundle["users"]:
        assert u["created_at"] == "2026-10-29T00:00:00.000000Z"
        assert u["account_class"] == "regular"
        assert u["expires_at"] is None and u["activated_at"] is None
    eligible = [
        r
        for r in bundle["listings"]
        if r["availability"] == "available"
        and datetime.fromisoformat(r["available_from"])
        <= query_time
        < datetime.fromisoformat(r["available_until"])
    ]
    assert len(eligible) == 800
    assert len({r["created_at"] for r in bundle["listings"]}) == 1
    assert not any(bundle["manifest"]["acceptance"].values())
    assert all(
        not ({"password", "session", "email", "otp", "token", "private_key"} & set(u))
        for u in bundle["users"]
    )


def test_image_plan_has_owned_unique_ids_keys_and_exact_source_bytes(inputs):
    root, _, document = inputs
    bundle = build(root)
    sources = {i["source_relative_path"]: i for i in document["images"]}
    rows = {r["id"]: r for r in bundle["listings"]}
    for field in ("image_id", "upload_id", "operation_id", "relative_object_key"):
        assert len({i[field] for i in bundle["image_plan"]}) == 1000
    all_ids = [r["id"] for r in bundle["users"] + bundle["listings"]]
    all_ids += [
        i[k]
        for i in bundle["image_plan"]
        for k in ("image_id", "upload_id", "operation_id")
    ]
    assert len(all_ids) == len(set(all_ids))
    for image in bundle["image_plan"]:
        listing = rows[image["listing_id"]]
        source = sources[image["source_relative_path"]]
        assert image["owner_id"] == listing["owner_id"]
        assert (source["category_code"], source["topic_slug"]) == (
            listing["category_code"],
            listing["topic_slug"],
        )
        assert (
            image["sha256"]
            == hashlib.sha256(
                (root / image["source_relative_path"]).read_bytes()
            ).hexdigest()
        )
        assert "confirmed" not in image and "bucket" not in image


def test_reproducibility_excludes_audit_timestamps_but_binds_threshold_and_logical_time(
    inputs,
):
    root, inventory, doc = inputs
    first = build(root, 2030)
    doc["recorded_utc"] = "2099-01-01 00:00:00 UTC"
    inventory.write_text(json.dumps(doc))
    second = build(root, 2031)
    assert first["manifest"]["generated_at"] != second["manifest"]["generated_at"]
    assert (
        first["manifest"]["logical_data_fingerprint"]
        == second["manifest"]["logical_data_fingerprint"]
    )
    changed = reference.build_reference(
        logical_time=T, image_root=root, sensitive_threshold_paise=800000
    )
    assert (
        changed["manifest"]["logical_data_fingerprint"]
        != first["manifest"]["logical_data_fingerprint"]
    )
    changed_time = reference.build_reference(
        logical_time="2026-10-31T00:00:00.000000Z",
        image_root=root,
        sensitive_threshold_paise=500000,
    )
    assert (
        changed_time["manifest"]["logical_data_fingerprint"]
        != first["manifest"]["logical_data_fingerprint"]
    )


@pytest.mark.parametrize(
    "kind", ["price", "owner", "image", "claim", "unknown", "source"]
)
def test_validator_refuses_changed_data_and_false_acceptance(inputs, kind, monkeypatch):
    root = inputs[0]
    original = build(root)
    changed = deepcopy(original)
    if kind == "price":
        changed["listings"][0]["asking_price_paise"] = 99
    if kind == "owner":
        changed["listings"][0]["owner_id"] = changed["users"][-1]["id"]
    if kind == "image":
        changed["image_plan"][0]["sha256"] = "0" * 64
    if kind == "claim":
        changed["manifest"]["acceptance"]["data_ready"] = True
    if kind == "unknown":
        changed["users"][0]["password"] = "synthetic-only"
    if kind == "source":
        source = reference.source_binding()
        source["source_digest"] = "sha256:" + "0" * 64
        monkeypatch.setattr(reference, "source_binding", lambda: source)
    with pytest.raises(ValueError, match="altered, stale"):
        reference.validate_reference(changed, image_root=root)


def test_published_descendant_keeps_exact_recorded_source_binding(inputs, monkeypatch):
    """A new publication HEAD alone is not a data/schema/source-content change."""
    root = inputs[0]
    bundle = build(root)
    current = reference.source_binding() | {"base_revision": "f" * 40}
    monkeypatch.setattr(reference, "source_binding", lambda: current)
    assert reference.validate_reference(bundle, image_root=root) == bundle["manifest"]


@pytest.mark.parametrize("base", ["0" * 40, "--not-a-revision"])
def test_unknown_or_malformed_recorded_base_refused(inputs, base):
    bundle = build(inputs[0])
    bundle["manifest"]["source_revision"] = base
    with pytest.raises(ValueError, match="known ancestor"):
        reference.validate_reference(bundle, image_root=inputs[0])


@pytest.mark.parametrize(
    "kind",
    [
        "changed-content",
        "missing",
        "traversal",
        "symlink",
        "wrong-mime",
        "oversized",
        "duplicated-topic",
    ],
)
def test_source_inventory_refuses_unreviewed_inputs_before_output(
    inputs, kind, tmp_path
):
    root, inventory, doc = inputs
    image = doc["images"][0]
    path = root / image["source_relative_path"]
    if kind == "changed-content":
        path.write_bytes(png(250))
    if kind == "missing":
        path.unlink()
    if kind == "traversal":
        image["source_relative_path"] = "../outside.png"
    if kind == "symlink":
        source = tmp_path / "outside.png"
        path.replace(source)
        path.symlink_to(source)
    if kind == "wrong-mime":
        image["media_type"] = "image/jpeg"
    if kind == "oversized":
        path.write_bytes(b"x" * (reference.MAX_IMAGE_BYTES + 1))
        image["size_bytes"] = reference.MAX_IMAGE_BYTES + 1
    if kind == "duplicated-topic":
        doc["images"][-1] = deepcopy(doc["images"][0])
    inventory.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        reference.write_reference(
            name="refused",
            logical_time=T,
            image_root=root,
            sensitive_threshold_paise=500000,
        )
    assert not (files.RUNS_ROOT / "refused").exists()


def test_exclusive_named_runs_pair_validation_and_no_replacement(inputs):
    root = inputs[0]
    manifest = reference.write_reference(
        name="first", logical_time=T, image_root=root, sensitive_threshold_paise=500000
    )
    assert reference.read_reference("first", image_root=root) == manifest
    before = (files.RUNS_ROOT / "first/dataset.json").read_bytes()
    with pytest.raises(ValueError):
        reference.write_reference(
            name="first",
            logical_time=T,
            image_root=root,
            sensitive_threshold_paise=500000,
        )
    assert (files.RUNS_ROOT / "first/dataset.json").read_bytes() == before
    bad = deepcopy(manifest)
    bad["acceptance"]["sql_loaded"] = True
    (files.RUNS_ROOT / "first/manifest.json").write_bytes(canonical_json(bad))
    with pytest.raises(ValueError, match="differs"):
        reference.read_reference("first", image_root=root)
    with pytest.raises(ValueError):
        reference.write_reference(
            name="../escape",
            logical_time=T,
            image_root=root,
            sensitive_threshold_paise=500000,
        )


@pytest.mark.parametrize(
    "clock",
    [
        "2030-01-01T12:00:00.000000Z",
        "2030-01-01T00:00:00Z",
        "2030-01-01T00:00:00.000000+00:00",
        "not-a-clock",
    ],
)
def test_canonical_midnight_required(clock):
    with pytest.raises(ValueError):
        reference.logical_clock(clock)


def test_listing_populations_remain_stable_through_november(inputs):
    """All four availability cohorts stay unchanged at late-November evaluation times."""
    bundle = build(inputs[0])
    assert (
        bundle["manifest"]["measurement_window"]["before"]
        == "2026-12-01T00:00:00.000000Z"
    )
    for instant in (
        "2026-10-30T01:00:00+00:00",
        "2026-11-13T00:00:00+00:00",
        "2026-11-29T00:00:00+00:00",
        "2026-11-30T23:59:59.999999+00:00",
    ):
        clock = datetime.fromisoformat(instant)
        eligible = [
            r
            for r in bundle["listings"]
            if r["availability"] == "available"
            and datetime.fromisoformat(r["available_from"])
            <= clock
            < datetime.fromisoformat(r["available_until"])
        ]
        assert len(eligible) == 800
    with pytest.raises(ValueError, match="cutoff"):
        reference.build_reference(
            logical_time="2026-12-01T00:00:00.000000Z",
            image_root=inputs[0],
            sensitive_threshold_paise=500000,
        )
