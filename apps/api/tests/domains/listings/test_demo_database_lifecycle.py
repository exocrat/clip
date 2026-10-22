"""Exercise LI-02's real shell control flow with a controlled psql process.

These checks need no database or AWS access. They verify that metadata reaches
the guards, malformed/failed queries cannot cause writes, and diagnostics stay
private. They do not substitute for the live PostgreSQL setup/migration check.
"""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[5]
    / "infra/terraform/domains/listings/test/scripts/database-lifecycle.sh"
)


@pytest.fixture
def database_client(tmp_path):
    """Record query/write boundaries and supply controlled metadata responses."""
    client = tmp_path / "psql"
    client.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys\n"
        "sql = next((a[10:] for a in sys.argv if a.startswith('--command=')), None)\n"
        "if sql is None:\n"
        "    sql = sys.stdin.read()\n"
        "query = sql.startswith('SELECT (EXISTS') or "
        "sql.startswith('SELECT pg_get_userbyid') or sql.startswith('SELECT count(*)')\n"
        "with pathlib.Path(os.environ['CHECK_RECORD']).open('a') as record:\n"
        "    record.write(json.dumps({'query': query, 'args': sys.argv[1:], "
        "'uses_app_password': os.environ.get('PGPASSWORD') == 'a' * 64, "
        "'connect_timeout': os.environ['PGCONNECT_TIMEOUT'], "
        "'options': os.environ['PGOPTIONS']}) + '\\n')\n"
        "print('controlled-private-diagnostic', file=sys.stderr)\n"
        "if query:\n"
        "    if os.environ.get('CHECK_QUERY_FAIL') == '1':\n"
        "        print('controlled-private-diagnostic')\n"
        "        sys.exit(2)\n"
        "    key = 'CHECK_STATE' if sql.startswith('SELECT (EXISTS') else "
        "'CHECK_OWNER' if sql.startswith('SELECT pg_get_userbyid') else 'CHECK_CLIENTS'\n"
        "    print(os.environ[key])\n"
        "else:\n"
        "    print('controlled-private-write-output')\n"
    )
    client.chmod(0o755)
    record = tmp_path / "record.jsonl"

    def run(
        action,
        state="0 0",
        owner="clip_test_listings_app",
        clients="0",
        fail=False,
        omit_password=False,
        invalid_url=False,
    ):
        """Run the unmodified shell entry point against synthetic client replies."""
        environment = {
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "PGHOST": "db.example.test",
            "PGPORT": "5432",
            "PGDATABASE": "clip_test",
            "PGUSER": "clip_test_admin",
            "PGPASSWORD": "controlled-local-test-input",
            "PGCONNECT_TIMEOUT": "0",
            "PGOPTIONS": "-c statement_timeout=0 -c lock_timeout=0",
            "CLIP_DATABASE_URL": (
                f"postgresql://clip_test_listings_app:{'a' * 64}"
                "@db.example.test:5432/clip_test_listings?sslmode=require"
            ),
            "CHECK_RECORD": str(record),
            "CHECK_STATE": state,
            "CHECK_OWNER": owner,
            "CHECK_CLIENTS": clients,
            "CHECK_QUERY_FAIL": "1" if fail else "0",
        }
        if action == "seed":
            environment["PGDATABASE"] = "clip_test_listings"
            environment["PGUSER"] = "clip_test_listings_app"
            # Match the deployed ECS seed definition: no administrator secret.
            environment.pop("PGPASSWORD")
        elif omit_password:
            environment.pop("PGPASSWORD")
        if invalid_url:
            environment["CLIP_DATABASE_URL"] = "invalid-controlled-test-input"
        result = subprocess.run(
            ["/bin/sh", str(SCRIPT), action],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        calls = (
            [json.loads(line) for line in record.read_text().splitlines()]
            if record.exists()
            else []
        )
        output = result.stdout + result.stderr
        assert "controlled-private" not in output
        assert "controlled-local-test-input" not in output
        assert "a" * 64 not in output
        for call in calls:
            assert call["connect_timeout"] == "10"
            assert call["options"] == "-c statement_timeout=30000 -c lock_timeout=30000"
            if call["query"]:
                assert "--tuples-only" in call["args"]
                assert "--no-align" in call["args"]
        return result, calls

    return run


@pytest.mark.parametrize(
    "action,state,owner,clients,success,writes",
    [
        ("bootstrap", "0 0", "", "0", True, 2),
        ("bootstrap", "0 1", "", "0", False, 0),
        ("bootstrap", "1 0", "", "0", False, 0),
        ("bootstrap", "1 1", "", "0", False, 0),
        ("bootstrap", "", "", "0", False, 0),
        ("bootstrap", "unexpected", "", "0", False, 0),
        ("cleanup", "0 0", "", "0", True, 0),
        ("cleanup", "0 1", "", "0", True, 1),
        ("cleanup", "1 0", "", "0", False, 0),
        ("cleanup", "1 1", "clip_test_listings_app", "0", True, 2),
        ("cleanup", "1 1", "another_owner", "0", False, 0),
        ("cleanup", "1 1", "", "0", False, 0),
        ("cleanup", "", "", "0", False, 0),
        ("cleanup", "unexpected", "", "0", False, 0),
        ("check-idle", "", "", "0", True, 0),
        ("check-idle", "", "", "1", False, 0),
        ("check-idle", "", "", "", False, 0),
        ("check-idle", "", "", "unexpected", False, 0),
    ],
)
def test_metadata_controls_lifecycle_safely(
    database_client, action, state, owner, clients, success, writes
):
    """Known states select the intended path; unknown states never mutate."""
    result, calls = database_client(action, state, owner, clients)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    assert sum(not call["query"] for call in calls) == writes


@pytest.mark.parametrize("action", ["bootstrap", "cleanup", "check-idle"])
def test_failed_metadata_query_never_mutates(database_client, action):
    """A database client error must stop before writes and hide its diagnostics."""
    result, calls = database_client(action, fail=True)
    assert result.returncode != 0
    assert all(call["query"] for call in calls)


def test_seed_uses_only_its_application_url(database_client):
    """The actual ECS seed secret set must work without an admin password."""
    result, calls = database_client("seed")
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(calls) == 1
    assert calls[0]["uses_app_password"] is True
    assert calls[0]["query"] is False


@pytest.mark.parametrize("action", ["bootstrap", "cleanup", "check-idle"])
def test_admin_actions_require_their_password(database_client, action):
    """Relaxing the seed contract must not relax any administrator action."""
    result, calls = database_client(action, omit_password=True)
    assert result.returncode != 0
    assert calls == []


@pytest.mark.parametrize("action", ["bootstrap", "seed"])
def test_invalid_url_never_reaches_database(database_client, action):
    """Credential extraction failures stop before the PostgreSQL client runs."""
    result, calls = database_client(action, invalid_url=True)
    assert result.returncode != 0
    assert calls == []
