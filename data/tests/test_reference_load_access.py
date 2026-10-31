"""One-window loader and S3 refusal controls; no real AWS/DB acceptance."""

from contextlib import nullcontext
from datetime import datetime, UTC, timedelta
from types import SimpleNamespace

import pytest

from scripts.evaluation import reference_load_access as access


class Connection:
    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def transaction(self):
        return nullcontext()

    def execute(self, statement, args=None):
        self.calls.append(statement)
        if isinstance(statement, str):
            if "rolvaliduntil" in statement:
                row = (123,) + (False,) * 7 + (None,)
            elif "SELECT oid,rolsuper" in statement:
                row = (999 if self.failure == "oid" else 123,) + (False,) * 6
            elif "pg_auth_members" in statement:
                row = (1,) if self.failure == "member" else None
            elif "relowner" in statement or "nspowner" in statement:
                row = (1,) if self.failure == "owner" else None
            elif "SELECT (SELECT count" in statement:
                row = (1, 0, 0, 0, 0) if self.failure == "nonempty" else (0,) * 5
            elif "WHERE oid=" in statement:
                row = (False,)
            else:
                row = (False,) * 7
            return SimpleNamespace(fetchone=lambda: row)
        if self.failure == "uncertain":
            raise RuntimeError("synthetic-private-error")
        return SimpleNamespace(fetchone=lambda: None)


@pytest.fixture(autouse=True)
def guard(monkeypatch):
    monkeypatch.setattr(access, "guard_admin", lambda *args, **kwargs: None)


@pytest.mark.parametrize("failure", ["member", "owner", "nonempty"])
def test_unsafe_target_never_activates(failure):
    instance = access.WindowAccess()
    c = Connection(failure)
    with pytest.raises(access.LoadAccessRefused):
        instance.activate(
            c,
            expires=datetime.now(UTC) + timedelta(minutes=30),
            record=lambda **event: None,
        )
    assert not instance.attempted
    assert all(isinstance(s, str) for s in c.calls)


@pytest.mark.parametrize("seconds", [-1, 60, 3000])
def test_expiry_is_bounded_before_password_sql(seconds):
    instance = access.WindowAccess()
    c = Connection()
    with pytest.raises(access.LoadAccessRefused):
        instance.activate(
            c,
            expires=datetime.now(UTC) + timedelta(seconds=seconds),
            record=lambda **event: None,
        )
    assert c.calls == []


def test_one_attempt_even_after_uncertain_sql_and_cleanup_proof():
    c = Connection("uncertain")
    instance = access.WindowAccess()
    events = []
    with pytest.raises(RuntimeError):
        instance.activate(
            c,
            expires=datetime.now(UTC) + timedelta(minutes=30),
            record=lambda **event: events.append(event),
        )
    assert instance.attempted and events[-1]["stage"] == "loader_activation_attempt"
    with pytest.raises(access.LoadAccessRefused, match="activation_already_attempted"):
        instance.activate(
            Connection(),
            expires=datetime.now(UTC) + timedelta(minutes=30),
            record=lambda **event: None,
        )
    with pytest.raises(access.LoadAccessRefused, match="cleanup_ownership"):
        instance.close(Connection("oid"), record=lambda **event: None)
    assert not instance.closed
    instance.close(Connection(), record=lambda **event: events.append(event))
    assert instance.closed and events[-1]["stage"] == "loader_disabled_password_cleared"
    assert "synthetic-private-error" not in str(events)


def test_no_attempt_means_no_role_write():
    c = Connection()
    access.WindowAccess().close(c, record=lambda **event: None)
    assert c.calls == []


class Storage:
    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []

    def __getattr__(self, name):
        def call(**kwargs):
            self.calls.append((name, kwargs))
            assert kwargs["ExpectedBucketOwner"] == "335523638354"
            if name == "head_bucket":
                return {}
            if name == "get_bucket_location":
                return {
                    "LocationConstraint": (
                        "wrong" if self.failure == "region" else "ap-south-1"
                    )
                }
            if name == "get_public_access_block":
                return {
                    "PublicAccessBlockConfiguration": {
                        k: self.failure != "block"
                        for k in (
                            "BlockPublicAcls",
                            "IgnorePublicAcls",
                            "BlockPublicPolicy",
                            "RestrictPublicBuckets",
                        )
                    }
                }
            if name == "get_bucket_policy_status":
                return {"PolicyStatus": {"IsPublic": self.failure == "public"}}
            if name == "get_bucket_encryption":
                return {
                    "ServerSideEncryptionConfiguration": {
                        "Rules": [
                            {
                                "ApplyServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": (
                                        "aws:kms"
                                        if self.failure == "encryption"
                                        else "AES256"
                                    )
                                }
                            }
                        ]
                    }
                }
            if name == "get_bucket_ownership_controls":
                return {
                    "OwnershipControls": {
                        "Rules": [
                            {
                                "ObjectOwnership": (
                                    "ObjectWriter"
                                    if self.failure == "owner"
                                    else "BucketOwnerEnforced"
                                )
                            }
                        ]
                    }
                }
            if name == "list_objects_v2":
                assert (
                    kwargs["MaxKeys"] == 1
                    and kwargs["Prefix"] == "id01/next06-reference-42-v1/"
                )
                return {
                    "KeyCount": 1 if self.failure == "occupied" else 0,
                    "IsTruncated": False,
                }
            pytest.fail("Unexpected provider operation")

        return call


