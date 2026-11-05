"""The approved pilot receives its private session through the child environment."""

from pathlib import Path

from scripts.evaluation.k6.real_run_coordinator import _prepare_child_env


def test_pilot_session_reaches_child_without_enabling_local_mode():
    """Prevent a valid pilot from failing before its first authenticated request."""
    cookie = "__Host-clip_session=synthetic-test-only"
    env = _prepare_child_env(
        {"workload_kind": "exp05-pilot", "run_id": "pilot-test", "configuration": "A"},
        Path("/tmp/pilot-profile.json"),
        {"api_origin": "https://clip-iisc.site"},
        cookie,
        None,
    )
    assert env["CLIP_REAL_RUN_SESSION_COOKIE"] == cookie
    assert env["CLIP_EXP05_REAL_RUN_MODE"] == "approved-runner"
    assert env["CLIP_EXP05_LOCAL_LOAD"] == "false"
    assert env["CLIP_EXP05_REAL_TARGET"] == "https://clip-iisc.site/api"
    assert not any("CSRF" in key for key in env)
