"""Cloud adapter guard/media/uncertain-write tests; no AWS or cloud DB connections.

Botocore validates exact S3 request shapes; scripted DB rows exercise refusal
ordering only. Real shared insertion SQL is checked by the native local rehearsal.
None of these fixtures is evidence of deployed Identity/S3/IAM acceptance.
"""

from base64 import b64encode
from contextlib import nullcontext
from dataclasses import replace
import io
import json
from pathlib import Path
from types import SimpleNamespace

import boto3
from botocore.stub import Stubber
import pytest

from data.generators import reference_cloud as cloud
from data.tests.test_reference import inputs, build


@pytest.fixture
def bundle(inputs):
    return build(inputs[0])


@pytest.fixture
def target(bundle):
    return cloud.CloudTarget(
        account=cloud.ACCOUNT,
        region=cloud.REGION,
        profile="project-operator",
        host="reference.example.invalid",
        port=5432,
        database="clip_reference",
        role="clip_reference_loader",
        server_version_num="180006",
        bucket="clip-reference-private",
        prefix="listings/next06-test-run",
        source_revision=bundle["manifest"]["source_binding"]["base_revision"],
        logical_data_fingerprint=bundle["manifest"]["logical_data_fingerprint"],
        sensitive_threshold_paise=bundle["manifest"][
            "sensitive_purchase_threshold_paise"
        ],
    )


def secret(target, **changes):
    fields = dict(
        host=target.host,
        port=target.port,
        dbname=target.database,
        user=target.role,
        sslmode="verify-full",
        sslrootcert="/approved/ca.pem",
    )
    fields.update(changes)
    return " ".join(f"{k}={v}" for k, v in fields.items())


@pytest.mark.parametrize(
    "change",
    [
        {"account": "387743104934"},
        {"region": "us-east-1"},
        {"host": "one,two"},
        {"database": "postgres"},
        {"role": "rdsadmin"},
        {"prefix": "listings"},
        {"prefix": "listings/../next06-run"},
        {"prefix": "/listings/next06-run"},
        {"port": True},
        {"source_revision": "unaccepted"},
        {"bucket": ""},
    ],
)
def test_unbound_or_alternate_targets_refused(target, change):
    with pytest.raises(cloud.CloudLoadRejected):
        replace(target, **change)


@pytest.mark.parametrize(
    "change",
    [
        {"host": "other.example.invalid"},
        {"sslmode": "require"},
        {"user": "postgres"},
        {"options": "unsafe"},
    ],
)
def test_dsn_mismatch_tls_and_indirection_refused(target, bundle, change):
    with pytest.raises(cloud.CloudLoadRejected):
        cloud.validate_binding(target, bundle, secret(target, **change))


def test_data_binding_and_key_convention(target, bundle):
    cloud.validate_binding(target, bundle, secret(target))
    image = bundle["image_plan"][0]
    assert (
        target.object_key_for(image["upload_id"])
        == f"{target.prefix}/{image['upload_id']}"
    )
    with pytest.raises(ValueError):
        target.object_key_for("../foreign")
    with pytest.raises(cloud.CloudLoadRejected):
        cloud.validate_binding(
            replace(target, logical_data_fingerprint="sha256:" + "0" * 64),
            bundle,
            secret(target),
        )


class GuardDatabase:
    """Only explicit preflight rows; not a fake successful schema transaction."""

    def __init__(self, target, bundle, failure=None):
        self.target, self.bundle, self.failure = target, bundle, failure
        self.info = SimpleNamespace(host=target.host, port=target.port)
        self.pgconn = SimpleNamespace(ssl_in_use=failure != "tls")
        if failure == "host":
            self.info.host = "other.example.invalid"

    def execute(self, statement):
        if "pg_roles" in statement:
            return SimpleNamespace(
                fetchone=lambda: (
                    (True, False, False)
                    if self.failure == "privileges"
                    else (False, False, False)
                )
            )
        if "embedding_pipelines" in statement:
            return SimpleNamespace(
                fetchone=lambda: (1,) if self.failure == "pipeline" else (0,)
            )
        if "current_database()" in statement:
            row = (
                self.target.database,
                self.target.role,
                self.target.role,
                self.target.server_version_num,
            )
            if self.failure == "login":
                row = (
                    self.target.database,
                    self.target.role,
                    "other_login",
                    self.target.server_version_num,
                )
            return SimpleNamespace(fetchone=lambda: row)
        if "schema_migrations" in statement:
            versions = self.bundle["manifest"]["source_binding"]["migration_versions"]
            return [
                (v,) for v in (versions[:-1] if self.failure == "schema" else versions)
            ]
        return SimpleNamespace(
            fetchone=lambda: (
                (1, 0, 0, 0) if self.failure == "nonempty" else (0, 0, 0, 0)
            )
        )


@pytest.mark.parametrize(
    "failure", ["tls", "host", "login", "schema", "nonempty", "privileges", "pipeline"]
)
def test_actual_database_drift_refused_before_upload(target, bundle, failure):
    with pytest.raises(cloud.CloudLoadRejected):
        cloud.guard_database(GuardDatabase(target, bundle, failure), target, bundle)


