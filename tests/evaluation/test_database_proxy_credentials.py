"""Credential preparation binds private inputs without creating cloud resources."""

from datetime import UTC, datetime, timedelta
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts.evaluation import database_proxy_credentials as subject


def fake_session():
    """Expose only read methods, recording when plaintext is actually requested."""
    calls = []
    state = {"version": 2}

    class Missing(Exception):
        pass

    def missing(**_):
        raise Missing

    def parameter(Name, WithDecryption):
        calls.append((Name, WithDecryption))
        role = next(role for path, role in subject.SOURCES.values() if path == Name)
        return {
            "Parameter": {
                "Type": "SecureString",
                "Version": state["version"],
                "Value": (
                    f"postgresql://{role}:synthetic%3Aonly@source.example:5432/{subject.DATABASE_NAME}?sslmode=verify-full&sslrootcert=system"
                    if WithDecryption
                    else "ciphertext-placeholder"
                ),
            }
        }

    clients = {
        "sts": SimpleNamespace(
            get_caller_identity=lambda: {
                "Account": subject.ACCOUNT,
                "Arn": f"arn:aws:iam::{subject.ACCOUNT}:user/surajs2",
            }
        ),
        "rds": SimpleNamespace(
            describe_db_instances=lambda **_: {
                "DBInstances": [
                    {
                        "DBInstanceStatus": "available",
                        "PubliclyAccessible": False,
                        "Endpoint": {"Address": "source.example"},
                    }
                ]
            }
        ),
        "ssm": SimpleNamespace(get_parameter=parameter),
        "secretsmanager": SimpleNamespace(
            describe_secret=missing,
            exceptions=SimpleNamespace(ResourceNotFoundException=Missing),
        ),
    }
    return SimpleNamespace(client=lambda name: clients[name]), calls, state


def prepared(session):
    return json.dumps(
        subject.prepare(session, datetime.now(UTC) + timedelta(hours=1)), sort_keys=True
    ).encode()


def test_metadata_only_preparation_then_exact_private_handoff():
    session, calls, _ = fake_session()
    raw = prepared(session)
    assert len(calls) == 3 and not any(decrypt for _, decrypt in calls)
    assert b"synthetic" not in raw and b"ciphertext" not in raw
    values = subject.terraform_passwords(session, raw, hashlib.sha256(raw).hexdigest())
    assert values == {name: "synthetic:only" for name in subject.SOURCES}
    assert sum(decrypt for _, decrypt in calls) == 3


def test_source_version_drift_refuses_decryption():
    session, calls, state = fake_session()
    raw = prepared(session)
    state["version"] = 3
    with pytest.raises(ValueError, match="credential_source_plan_drift"):
        subject.terraform_passwords(session, raw, hashlib.sha256(raw).hexdigest())
    assert not any(decrypt for _, decrypt in calls)


def test_wrong_digest_refuses_all_provider_calls():
    session, calls, _ = fake_session()
    with pytest.raises(ValueError, match="source_plan_digest_mismatch"):
        subject.terraform_passwords(session, b"{}", "0" * 64)
    assert calls == []


@pytest.mark.parametrize(
    "suffix",
    ["&sslmode=disable", "&host=", "&options=-cfoo", "&unexpected", "#fragment"],
)
def test_ambiguous_source_values_are_redacted(suffix):
    value = (
        f"postgresql://role:synthetic-only@source.example/{subject.DATABASE_NAME}?sslmode=verify-full&sslrootcert=system"
        + suffix
    )
    with pytest.raises(ValueError) as error:
        subject.validate_credentials(value, "role", "source.example")
    assert str(error.value) == "source_credential_binding_invalid"


def test_private_output_never_overwrites(tmp_path):
    output = tmp_path / "plan.json"
    subject.write_new(output, {"metadata": True})
    assert output.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        subject.write_new(output, {"changed": True})
    assert json.loads(output.read_text()) == {"metadata": True}