@pytest.mark.parametrize(
    "failure", ["region", "block", "public", "encryption", "owner", "occupied"]
)
def test_storage_refuses_mismatch_without_puts(failure):
    s3 = Storage(failure)
    target = SimpleNamespace(
        bucket="clip-test-listings-images-ap-south-1-id01",
        account="335523638354",
        region="ap-south-1",
        prefix="id01/next06-reference-42-v1",
    )
    with pytest.raises(access.LoadAccessRefused):
        access.storage_preflight(s3, target)
    assert not any(name.startswith(("put_", "delete_")) for name, _ in s3.calls)


def test_empty_private_bucket_inspection_passes():
    s3 = Storage()
    target = SimpleNamespace(
        bucket="clip-test-listings-images-ap-south-1-id01",
        account="335523638354",
        region="ap-south-1",
        prefix="id01/next06-reference-42-v1",
    )
    assert access.storage_preflight(s3, target)["objects_before"] == 0
    assert len(s3.calls) == 7


@pytest.mark.parametrize(
    "raw,group",
    [
        (b"p123\nn*:5432\n", 9),
        (b"p123\nn0.0.0.0:5432\n", 9),
        (b"p123\nn127.0.0.1:5432\n", 8),
        (b"p123\n", 9),
    ],
)
def test_listener_cannot_expose_database_or_adopt_another_process(raw, group):
    with pytest.raises(access.LoadAccessRefused):
        access.verify_owned_listener(raw, group, lambda pid: 9)


def test_owned_loopback_listener_passes():
    access.verify_owned_listener(b"p123\nn127.0.0.1:5432\n", 9, lambda pid: 9)


def bounded_storage():
    calls = []
    client = SimpleNamespace(
        put_object=lambda **kwargs: calls.append(kwargs) or {},
        get_object=lambda **kwargs: calls.append(kwargs) or {},
    )
    target = SimpleNamespace(
        bucket="bucket", account="335523638354", prefix="id01/next06-run"
    )
    return (
        access.BoundedStorage(
            client, target, {"id01/next06-run/key"}, deadline=100, clock=lambda: 1
        ),
        calls,
    )


def test_bounded_storage_requires_exact_key_owner_create_only_and_new_put():
    s3, calls = bounded_storage()
    args = {
        "Bucket": "bucket",
        "ExpectedBucketOwner": "335523638354",
        "Key": "id01/next06-run/key",
    }
    with pytest.raises(access.LoadAccessRefused):
        s3.get_object(**args)
    with pytest.raises(access.LoadAccessRefused):
        s3.put_object(**args)
    with pytest.raises(access.LoadAccessRefused):
        s3.put_object(**(args | {"Key": "other/key", "IfNoneMatch": "*"}))
    with pytest.raises(access.LoadAccessRefused):
        s3.put_object(**(args | {"ExpectedBucketOwner": "other", "IfNoneMatch": "*"}))
    assert calls == []
    s3.put_object(**args, IfNoneMatch="*")
    s3.get_object(**args)
    with pytest.raises(access.LoadAccessRefused):
        s3.put_object(**args, IfNoneMatch="*")
    with pytest.raises(access.LoadAccessRefused):
        s3.delete_object(**args)
    assert len(calls) == 2


@pytest.mark.parametrize("limit", ["time", "calls"])
def test_bounded_storage_limits_before_dispatch(limit):
    s3, calls = bounded_storage()
    if limit == "time":
        s3.deadline = 0
    else:
        s3.calls = 2008
    with pytest.raises(access.LoadAccessRefused):
        s3.put_object(
            Bucket="bucket",
            ExpectedBucketOwner="335523638354",
            Key="id01/next06-run/key",
            IfNoneMatch="*",
        )
    assert calls == []


@pytest.mark.parametrize(
    "success,stopped,pending,expected",
    [
        (True, True, False, "cloud_load_passed_resources_stopped"),
        (False, True, False, "cloud_load_failed_resources_stopped"),
        (True, False, False, "cleanup_pending_operator_attention"),
        (True, True, True, "cleanup_pending_operator_attention"),
    ],
)
def test_load_closeout_requires_actual_counts_and_cleanups(
    success, stopped, pending, expected
):
    report = {
        "resource_start_attempts": {"rds": True, "ec2": True},
        "cleanup": {
            "rds_stopped": stopped,
            "host_stopped": True,
            "loader_cleanup_pending": pending,
            "loader_disabled_password_cleared": True,
            "owned_tunnel_exited": True,
            "owned_session_terminated": True,
        },
        "load_passed": success,
        "load_result": {
            "objects_verified": 1000,
            "users_verified": 5000,
            "listings_verified": 1000,
        },
    }
    assert access.load_window_outcome(report) == expected


def test_success_without_loader_or_tunnel_cleanup_is_not_accepted():
    report = {
        "resource_start_attempts": {"rds": True, "ec2": True},
        "cleanup": {"rds_stopped": True, "host_stopped": True},
        "load_passed": True,
    }
    assert access.load_window_outcome(report) == "cleanup_pending_operator_attention"
