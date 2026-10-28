"""Run proxy mock plans in a fresh copy without credentials or any backend.

Only provider schemas may be downloaded. Terraform uses a mock AWS provider and
synthetic inputs; no real plan/apply, state read or cloud request is performed.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "infra/terraform/shared/test"


def main() -> int:
    """Keep the fixed mock target, version and credentials/backend exclusions explicit."""
    binary = os.environ.get("TERRAFORM_BIN", "terraform")
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ["HOME"],
        "TF_CLI_CONFIG_FILE": "/dev/null",
        "TF_IN_AUTOMATION": "1",
        "CHECKPOINT_DISABLE": "1",
        "AWS_CONFIG_FILE": "/dev/null",
        "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
        "AWS_EC2_METADATA_DISABLED": "true",
    }
    expected = (ROOT / ".terraform-version").read_text().strip()
    version = subprocess.run(
        [binary, "version", "-json"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    if json.loads(version.stdout)["terraform_version"] != expected:
        raise ValueError("Use the project-pinned Terraform version")
    with TemporaryDirectory(prefix="clip-id01-proxy-mocks-") as directory:
        target = Path(directory) / "root"
        shutil.copytree(
            SOURCE,
            target,
            ignore=shutil.ignore_patterns(
                ".terraform", "*.tfstate*", "*.tfvars*", "*.tfplan*"
            ),
        )
        path = target / "versions.tf"
        config, replaced = re.subn(r'  backend "s3" \{[^}]*\}\n', "", path.read_text())
        if replaced != 1 or re.search(r'\bbackend\s+"', config):
            raise ValueError("Expected exactly the fixed removable S3 backend")
        path.write_text(config)
        tests = (target / "tests/identity_https_proxy.tftest.hcl").read_text()
        if tests.count('mock_provider "aws"') != 1:
            raise ValueError("The fixed AWS mock declaration must be present")
        for arguments in (
            [
                "init",
                "-backend=false",
                "-input=false",
                "-lockfile=readonly",
                "-no-color",
            ],
            ["test", "-filter=tests/identity_https_proxy.tftest.hcl", "-no-color"],
        ):
            result = subprocess.run(
                [binary, f"-chdir={target}", *arguments], env=env, timeout=120
            )
            if result.returncode:
                return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
