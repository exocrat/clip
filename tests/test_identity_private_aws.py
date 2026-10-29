"""Real local child-process payload/privacy tests; no AWS requests or credentials."""

import os
import subprocess
import sys

import pytest

from scripts import identity_private_aws as bridge

MARKER = "synthetic-private-payload"
PAYLOAD = {
    "Name": "/clip/test/conversations/database-url",
    "Value": MARKER,
    "Type": "SecureString",
    "Tier": "Standard",
    "KeyId": "alias/aws/ssm",
    "Overwrite": False,
}


def child_runner(monkeypatch, *, fail=False):
    """Replace only the external CLI process; actually inherit/read the RAM fd."""
    original = subprocess.run
    observed = []

    def run(args, **kwargs):
        assert MARKER not in " ".join(args)
        assert "input" not in kwargs
        descriptor = kwargs["pass_fds"][0]
        observed.append(descriptor)
        code = """import json,os,stat,sys
p=sys.argv[1].removeprefix("file://")
fd=int(p.rsplit("/",1)[1])
assert stat.S_IMODE(os.fstat(fd).st_mode)==0o600
assert "memfd:" in os.readlink(p)
with open(p) as f: first=json.load(f)
with open(p) as f: second=json.load(f)
assert first==second and first["Value"]=="synthetic-private-payload"
if sys.argv[2]=="True":
 print(first["Value"],file=sys.stderr)
 sys.exit(1)
print(json.dumps({"verified":True}))
"""
        return original(
            [
                sys.executable,
                "-c",
                code,
                args[args.index("--cli-input-json") + 1],
                str(fail),
            ],
            **kwargs,
        )

    monkeypatch.setattr(bridge.subprocess, "run", run)
    return observed


def test_private_payload_reopens_in_child_without_argv_or_disk(monkeypatch):
    """Actual descriptor input survives repeated reads and closes after success."""
    observed = child_runner(monkeypatch)
    assert bridge.call("parameter_create", PAYLOAD, allow_write=True) == {
        "verified": True
    }
    with pytest.raises(OSError):
        os.fstat(observed[0])


def test_failure_hides_private_stderr_and_closes_descriptor(monkeypatch):
    """A CLI failure cannot reflect the private payload in the public exception."""
    observed = child_runner(monkeypatch, fail=True)
    with pytest.raises(bridge.PrivateAwsFailure) as error:
        bridge.call("parameter_create", PAYLOAD, allow_write=True)
    assert MARKER not in str(error.value)
    assert error.value.__suppress_context__
    with pytest.raises(OSError):
        os.fstat(observed[0])


def test_unknown_operation_or_unapproved_write_never_launches(monkeypatch):
    """The helper has no implicit write or arbitrary-operation path."""

    def forbidden(*args, **kwargs):
        pytest.fail("No process should launch")

    monkeypatch.setattr(bridge.subprocess, "run", forbidden)
    for operation in ("parameter_create", "delete_everything"):
        with pytest.raises(bridge.PrivateAwsFailure):
            bridge.call(operation, {})


def test_wrong_parameter_or_overwrite_never_launches(monkeypatch):
    """Even explicit write opt-in cannot overwrite or target another secret."""

    def forbidden(*args, **kwargs):
        pytest.fail("No process should launch")

    monkeypatch.setattr(bridge.subprocess, "run", forbidden)
    for changes in (
        {"Name": "/clip/test/another-secret"},
        {"Overwrite": True},
        {"Type": "String"},
    ):
        with pytest.raises(bridge.PrivateAwsFailure):
            bridge.call("parameter_create", PAYLOAD | changes, allow_write=True)
