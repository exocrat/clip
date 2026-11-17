"""Secret handoff guards: synthetic keys and fake CLI processes; never AWS calls."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import prepare_turnstile_deployment as module

SITE = "synthetic-public-widget-key"
SECRET = "synthetic-private-verifier-key"


@pytest.fixture
def keys(tmp_path):
    path = tmp_path / "keys.json"
    path.write_text(json.dumps({"site_key": SITE, "secret_key": SECRET}))
    path.chmod(0o600)
    return path


def test_default_prepares_public_files_without_aws(keys, tmp_path, monkeypatch):
    def forbidden(*args):
        raise AssertionError("No AWS calls in local preparation")

    monkeypatch.setattr(module, "publish_secret", forbidden)
    output = tmp_path / "handoff"
    module.prepare(keys, output)
    assert json.loads((output / "turnstile.tfvars.json").read_text()) == {
        "turnstile_site_key": SITE
    }
    receipt = json.loads((output / "handoff.json").read_text())
    assert receipt["aws_write_performed"] is False
    assert receipt["parameter_arn"] == module.PARAMETER_ARN
    assert SECRET not in "".join(path.read_text() for path in output.iterdir())


@pytest.mark.parametrize("mode", ["public", "symlink", "malformed", "oversized"])
def test_bad_key_sources_refuse_safely(keys, tmp_path, mode):
    if mode == "public":
        keys.chmod(0o644)
    elif mode == "symlink":
        link = tmp_path / "linked"
        link.symlink_to(keys)
        keys = link
    elif mode == "malformed":
        keys.write_text('{"private":"' + SECRET + '"}')
    else:
        keys.write_text("x" * 16385)
    with pytest.raises(ValueError) as error:
        module.read_keys(keys)
    assert SECRET not in str(error.value)


def runner(account, calls, *, fail=False):
    """Fake the CLI process without reading credentials or making requests."""

    def execute(command, **kwargs):
        assert SECRET not in " ".join(command)
        assert kwargs["timeout"] == 30 and kwargs["capture_output"] is True
        assert kwargs["env"]["AWS_MAX_ATTEMPTS"] == "1"
        service, operation = command[1:3]
        assert command[command.index("--profile") + 1] == "synthetic-profile"
        assert (
            command[command.index("--endpoint-url") + 1]
            == f"https://{service}.{module.REGION}.amazonaws.com"
        )
        payload = None
        if kwargs["pass_fds"]:
            descriptor = kwargs["pass_fds"][0]
            payload = os.read(descriptor, 16384).decode()
            assert command[-2:] == [
                "--cli-input-json",
                f"file:///proc/self/fd/{descriptor}",
            ]
        calls.append((service, payload))
        if service == "sts":
            assert operation == "get-caller-identity"
            return SimpleNamespace(
                returncode=0, stdout=json.dumps({"Account": account})
            )
        assert service == "ssm" and operation == "put-parameter"
        return SimpleNamespace(
            returncode=1 if fail else 0,
            stdout=json.dumps({"Version": 1}),
            stderr=SECRET,
        )

    return execute


def test_write_verifies_account_and_creates_only_exact_secure_parameter():
    calls = []
    assert (
        module.publish_secret(
            SECRET, "synthetic-profile", runner(module.ACCOUNT, calls), "synthetic-aws"
        )
        == 1
    )
    write = json.loads(calls[1][1])
    assert write["Name"] == "/clip/test/turnstile/secret-key"
    assert write["Type"] == "SecureString" and write["Tier"] == "Standard"
    assert write["Value"] == SECRET and write["Overwrite"] is False


def test_wrong_account_never_requests_secret_write():
    calls = []
    with pytest.raises(ValueError):
        module.publish_secret(
            SECRET, "synthetic-profile", runner("000000000000", calls), "synthetic-aws"
        )
    assert calls == [("sts", None)]


def test_cli_failure_does_not_expose_secret_or_retry():
    calls = []
    with pytest.raises(ValueError) as error:
        module.publish_secret(
            SECRET,
            "synthetic-profile",
            runner(module.ACCOUNT, calls, fail=True),
            "synthetic-aws",
        )
    assert SECRET not in str(error.value)
    assert len([service for service, _ in calls if service == "ssm"]) == 1


def test_output_conflict_refuses_before_any_aws_write(keys, tmp_path, monkeypatch):
    output = tmp_path / "handoff"
    output.mkdir()
    (output / "turnstile.tfvars.json").write_text("different")

    def forbidden(*args):
        raise AssertionError("Conflict must stop before writing AWS")

    monkeypatch.setattr(module, "publish_secret", forbidden)
    with pytest.raises(ValueError):
        module.prepare(keys, output, "synthetic-profile")


def test_cli_requires_both_write_flag_and_profile(monkeypatch, keys, tmp_path):
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepare",
            "--keys-file",
            str(keys),
            "--output",
            str(tmp_path / "out"),
            "--write-secret",
        ],
    )
    with pytest.raises(SystemExit) as result:
        module.main()
    assert result.value.code == 2
