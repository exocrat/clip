"""Loopback-only test harness safety and actual API/SQL registration check."""

import os
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from scripts.identity_ui_preview import preview_app, SYNTHETIC_EMAIL


def test_preview_harness_refuses_production_before_database_or_listener():
    result = subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "python",
            "scripts/identity_ui_preview.py",
            "--synthetic-preview",
        ],
        cwd=Path(__file__).resolve().parents[5],
        env={key: os.environ[key] for key in ("HOME", "PATH")}
        | {"CLIP_ENVIRONMENT": "production"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "requires explicit test environment" in result.stderr
    assert result.stdout == ""


def test_preview_mail_route_is_not_installed_in_normal_startup():
    # Isolate startup configuration so importing app.main cannot cache settings
    # before another test explicitly selects its own environment.
    result = subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "python",
            "-c",
            "from app.main import app; assert {r.path for r in app.routes} == {'/health'}",
        ],
        cwd=Path(__file__).resolve().parents[5],
        env={key: os.environ[key] for key in ("HOME", "PATH")}
        | {"CLIP_ENVIRONMENT": "test", "PYTHONPATH": "apps/api"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0 and result.stdout == ""


def test_preview_uses_real_registration_and_refuses_non_loopback(disposable_database):
    from uuid import uuid4

    app = preview_app(disposable_database)
    origin = "http://localhost:5173"
    with TestClient(app, base_url=origin, client=("127.0.0.1", 50000)) as browser:
        headers = {"Origin": origin, "X-CLIP-Request": "1"}
        requested = browser.post(
            "/auth/temporary/registration-challenges",
            headers=headers,
            json={"email": SYNTHETIC_EMAIL, "operation_id": str(uuid4())},
        )
        assert requested.status_code == 202
        mail = browser.get("/__identity_preview__/mail")
        assert mail.headers["cache-control"] == "no-store"
        code = mail.json()["code"]
        assert isinstance(code, str) and len(code) == 6
        result = browser.post(
            "/auth/temporary/accounts",
            headers=headers,
            json={
                "challenge_id": requested.json()["challenge_id"],
                "code": code,
                "password": "synthetic preview passphrase",
            },
        )
        assert result.status_code == 201
        assert browser.get("/me").status_code == 200
        assert code not in result.text
    with TestClient(app, base_url=origin, client=("192.0.2.27", 50000)) as browser:
        assert browser.get("/__identity_preview__/mail").status_code == 403
