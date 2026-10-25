"""Reviewed CSRF response double only for explicit synthetic browser harnesses.

This file is excluded from API images and normal startup. It does not issue real
sessions or prove CSRF protection; the real Identity middleware owns that check.
"""

from fastapi import FastAPI, Response
from app.contracts.domain_types import CsrfToken


def install_demo_csrf(app: FastAPI, prefix: str = "") -> None:
    """Support strict frontend preflight inside the caller's isolated test app."""
    if prefix not in {"", "/api"}:
        raise ValueError("Invalid isolated fixture prefix")

    @app.get(prefix + "/auth/csrf", response_model=CsrfToken, include_in_schema=False)
    def csrf(response: Response) -> CsrfToken:
        """Return a conspicuously synthetic token under the harness transport gate."""
        response.headers["Cache-Control"] = "no-store"
        return CsrfToken(csrf_token="synthetic-demo-csrf-" + "0" * 45)
