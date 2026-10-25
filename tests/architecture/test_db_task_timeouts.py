"""Exercise the PD-16 shell tasks' deadline and private-diagnostic boundaries.

Use controlled psql stand-ins and a real GNU timeout with shortened durations.
No database, Docker, credentials, provider, or cloud action is required.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra/terraform/shared/test/scripts"


@pytest.fixture
def tools(tmp_path):
    """Build local stand-ins; keep the production deadline contract checked."""
    real_timeout = shutil.which("timeout")
    if not real_timeout:
        pytest.skip("GNU timeout is required for this Linux-container regression")
    # New executable stand-ins can take more than 0.2s to start on macOS.
    # Allow startup while still killing the 10s hanging client well before the
    # outer 6s watchdog. The production 60s/5s arguments remain asserted below.
    (tmp_path / "timeout").write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        "assert sys.argv[1:4] == ['--signal=TERM', '--kill-after=5s', '60s']\n"
        f"os.execv({real_timeout!r}, ['timeout', '--signal=TERM', "
        "'--kill-after=0.1s', '2s', *sys.argv[4:]])\n"
    )
    (tmp_path / "psql").write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, signal, sys, time\n"
        "pathlib.Path(os.environ['CHECK_RECORD']).write_text(json.dumps({"
        "key: os.environ.get(key) for key in ['PGCONNECT_TIMEOUT', 'PGOPTIONS']}))\n"
        "mode = os.environ['CHECK_MODE']\n"
        "if mode == 'hang':\n"
        "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "    time.sleep(10)\n"
        "if mode == 'fail':\n"
        "    print('controlled-private-diagnostic')\n"
        "    print('controlled-private-diagnostic', file=sys.stderr)\n"
        "    sys.exit(2)\n"
        "print('1')\n"
    )
    for name in ("timeout", "psql"):
        (tmp_path / name).chmod(0o755)
    return tmp_path


@pytest.mark.parametrize("script", ["setup-db-role.sh", "probe-db.sh"])
@pytest.mark.parametrize("mode", ["success", "fail", "hang"])
def test_database_tasks_bound_psql_and_hide_private_output(tools, script, mode):
    """A stuck child must stop; ordinary failures must not disclose diagnostics."""
    record = tools / "record.json"
    result = subprocess.run(
        ["/bin/sh", str(SCRIPTS / script)],
        env={
            "PATH": f"{tools}:{os.environ['PATH']}",
            "PGPASSWORD": "controlled-local-test-input",
            "PROBE_PASSWORD": "controlled-local-test-input",
            "PGHOST": "127.0.0.1",
            "PGPORT": "5432",
            "PGDATABASE": "clip_test",
            "PGUSER": "clip_test_probe",
            "PGCONNECT_TIMEOUT": "0",
            "PGOPTIONS": "-c statement_timeout=0 -c lock_timeout=0",
            "CHECK_RECORD": str(record),
            "CHECK_MODE": mode,
        },
        capture_output=True,
        text=True,
        timeout=6,
    )
    assert (result.returncode == 0) == (mode == "success")
    assert "controlled-private-diagnostic" not in result.stdout + result.stderr
    assert "controlled-local-test-input" not in result.stdout + result.stderr
    assert json.loads(record.read_text()) == {
        "PGCONNECT_TIMEOUT": "10",
        "PGOPTIONS": "-c statement_timeout=30000 -c lock_timeout=30000",
    }
    if mode == "hang":
        assert "failed or timed out" in result.stdout


@pytest.mark.parametrize("script", ["setup-db-role.sh", "probe-db.sh"])
def test_database_tasks_fail_when_timeout_tool_is_missing(tmp_path, script):
    """A client image without the deadline tool must fail before running SQL."""
    result = subprocess.run(
        ["/bin/sh", str(SCRIPTS / script)],
        env={"PATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=4,
    )
    assert result.returncode != 0
    assert "required timeout tool unavailable" in result.stdout
