"""Check the local image builder using a fake Docker CLI only."""

import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path("scripts/evaluation/build_lambda_image.sh").resolve()
REVISION = "a" * 40


@pytest.fixture
def fake_docker(tmp_path):
    docker = tmp_path / "docker"
    docker.write_text("""#!/bin/bash
printf '%s\\n' "$*" >> "$FAKE_DOCKER_LOG"
if [[ $1 == context ]]; then printf 'unix:///tmp/fake-docker.sock\\n'; exit; fi
if [[ $* == *'org.opencontainers.image.revision'* && $* == *'image inspect'* ]]; then
  printf '%s\\n' "$FAKE_IMAGE_REVISION"; exit
fi
if [[ $* == *'image inspect'* && $* == *'clip-exp03-lambda:'* && $* != *'--format'* ]]; then exit 1; fi
if [[ $* == *'image inspect'* && $* == *'--format'* ]]; then printf 'linux/amd64\\n'; exit; fi
if [[ $* == *' build '* ]]; then exit 0; fi
exit 2
""")
    docker.chmod(0o755)
    log = tmp_path / "docker-calls.log"
    env = {
        **os.environ,
        "PATH": str(tmp_path) + ":/usr/bin:/bin",
        "FAKE_DOCKER_LOG": str(log),
        "FAKE_IMAGE_REVISION": REVISION,
    }
    return env, log


def run_builder(env):
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "clip-exp03-hybrid:local-aaaaaaa",
            "clip-exp03-lambda:local-aaaaaaa",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_declared_matching_revision_is_carried_to_offline_build(fake_docker):
    env, log = fake_docker
    result = run_builder(env)
    assert result.returncode == 0, result.stderr
    calls = log.read_text()
    assert f"--label org.opencontainers.image.revision={REVISION}" in calls
    assert "--pull=false --network=none --platform linux/amd64" in calls
    # Dockerfile.lambda supplies the sha256: prefix in its FROM instruction.
    assert (
        "--build-arg LWA_DIGEST=17cfd08eff1dfea3f6a9a1e9c65fdac80aa4919b6085e746615530f43f57d2f1"
        in calls
    )
    assert "LWA_DIGEST=sha256:" not in calls


@pytest.mark.parametrize("revision", ["", "a" * 7, "b" * 40, "a" * 39 + "z"])
def test_missing_or_mismatched_revision_refuses_before_build(fake_docker, revision):
    env, log = fake_docker
    env["FAKE_IMAGE_REVISION"] = revision
    result = run_builder(env)
    assert result.returncode == 2
    assert "matching full OCI revision label" in result.stderr
    assert " build " not in f" {log.read_text()} "