@pytest.mark.parametrize(
    "identity",
    [
        {"Account": "387743104934", "Arn": "arn:aws:iam::387743104934:root"},
        {"Account": cloud.ACCOUNT, "Arn": f"arn:aws:iam::{cloud.ACCOUNT}:root"},
        {"Account": cloud.ACCOUNT, "Arn": "unexpected"},
    ],
)
def test_wrong_identity_cannot_reach_storage_or_sql(target, bundle, inputs, identity):
    def forbidden(*args, **kwargs):
        pytest.fail("Wrong identity reached a provider")

    with pytest.raises(cloud.CloudLoadRejected):
        cloud.load_cloud(
            target=target,
            bundle=bundle,
            image_root=inputs[0],
            secret=secret(target),
            sts=SimpleNamespace(get_caller_identity=lambda: identity),
            s3=SimpleNamespace(head_bucket=forbidden),
            connect=forbidden,
            ledger=None,
            execute=True,
        )


def test_no_implicit_execute():
    with pytest.raises(cloud.CloudLoadRejected, match="explicit_execution"):
        cloud.load_cloud(
            target=None,
            bundle=None,
            image_root=None,
            secret=None,
            sts=None,
            s3=None,
            connect=None,
            ledger=None,
        )


@pytest.mark.parametrize(
    "failure", [None, "put_uncertain", "wrong_bytes", "wrong_encryption"]
)
def test_create_only_real_byte_contract_and_failed_put_ledger(
    target, bundle, inputs, tmp_path, failure
):
    image = bundle["image_plan"][0]
    content = (inputs[0] / image["source_relative_path"]).read_bytes()
    key = target.object_key_for(image["upload_id"])
    client = boto3.client(
        "s3",
        region_name=cloud.REGION,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    params = dict(
        Bucket=target.bucket,
        Key=key,
        ExpectedBucketOwner=cloud.ACCOUNT,
        Body=content,
        ContentType=image["media_type"],
        IfNoneMatch="*",
        ChecksumSHA256=b64encode(bytes.fromhex(image["sha256"])).decode(),
    )
    stream = io.BytesIO(b"corrupt" if failure == "wrong_bytes" else content)
    path = tmp_path / "ledger.jsonl"
    ledger = cloud.Ledger(path)
    try:
        with Stubber(client) as stub:
            if failure == "put_uncertain":
                stub.add_client_error(
                    "put_object",
                    service_error_code="RequestTimeout",
                    expected_params=params,
                )
            else:
                stub.add_response("put_object", {}, params)
                stub.add_response(
                    "get_object",
                    {
                        "Body": stream,
                        "ContentLength": len(content),
                        "ServerSideEncryption": (
                            "aws:kms" if failure == "wrong_encryption" else "AES256"
                        ),
                        "ContentType": image["media_type"],
                    },
                    {
                        "Bucket": target.bucket,
                        "Key": key,
                        "ExpectedBucketOwner": cloud.ACCOUNT,
                    },
                )
            action = lambda: cloud.upload_verified(
                client, target, {"image_plan": [image]}, inputs[0], ledger
            )
            if failure:
                with pytest.raises(Exception):
                    action()
            else:
                assert action() == {
                    "objects_verified": 1,
                    "logical_object_bytes": len(content),
                }
            stub.assert_no_pending_responses()
    finally:
        ledger.close()
        client.close()
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert events[0]["state"] == "put_planned"
    assert len(events) == (1 if failure else 2)
    if failure != "put_uncertain":
        assert stream.closed
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        cloud.Ledger(path)


def test_media_failure_cannot_commit_rows(
    target, bundle, inputs, tmp_path, monkeypatch
):
    def failed_media(*args):
        raise cloud.CloudLoadRejected("uploaded_bytes_mismatch")

    def forbidden(*args, **kwargs):
        pytest.fail("Unverified media reached SQL insertion")

    monkeypatch.setattr(cloud, "upload_verified", failed_media)
    monkeypatch.setattr(cloud, "insert_rows", forbidden)
    ledger = cloud.Ledger(tmp_path / "events.jsonl")
    try:
        with pytest.raises(cloud.CloudLoadRejected):
            cloud.load_cloud(
                target=target,
                bundle=bundle,
                image_root=inputs[0],
                secret=secret(target),
                sts=SimpleNamespace(
                    get_caller_identity=lambda: {
                        "Account": cloud.ACCOUNT,
                        "Arn": f"arn:aws:iam::{cloud.ACCOUNT}:user/operator",
                    }
                ),
                s3=SimpleNamespace(head_bucket=lambda **kwargs: None),
                connect=lambda *args, **kwargs: nullcontext(
                    GuardDatabase(target, bundle)
                ),
                ledger=ledger,
                execute=True,
            )
    finally:
        ledger.close()


def test_offline_plan_never_constructs_cloud_clients(
    bundle, tmp_path, monkeypatch, capsys
):
    from data.generators import files, reference

    monkeypatch.setattr(reference, "read_reference", lambda *args, **kwargs: bundle)
    monkeypatch.setattr(files, "_run_path", lambda name: tmp_path)
    monkeypatch.setattr(files, "_read_json", lambda path: bundle)

    def forbidden(*args, **kwargs):
        pytest.fail("Offline plan constructed an AWS session")

    monkeypatch.setattr(boto3, "Session", forbidden)
    assert cloud.main(["plan", "--name", "fixture", "--image-root", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["target"] is None and report["account"] == cloud.ACCOUNT
