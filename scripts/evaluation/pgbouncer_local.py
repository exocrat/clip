"""Real local transaction pool for the capacity harness; never accesses AWS.

Uses the exact deployment policy and binary over owned Unix sockets. This
isolates connection reuse/CPU effects; a separate native test covers TLS.
"""

from contextlib import contextmanager
from decimal import Decimal
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

import psycopg
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "clip-pgbouncer:local-20261104"


def command(args):
    """Withhold secret-bearing command output on failure."""
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("local_pgbouncer_command_failed")
    return result.stdout.strip()


@contextmanager
def local_pool(directory, database_socket, config, report):
    """Start and remove exactly one owned pool; rewrite only local worker DSNs."""
    spec = importlib.util.spec_from_file_location(
        "clip_pool_entrypoint", ROOT / "infra/pgbouncer/entrypoint.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = directory / "pool"
    root.mkdir(mode=0o700)
    credentials = {}
    for name in ("identity", "marketplace", "conversations"):
        values = conninfo_to_dict(config[f"{name}_dsn"])
        credentials[values["user"]] = values["password"]
        values.update(host="/run/clip-pool", port="6432")
        # Keep the URI format required by Identity's source validation.
        from urllib.parse import urlencode

        config[f"{name}_dsn"] = "postgresql:///?" + urlencode(values)
    auth, ini = module.render(
        "/run/clip-db",
        "clip_test_identity",
        credentials,
        root=Path("/run/clip-pool"),
        local_socket="/run/clip-pool",
    )
    for name, content in (("users.txt", auth), ("pgbouncer.ini", ini)):
        (root / name).write_text(content)
        (root / name).chmod(0o600)
    docker = ["docker", "--context", "default"]
    identifier = None
    try:
        identifier = command(
            docker
            + [
                "run",
                "--detach",
                "--network",
                "none",
                "--cpus",
                "1",
                "--memory",
                "256m",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--mount",
                f"type=bind,src={database_socket},dst=/run/clip-db",
                "--mount",
                f"type=bind,src={root},dst=/run/clip-pool",
                "--entrypoint",
                "/usr/sbin/pgbouncer",
                IMAGE,
                "/run/clip-pool/pgbouncer.ini",
            ]
        )
        deadline = time.monotonic() + 10
        while not (root / ".s.PGSQL.6432").exists():
            if time.monotonic() > deadline:
                raise RuntimeError("local_pgbouncer_start_failed")
            time.sleep(0.05)
        report["database_pool"] = {
            "image_id": command(
                docker + ["image", "inspect", IMAGE, "--format", "{{.Id}}"]
            ),
            "backend_limits": {role: limit for role, limit in module.ROLES.values()},
            "mode": "transaction",
            "cpu": 1,
            "memory_mib": 256,
            "tls_tested_here": False,
        }
        try:
            yield root, identifier
        finally:
            report["database_pool"]["final_snapshot"] = snapshot(
                root, config["identity_dsn"]
            )
            report["database_pool"]["log"] = command(docker + ["logs", identifier])

    finally:
        if identifier:
            command(docker + ["rm", "--force", identifier])


def snapshot(root, dsn):
    """Content-free pool accounting, using only its read-only administration user."""
    params = conninfo_to_dict(dsn)
    params.update(host=str(root), dbname="pgbouncer", port="6432")
    with psycopg.connect(
        **params, connect_timeout=2, autocommit=True, row_factory=psycopg.rows.dict_row
    ) as connection:
        return json.loads(
            json.dumps(
                {
                    "stats": connection.execute("SHOW STATS").fetchall(),
                    "pools": connection.execute("SHOW POOLS").fetchall(),
                },
                default=lambda value: (
                    int(value)
                    if isinstance(value, Decimal) and value == int(value)
                    else float(value)
                ),
            )
        )
