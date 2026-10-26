"""Real disposable SQL and offline secret port for the explicit local demo."""

import json

from fastapi.testclient import TestClient

from scripts.identity_local_demo import LocalParameters, REFS, demo_application
from apps.api.tests.domains.identity.test_runtime_configuration import (
    Parameters,
    key_document,
)


def test_local_demo_uses_only_two_remote_parameters_and_real_http(tmp_path):
    """Startup validates restricted SQL; auth stays real and no mailbox bypass exists."""
    parameters = Parameters(
        {
            REFS.authentication_keys: json.dumps(key_document()),
            REFS.email_delivery: json.dumps(
                {"version": 1, "primary": "resend", "resend_api_key": "synthetic-key"}
            ),
        }
    )
    with demo_application(tmp_path, ("user@example.test",), parameters) as app:
        with TestClient(
            app, base_url="http://localhost:5173", client=("127.0.0.1", 50000)
        ) as browser:
            assert browser.get("/health").status_code == 200
            assert browser.get("/me").status_code == 401
            assert browser.get("/catalogue").status_code == 401
            response = browser.post(
                "/auth/microsoft/login-attempts",
                headers={"Origin": "http://localhost:5173", "X-CLIP-Request": "1"},
            )
            assert response.status_code == 201
            assert "nonce" in response.json()
            assert "/__identity_preview__/mail" not in app.openapi()["paths"]
    assert parameters.calls == [REFS.authentication_keys, REFS.email_delivery]


def test_local_parameter_adapter_refuses_other_references():
    """Never allow the local launcher to read a master or unrelated secret."""
    import pytest
    from pydantic import SecretStr

    parameters = Parameters({})
    adapter = LocalParameters(parameters, SecretStr("local-only"))
    with pytest.raises(ValueError):
        adapter.get_parameter(Name="/unrelated/private-reference", WithDecryption=True)
    assert parameters.calls == []
