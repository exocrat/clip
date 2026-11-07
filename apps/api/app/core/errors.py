"""Safe public HTTP errors; exception internals and submitted values stay private."""

from dataclasses import dataclass
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse


@dataclass(frozen=True)
class ErrorSpec:
    """Code-owned public error definition; never construct from untrusted text."""

    status: int
    code: str
    message: str


ERRORS = {
    400: ErrorSpec(400, "bad_request", "Malformed request"),
    401: ErrorSpec(401, "unauthenticated", "Authentication required"),
    403: ErrorSpec(403, "forbidden", "Action not permitted"),
    404: ErrorSpec(404, "not_found", "Resource not found"),
    405: ErrorSpec(405, "method_not_allowed", "Method not allowed"),
    413: ErrorSpec(413, "payload_too_large", "Request body too large"),
    409: ErrorSpec(409, "conflict", "Resource state conflict"),
    422: ErrorSpec(422, "validation_error", "Request validation failed"),
    429: ErrorSpec(429, "rate_limited", "Request rate limit reached"),
    500: ErrorSpec(500, "internal_error", "Unexpected server error"),
    503: ErrorSpec(503, "dependency_unavailable", "Required dependency unavailable"),
}


@dataclass(frozen=True)
class FieldError:
    """Reviewed field/code pair, excluding rejected inputs and exception messages."""

    field: str
    code: str

    def __post_init__(self) -> None:
        """Keep code-owned metadata bounded and structurally simple."""
        if not all(
            isinstance(v, str) and re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_.]{0,127}", v)
            for v in (self.field, self.code)
        ):
            raise ValueError("Invalid public field-error metadata")


class PublicError(Exception):
    """Carry only an explicitly reviewed error definition and safe field codes."""

    def __init__(self, spec: ErrorSpec, details: tuple[FieldError, ...] = ()) -> None:
        """Store public metadata; callers must not pass raw provider/user messages."""
        super().__init__(spec.code)
        self.spec = spec
        self.details = details


def error_response(
    request: Request,
    spec: ErrorSpec,
    details: tuple[FieldError, ...] = (),
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the standard envelope using server-assigned correlation metadata."""
    error = {"code": spec.code, "message": spec.message}
    if details:
        error["details"] = [{"field": d.field, "code": d.code} for d in details]
    body = {"error": error}
    request_id = request.scope.get("clip.request_id")
    if request_id:
        body["request_id"] = request_id
    return JSONResponse(body, status_code=spec.status, headers=headers)


async def public_error_handler(request: Request, exc: PublicError) -> JSONResponse:
    """Map explicit application failures without serializing an exception."""
    return error_response(request, exc.spec, exc.details)


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Replace arbitrary HTTPException detail with a safe common message."""
    spec = ERRORS.get(
        exc.status_code, ErrorSpec(exc.status_code, "request_failed", "Request failed")
    )
    headers = {
        k: v
        for k, v in (exc.headers or {}).items()
        if k.lower() in {"www-authenticate", "retry-after", "allow"}
    }
    return error_response(request, spec, headers=headers)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Report only input locations: nested map keys may contain private values.

    Detailed domain field errors use reviewed FieldError entries. Generic schema
    errors name body/query/path/header/cookie only, never arbitrary input keys.
    """
    allowed = {"body", "query", "path", "header", "cookie"}
    locations = {
        str(e["loc"][0])
        for e in exc.errors()
        if e.get("loc") and e["loc"][0] in allowed
    }
    details = tuple(FieldError(loc, "invalid_value") for loc in sorted(locations))
    return error_response(request, ERRORS[422], details)


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic failure without exposing or logging raw exception data."""
    return error_response(request, ERRORS[500])


def install_error_handlers(app: FastAPI) -> None:
    """Install one envelope for framework, validation, application and server errors."""
    app.add_exception_handler(PublicError, public_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
