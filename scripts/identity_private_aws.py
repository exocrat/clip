"""Operator-only AWS CLI transport; import performs no cloud action.

Linux memfd keeps JSON payloads out of argv, named disk files and stdin parsing.
This uses the already configured AWS CLI login, avoiding optional SDK login
provider dependencies. A caller still needs exact cloud-action approval.
Returned responses can contain secrets and must remain private process memory.
"""

import ctypes
import json
import os
import subprocess
import sys

PROFILE = "adityalaxmi1"
REGION = "ap-south-1"
OPERATIONS = {
    "identity": ("sts", "get-caller-identity"),
    "parameter_metadata": ("ssm", "describe-parameters"),
    "parameter_read": ("ssm", "get-parameter"),
    "parameter_create": ("ssm", "put-parameter"),
}


class PrivateAwsFailure(Exception):
    """Fixed public failure without payload, raw stderr or exception chaining."""


def _memory_descriptor() -> int:
    """Create a Linux anonymous RAM fd even when standalone Python omits os.memfd."""
    if sys.platform != "linux":
        raise ValueError
    if hasattr(os, "memfd_create"):
        return os.memfd_create("clip-private-aws-json", os.MFD_CLOEXEC)
    library = ctypes.CDLL(None, use_errno=True)
    create = library.memfd_create
    create.argtypes = (ctypes.c_char_p, ctypes.c_uint)
    create.restype = ctypes.c_int
    descriptor = create(b"clip-private-aws-json", 1)  # Linux MFD_CLOEXEC.
    if descriptor < 0:
        raise OSError(ctypes.get_errno(), "Anonymous memory input unavailable")
    return descriptor


def call(operation: str, payload: dict, *, allow_write: bool = False) -> dict:
    """Run one explicit approved operation with a0600anonymous RAM payload.

    Writes require an additional opt-in; no retry, rotation or disk fallback.
    Only the fixed operator profile/region is supported. Every path closes the
    parent descriptor. This is not proof of API success until the response is
    checked by the caller against its exact target and expected result.
    """
    descriptor = None
    try:
        if operation not in OPERATIONS:
            raise ValueError
        if operation == "parameter_create":
            required = {
                "Name": "/clip/test/conversations/database-url",
                "Type": "SecureString",
                "Tier": "Standard",
                "KeyId": "alias/aws/ssm",
                "Overwrite": False,
            }
            if not allow_write or any(
                payload.get(key) != value for key, value in required.items()
            ):
                raise ValueError
        encoded = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        if len(encoded) > 65536:
            raise ValueError
        descriptor = _memory_descriptor()
        os.fchmod(descriptor, 0o600)
        with os.fdopen(os.dup(descriptor), "wb") as stream:
            stream.write(encoded)
        os.lseek(descriptor, 0, os.SEEK_SET)
        service, action = OPERATIONS[operation]
        env = {
            name: os.environ[name]
            for name in (
                "PATH",
                "HOME",
                "LANG",
                "LC_ALL",
                "SSL_CERT_FILE",
                "REQUESTS_CA_BUNDLE",
                "HTTPS_PROXY",
                "HTTP_PROXY",
                "NO_PROXY",
            )
            if name in os.environ
        }
        result = subprocess.run(
            [
                "aws",
                "--profile",
                PROFILE,
                "--region",
                REGION,
                service,
                action,
                "--cli-input-json",
                "file:///proc/self/fd/" + str(descriptor),
                "--output",
                "json",
                "--no-cli-pager",
            ],
            pass_fds=(descriptor,),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode:
            raise ValueError
        response = json.loads(result.stdout)
        if not isinstance(response, dict):
            raise ValueError
        return response
    except Exception:
        raise PrivateAwsFailure(
            "Private AWS CLI operation failed; inspect safe phase metadata; no automatic retry"
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
