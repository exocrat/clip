"""Canonical process-health contract; declarations only, no handler or service."""

from typing import Literal, TypedDict

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Only process liveness is promised; no dependency readiness is implied."""

    status: Literal["ok"]


class HealthRoute(TypedDict):
    """Explicit HTTP metadata shared by schema generation and the real handler."""

    path: str
    response_model: type[HealthResponse]
    operation_id: str
    summary: str
    description: str


HEALTH_ROUTE: HealthRoute = {
    "path": "/health",
    "response_model": HealthResponse,
    "operation_id": "health_health_get",
    "summary": "Health",
    "description": (
        "Report that this API process responds, without inspecting dependencies.\n\n"
        "This is a liveness signal only: it does not claim database, provider, or\n"
        "deployment readiness. It exposes no configuration or private state."
    ),
}
