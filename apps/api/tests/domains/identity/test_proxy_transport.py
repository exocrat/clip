"""Real Identity origin/cookie gates behind the exact proposed Uvicorn proxy trust.

Only disposable SQL and controlled upstream signer/mail are used. These tests
prove ASGI transport handling, not cloud routing, Caddy issuance or live delivery.
"""

from fastapi.testclient import TestClient
import pytest
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from apps.api.tests.domains.identity.session_fixtures import HEADERS

PROXY = "10.64.0.10"


@pytest.mark.parametrize(
    "peer,proto,origin,marker,status",
    [
        (PROXY, "https", "https://clip-iisc.site", "1", 201),
        ("10.64.0.11", "https", "https://clip-iisc.site", "1", 403),
        (PROXY, "http", "https://clip-iisc.site", "1", 403),
        (PROXY, "https", "https://foreign.invalid", "1", 403),
        (PROXY, "https", "null", "1", 403),
        (PROXY, "https", "https://clip-iisc.site", "0", 403),
    ],
)
def test_exact_proxy_trust_preserves_identity_origin_and_cookie_gates(
    identity_runtime, peer, proto, origin, marker, status
):
    """Forwarded HTTPS is accepted only from the fixed peer with valid app headers."""
    app = ProxyHeadersMiddleware(identity_runtime.app, trusted_hosts=PROXY)
    with TestClient(
        app, base_url="http://clip-iisc.site", client=(peer, 40000)
    ) as browser:
        result = browser.post(
            "/auth/microsoft/login-attempts",
            headers=HEADERS
            | {
                "Origin": origin,
                "X-CLIP-Request": marker,
                "X-Forwarded-Proto": proto,
                "X-Forwarded-For": "192.0.2.27",
            },
        )
        assert result.status_code == status
        if status == 201:
            assert "secure" in result.headers["set-cookie"].lower()
            assert "httponly" in result.headers["set-cookie"].lower()
        else:
            assert "set-cookie" not in result.headers
        with identity_runtime.connect() as connection:
            assert connection.execute(
                "SELECT count(*) FROM identity.microsoft_login_attempts"
            ).fetchone() == (1 if status == 201 else 0,)
