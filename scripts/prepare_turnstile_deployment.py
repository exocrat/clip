"""Prepare public runtime configuration; optionally publish a secret after approval.

Default mode is entirely local. The opt-in AWS write creates one exact Standard
SecureString without overwrite. Secret values never enter arguments, output,
Terraform or image builds. See docs/environment/turnstile-deployment.md.
"""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import shutil
import subprocess

ACCOUNT = "335523638354"
REGION = "ap-south-1"
PARAMETER = "/clip/test/turnstile/secret-key"
PARAMETER_ARN = f"arn:aws:ssm:{REGION}:{ACCOUNT}:parameter{PARAMETER}"


def read_keys(path: Path) -> tuple[str, str]:
    """Read a small owner-private local JSON file; never expose invalid input."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Use a regular private keys file, not a symbolic link.")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Restrict the keys file to its owner with chmod 600.")
    with path.open() as source:
        raw = source.read(16385)
    if len(raw) > 16384:
        raise ValueError("Invalid keys file.")
    try:
        data = json.loads(raw)
        site, secret = data["site_key"], data["secret_key"]
        if (
            not all(
                isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{10,256}", value)
                for value in (site, secret)
            )
            or site == secret
        ):
            raise ValueError
        return site, secret
    except Exception:
        raise ValueError(
            "Invalid keys file; copy the matching production pair."
        ) from None


def publish_secret(secret: str, profile: str, runner=None, aws_cli=None) -> int:
    """Create one parameter via the existing CLI login, after an account check.

    The secret uses a seekable Linux memory-only file descriptor, never
    arguments or a temporary disk payload file. Capture and suppress CLI diagnostics. No overwrite, rotation
    or automatic retry; inspect AWS privately after an uncertain failure.
    """
    try:
        runner = runner or subprocess.run
        aws_cli = aws_cli or shutil.which("aws")
        if not aws_cli:
            candidate = Path.home() / ".local/bin/aws"
            if candidate.is_file() and os.access(candidate, os.X_OK):
                aws_cli = str(candidate)
        if not aws_cli:
            raise ValueError
        env = dict(
            os.environ, AWS_CLI_AUTO_PROMPT="off", AWS_PAGER="", AWS_MAX_ATTEMPTS="1"
        )

        def request(service: str, operation: str, payload=None):
            """Use fixed regional HTTPS endpoints and bounded captured child I/O."""
            command = [
                aws_cli,
                service,
                operation,
                "--profile",
                profile,
                "--region",
                REGION,
                "--endpoint-url",
                f"https://{service}.{REGION}.amazonaws.com",
                "--output",
                "json",
                "--no-cli-pager",
                "--cli-connect-timeout",
                "5",
                "--cli-read-timeout",
                "10",
            ]
            descriptor = None
            try:
                if payload is not None:
                    # The CLI may read JSON more than once; stdin is not seekable.
                    # memfd keeps a reusable payload in RAM without a disk file.
                    descriptor = os.memfd_create("clip-runtime-secret", os.MFD_CLOEXEC)
                    os.write(descriptor, json.dumps(payload).encode())
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    command += [
                        "--cli-input-json",
                        f"file:///proc/self/fd/{descriptor}",
                    ]
                response = runner(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                    pass_fds=(descriptor,) if descriptor is not None else (),
                )
            finally:
                if descriptor is not None:
                    os.close(descriptor)
            if response.returncode != 0:
                raise ValueError
            return json.loads(response.stdout)

        if request("sts", "get-caller-identity").get("Account") != ACCOUNT:
            raise ValueError
        result = request(
            "ssm",
            "put-parameter",
            {
                "Name": PARAMETER,
                "Description": "CLIP production Turnstile verifier key; runtime only.",
                "Type": "SecureString",
                "Tier": "Standard",
                "Value": secret,
                "Overwrite": False,
            },
        )
        return int(result["Version"])
    except Exception:
        raise ValueError(
            "Secret was not confirmed created. Check the AWS identity, permissions "
            "and whether the parameter already exists. Nothing is overwritten; "
            "inspect privately before retrying."
        ) from None


def prepare(keys: Path, output: Path, profile: str | None = None) -> None:
    """Write a shareable public tfvars fragment and non-secret handoff receipt."""
    site, secret = read_keys(keys)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    variables = output / "turnstile.tfvars.json"
    content = json.dumps({"turnstile_site_key": site}, indent=2) + "\n"
    if variables.exists() and variables.read_text() != content:
        raise ValueError(
            "Output already contains a different site key; use a new directory."
        )
    # Only an explicitly supplied profile from --write-secret activates AWS calls.
    version = publish_secret(secret, profile) if profile else None
    variables.write_text(content)
    receipt = {
        "account": ACCOUNT,
        "region": REGION,
        "parameter_name": PARAMETER,
        "parameter_arn": PARAMETER_ARN,
        "secret_included": False,
        "aws_write_performed": version is not None,
        "parameter_version": version,
        "runtime_settings": ["CLIP_TURNSTILE_SITE_KEY", "CLIP_TURNSTILE_SECRET_KEY"],
        "warning": "Local preparation alone does not create the AWS parameter or deploy a fix.",
    }
    (output / "handoff.json").write_text(json.dumps(receipt, indent=2) + "\n")


def main() -> int:
    """Keep local preparation the default; require explicit AWS-write selection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keys-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--write-secret", action="store_true")
    parser.add_argument("--profile")
    args = parser.parse_args()
    if args.write_secret != bool(args.profile):
        parser.error(
            "Use --write-secret and --profile together, only after AWS-write approval."
        )
    os.umask(0o077)
    try:
        prepare(
            args.keys_file, args.output, args.profile if args.write_secret else None
        )
    except OSError, ValueError:
        print(
            "Preparation failed; check file permissions, matching keys and AWS prerequisites privately. No secret output."
        )
        return 1
    print("Prepared public tfvars and a non-secret handoff receipt.")
    print(
        "AWS parameter creation requested."
        if args.write_secret
        else "Local preparation only; no AWS calls or deployment."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
