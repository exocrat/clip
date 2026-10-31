"""Freeze-integrity refusals; synthetic archive/ledger controls, never cloud data."""

import hashlib
import io
import tarfile
from types import SimpleNamespace
from uuid import UUID

import pytest

from scripts.evaluation import reference_release as subject


def archive_fixture(tmp_path, *, unsafe=False):
    """Produce52tiny ordinary members; these are not actual product photos."""
    target = tmp_path / "fixture.tar.gz"
    records = []
    with tarfile.open(target, "w:gz") as archive:
        for index in range(52):
            name = (
                f"images/unit-{index}.jpg" if index < 45 else f"data/unit-{index}.json"
            )
            if unsafe and index == 0:
                name = "../outside"
            content = str(index).encode()
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
            records.append(
                {
                    "path": name,
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
    return target, {
        "archive": target.name,
        "archive_bytes": target.stat().st_size,
        "archive_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "files": records,
    }


def test_archive_verified_without_extraction(tmp_path):
    target, index = archive_fixture(tmp_path)
    assert subject.verify_archive(index, target)["members_verified"] == 52
    assert not (tmp_path / "images").exists()


def test_changed_archive_refused(tmp_path):
    target, index = archive_fixture(tmp_path)
    target.write_bytes(target.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="archive_bytes_changed"):
        subject.verify_archive(index, target)


def test_traversal_member_refused_without_extracting(tmp_path):
    target, index = archive_fixture(tmp_path, unsafe=True)
    with pytest.raises(ValueError, match="unsafe_archive_member"):
        subject.verify_archive(index, target)
    assert not (tmp_path.parent / "outside").exists()


def ledger_fixture():
    """Count-shaped verification data; no actual upload or acceptance assertion."""
    target = SimpleNamespace(
        account="synthetic",
        bucket="synthetic",
        prefix="unit",
        object_key_for=lambda identifier: "unit/" + identifier,
    )
    plan = [
        {
            "upload_id": str(UUID(int=i + 1, version=4)),
            "sha256": hashlib.sha256(str(i).encode()).hexdigest(),
            "size_bytes": 1,
        }
        for i in range(1000)
    ]
    bundle = {
        "manifest": {"logical_data_fingerprint": "sha256:" + "a" * 64},
        "image_plan": plan,
    }
    rows = [
        {
            "state": "target_checked",
            "account": target.account,
            "bucket": target.bucket,
            "prefix": target.prefix,
        }
    ]
    for item in plan:
        rows.extend(
            {
                "state": state,
                "key": target.object_key_for(item["upload_id"]),
                "sha256": item["sha256"],
            }
            for state in ("put_planned", "bytes_verified")
        )
    rows += [
        {"state": "sql_planned"},
        {
            "state": "sql_committed",
            "fingerprint": bundle["manifest"]["logical_data_fingerprint"],
        },
    ]
    return rows, bundle, target


@pytest.mark.parametrize("change", ["hash", "duplicate", "scope", "commit"])
def test_ledger_changes_cannot_validate_a_freeze(change):
    rows, bundle, target = ledger_fixture()
    assert subject.verify_ledger(rows, bundle, target)["objects_verified"] == 1000
    if change == "hash":
        rows[2]["sha256"] = "0" * 64
    if change == "duplicate":
        rows[4]["key"] = rows[2]["key"]
    if change == "scope":
        rows[0]["bucket"] = "another"
    if change == "commit":
        rows[-1]["fingerprint"] = "sha256:" + "b" * 64
    with pytest.raises(ValueError):
        subject.verify_ledger(rows, bundle, target)
