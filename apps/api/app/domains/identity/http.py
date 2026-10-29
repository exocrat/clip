"""Explicit Identity HTTP composition with real sessions, origin/CSRF and cookies.

Construction requires trusted real dependencies; unconfigured app.main keeps Identity unavailable
while preserving accepted Listings routes. This module never discovers secrets, DB targets or a fake provider.
Proxy/TLS/source wiring and real browser/provider verification remain deployment
checks; forwarded identity/IP headers are deliberately not trusted here.
"""

from dataclasses import dataclass, field
from datetime import datetime
import hmac
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Callable
from uuid import UUID
from urllib.parse import urlsplit

from fastapi import BackgroundTasks, FastAPI, Request, Response
from starlette.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import ERRORS, PublicError, error_response, install_error_handlers
from app.core.logging import RequestLoggingMiddleware
from app.core.runtime_bindings import runtime_claims, runtime_scope
from app.domains.identity.capabilities import Capability
from app.domains.identity.microsoft import MicrosoftTokenValidator
from app.domains.identity.sessions import (
    IdentitySessions,
    SessionGrant,
    SessionIdentity,
    bound_value,
)
from app.domains.identity.temporary_delivery import EmailSender
from app.contracts.domain_types import (
    ActivateTemporaryRequest,
    ChallengeAccepted,
    CsrfToken,
    MicrosoftLoginAttempt,
    MicrosoftSessionRequest,
    PasswordResetChallengeRequest,
    RegistrationChallengeRequest,
    ResetTemporaryPasswordRequest,
    SessionView,
    TemporarySessionRequest,
    ContactField,
    ContactValueRequest,
    OwnContacts,
    ProfilePatch,
    ProfileView,
)

PUBLIC_AUTH = frozenset(
    {
        "/auth/microsoft/login-attempts",
        "/auth/microsoft/sessions",
        "/auth/temporary/registration-challenges",
        "/auth/temporary/accounts",
        "/auth/temporary/sessions",
        "/auth/temporary/password-reset-challenges",
        "/auth/temporary/password-resets",
    }
)


@dataclass(frozen=True)
class BrowserPolicy:
    """Exact allowed origins and an explicit loopback-only insecure development mode."""

    origins: tuple[str, ...]
    development: bool = False

    def __post_init__(self) -> None:
        """Reject wildcard/path/credential origins and non-loopback HTTP exceptions."""
        if not self.origins:
            raise ValueError("Explicit browser origins required")
        for origin in self.origins:
            parsed = urlsplit(origin)
            if (
                parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or not parsed.hostname
                or parsed.scheme not in {"http", "https"}
                or "*" in origin
            ):
                raise ValueError("Invalid browser origin")
            if self.development:
                try:
                    loopback = (
                        parsed.hostname == "localhost"
                        or ip_address(parsed.hostname).is_loopback
                    )
                except ValueError:
                    loopback = False
                if not loopback:
                    raise ValueError("Development requires loopback origins")
            elif parsed.scheme != "https":
                raise ValueError("Secure browser origin required")

    @property
    def session_cookie(self) -> str:
        """Use browser-enforced host cookie rules outside explicit loopback mode."""
        return "clip_session_dev" if self.development else "__Host-clip_session"

    @property
    def attempt_cookie(self) -> str:
        """Keep the Microsoft binding separate from the authenticated session."""
        return "clip_ms_attempt_dev" if self.development else "__Host-clip_ms_attempt"


def session_view(identity: SessionIdentity) -> SessionView:
    """Project only reviewed public fields; no cookie/CSRF/private account state."""
    return SessionView(
        user_id=identity.caller.user_id,
        account_class=identity.caller.account_class,
        valid_until=identity.caller.valid_until,
        display_name=identity.display_name,
        handle_ready=identity.handle_ready,
    )


class IdentityBrowserMiddleware:
    """Create trusted request context and enforce unsafe-request browser boundaries."""

    def __init__(self, app: ASGIApp, sessions: IdentitySessions, policy: BrowserPolicy):
        """Bind explicit dependencies; all blocking storage runs outside event loop."""
        self.app, self.sessions, self.policy = app, sessions, policy

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind this explicit runtime per request, isolated from parallel app scopes."""
        with (
            runtime_scope(
                {
                    "identity.check_account_eligibility": self.sessions.capabilities.check_account_eligibility,
                    "identity.get_shareable_contact_options": self.sessions.contacts.get_shareable_contact_options,
                    "identity.get_selected_own_contacts": self.sessions.contacts.get_selected_own_contacts,
                }
            ),
            runtime_claims({}),
        ):
            await self._handle(scope, receive, send)

    async def _handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Never consume/log bodies or trust submitted caller/forwarding headers."""
        if scope["type"] != "http" or scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return
        scope.pop("clip.caller", None)
        scope.pop("clip.session", None)
        request = Request(scope)

        async def no_store(message: Message) -> None:
            """Prevent intermediaries caching authentication/private responses."""
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() != b"cache-control"
                ] + [(b"cache-control", b"no-store")]
            await send(message)

        unsafe = request.method not in {"GET", "HEAD", "OPTIONS"}
        raw_path = request.url.path
        path = raw_path[4:] if raw_path.startswith("/api/") else raw_path
        development_peer = True
        if self.policy.development:
            try:
                host = request.url.hostname or ""
                development_peer = (
                    (host == "localhost" or ip_address(host).is_loopback)
                    and request.client is not None
                    and ip_address(request.client.host).is_loopback
                )
            except ValueError:
                development_peer = False
        denied = (
            not development_peer
            or (not self.policy.development and request.url.scheme != "https")
            or (
                request.headers.get("origin") is not None
                and request.headers["origin"] not in self.policy.origins
            )
            or (
                unsafe
                and (
                    request.headers.get("origin") not in self.policy.origins
                    or request.headers.get("x-clip-request") != "1"
                )
            )
        )
        if denied:
            # Reject hostile transport/origin before any session read/idle update.
            await error_response(request, ERRORS[403])(scope, receive, no_store)
            return
        token = request.cookies.get(self.policy.session_cookie)
        failure = None
        if token:
            try:
                identity = await run_in_threadpool(self.sessions.authenticate, token)
                scope["clip.caller"] = identity.caller
                scope["clip.session"] = identity
            except PublicError as error:
                failure = error.spec
        if unsafe and path not in PUBLIC_AUTH:
            if not token:
                failure = ERRORS[401]
            else:
                try:
                    if not hmac.compare_digest(
                        bound_value(token, "csrf"),
                        request.headers.get("x-csrf-token", ""),
                    ):
                        failure = ERRORS[403]
                    elif (
                        path == "/auth/session"
                        and failure is not None
                        and failure.status == 401
                    ):
                        # Retained token+CSRF can retry logout; storage still
                        # checks account/expiry before idempotent revocation.
                        failure = None
                except PublicError, TypeError:
                    failure = ERRORS[403]
        if path in PUBLIC_AUTH and failure is not None and failure.status == 401:
            failure = None
        if failure is not None and (unsafe or failure.status != 401):
            await error_response(request, failure)(scope, receive, no_store)
            return
        await self.app(scope, receive, no_store)


def create_identity_app(
    sessions: IdentitySessions,
    policy: BrowserPolicy,
    sender: EmailSender,
    validator: MicrosoftTokenValidator,
    clock: Callable[[], datetime],
) -> FastAPI:
    """Build actual auth handlers for an explicitly configured trusted runtime.

    No ambient credentials/provider connection or automatic production activation.
    Runtime wiring must supply approved keys/role/source/TLS before deployment.
    """
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    install_error_handlers(app)
    install_identity_http(
        app, IdentityHttpDependencies(sessions, policy, sender, validator, clock)
    )
    app.add_middleware(RequestLoggingMiddleware)
    return app


@dataclass(frozen=True)
class IdentityHttpDependencies:
    """Explicit trusted bindings, not an environment switch or auth credential.

    Sessions own real persistence/keys; the clock, sender and validator are supplied
    by reviewed composition. This object performs no discovery, I/O or fallback.
    Controlled signer/mail ports are permitted only in explicit local/test apps.
    """

    sessions: IdentitySessions = field(repr=False)
    policy: BrowserPolicy
    sender: EmailSender = field(repr=False)
    validator: MicrosoftTokenValidator = field(repr=False)
    clock: Callable[[], datetime] = field(repr=False)

    def __post_init__(self) -> None:
        """Reject incomplete/wrong runtime bindings before installing any route."""
        if (
            not isinstance(self.sessions, IdentitySessions)
            or not isinstance(self.policy, BrowserPolicy)
            or not isinstance(self.validator, MicrosoftTokenValidator)
            or not callable(getattr(self.sender, "send", None))
            or not callable(self.clock)
        ):
            raise ValueError("Complete trusted Identity dependencies required")


def install_identity_http(
    app: FastAPI,
    runtime: IdentityHttpDependencies,
    *,
    path_prefix: str = "",
) -> None:
    """Install real auth routes and request-scoped caller policy into an existing app.

    The composition root owns error/logging middleware, health and lifespan; do not
    create a nested/mounted app that would split state or trusted caller context.
    Call once before startup. No provider/DB/secret I/O occurs during installation.
    """
    if not isinstance(runtime, IdentityHttpDependencies):
        raise ValueError("Complete trusted Identity dependencies required")
    if getattr(app.state, "identity_http_installed", False):
        raise ValueError("Identity HTTP already installed")
    if path_prefix not in ("", "/api"):
        raise ValueError("Unsupported Identity API prefix")

    def route(path: str) -> str:
        """Match the Vite and same-origin hosted UI /api transport paths."""
        return path_prefix + path

    sessions, policy = runtime.sessions, runtime.policy
    sender, validator, clock = runtime.sender, runtime.validator, runtime.clock
    app.add_middleware(IdentityBrowserMiddleware, sessions=sessions, policy=policy)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(policy.origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PATCH", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "X-CLIP-Request", "X-CSRF-Token"],
    )

    def source(request: Request) -> IPv4Address | IPv6Address:
        """Use only transport peer IP; deployment must review any proxy adaptation."""
        try:
            if request.client is None:
                raise ValueError
            return ip_address(request.client.host)
        except ValueError:
            raise PublicError(ERRORS[400]) from None

    def json_body(request: Request) -> None:
        """Reject form/simple requests even when a synthetic Origin is supplied."""
        if (
            request.headers.get("content-type", "").split(";")[0].lower()
            != "application/json"
        ):
            raise PublicError(ERRORS[422])

    def current(request: Request) -> SessionIdentity:
        """Consume only middleware-established live session/account facts."""
        identity = request.scope.get("clip.session")
        if not isinstance(identity, SessionIdentity):
            raise PublicError(ERRORS[401])
        return identity

    def set_cookie(
        response: Response, name: str, value: str, expires: datetime
    ) -> None:
        """Host-only secure/HttpOnly/Lax; explicit development mode is loopback-only."""
        response.set_cookie(
            name,
            value,
            expires=expires,
            path="/",
            secure=not policy.development,
            httponly=True,
            samesite="lax",
        )

    def grant(response: Response, result: SessionGrant) -> SessionView:
        """Cookie transport carries the sole bearer; JSON carries reviewed summary."""
        set_cookie(
            response,
            policy.session_cookie,
            result.token.get_secret_value(),
            result.expires_at,
        )
        return session_view(result.identity)

    @app.post(
        route("/auth/microsoft/login-attempts"),
        operation_id="identity_start_microsoft_login_attempt",
        response_model=MicrosoftLoginAttempt,
        status_code=201,
    )
    def attempt(request: Request, response: Response) -> MicrosoftLoginAttempt:
        """Begin bounded server nonce flow, setting only its private binding cookie."""
        result = sessions.start_microsoft(source(request))
        set_cookie(
            response,
            policy.attempt_cookie,
            result.token.get_secret_value(),
            result.expires_at,
        )
        return MicrosoftLoginAttempt(nonce=result.nonce, expires_at=result.expires_at)

    @app.post(
        route("/auth/microsoft/sessions"),
        operation_id="identity_create_microsoft_session",
        response_model=SessionView,
    )
    def microsoft(
        payload: MicrosoftSessionRequest, request: Request, response: Response
    ) -> SessionView:
        """Consume a browser-bound signed assertion once and establish its session."""
        json_body(request)
        result = sessions.microsoft_exchange(
            payload.id_token,
            request.cookies.get(policy.attempt_cookie),
            source(request),
            validator,
        )
        response.delete_cookie(
            policy.attempt_cookie,
            path="/",
            secure=not policy.development,
            httponly=True,
            samesite="lax",
        )
        return grant(response, result)

    @app.post(
        route("/auth/temporary/registration-challenges"),
        operation_id="identity_start_temporary_registration",
        response_model=ChallengeAccepted,
        status_code=202,
    )
    def registration(
        payload: RegistrationChallengeRequest,
        request: Request,
        background: BackgroundTasks,
    ) -> ChallengeAccepted:
        """Acknowledge before one-shot provider dispatch; never expose send outcome."""
        return challenge(
            payload.email,
            payload.operation_id,
            "initial_verification",
            request,
            background,
        )

    @app.post(
        route("/auth/temporary/password-reset-challenges"),
        operation_id="identity_start_password_reset",
        response_model=ChallengeAccepted,
        status_code=202,
    )
    def reset_challenge(
        payload: PasswordResetChallengeRequest,
        request: Request,
        background: BackgroundTasks,
    ) -> ChallengeAccepted:
        """Same acknowledgement and limits for known/ineligible/unknown addresses."""
        return challenge(
            payload.email, payload.operation_id, "password_reset", request, background
        )

    def challenge(
        email: str,
        operation: UUID,
        purpose: str,
        request: Request,
        background: BackgroundTasks,
    ) -> ChallengeAccepted:
        """Keep transient delivery private and run blocking dispatch after response."""
        json_body(request)
        result = sessions.challenges.start(email, purpose, operation, source(request))
        delivery = result.delivery
        if delivery is not None:
            background.add_task(lambda: delivery.dispatch(sender, now=clock()))
        return ChallengeAccepted(
            challenge_id=result.challenge_id, expires_at=result.expires_at
        )

    @app.post(
        route("/auth/temporary/accounts"),
        operation_id="identity_activate_temporary_account",
        response_model=SessionView,
        status_code=201,
    )
    def activate(
        payload: ActivateTemporaryRequest, request: Request, response: Response
    ) -> SessionView:
        """Initial proof/account/credential/guard/session commit as one transaction."""
        json_body(request)
        return grant(
            response,
            sessions.activate(payload.challenge_id, payload.code, payload.password),
        )

    @app.post(
        route("/auth/temporary/sessions"),
        operation_id="identity_create_temporary_session",
        response_model=SessionView,
    )
    def login(
        payload: TemporarySessionRequest, request: Request, response: Response
    ) -> SessionView:
        """Credential exchange with uniform failures; rotate the opaque cookie."""
        json_body(request)
        return grant(
            response,
            sessions.password_login(payload.email, payload.password, source(request)),
        )

    @app.post(
        route("/auth/temporary/password-resets"),
        operation_id="identity_reset_temporary_password",
        status_code=204,
    )
    def reset(payload: ResetTemporaryPasswordRequest, request: Request) -> Response:
        """Consume/reset/revoke all sessions, requiring normal login afterward."""
        json_body(request)
        sessions.reset_password(
            payload.challenge_id, payload.code, payload.new_password
        )
        return Response(status_code=204)

    @app.get(
        route("/auth/csrf"),
        operation_id="identity_read_csrf_token",
        response_model=CsrfToken,
    )
    def csrf(request: Request) -> CsrfToken:
        """Return session-bound request token, never the bearer cookie secret."""
        current(request)
        return CsrfToken(
            csrf_token=bound_value(
                request.cookies.get(policy.session_cookie, ""), "csrf"
            )
        )

    @app.get(route("/me"), operation_id="identity_read_me", response_model=SessionView)
    def me(request: Request) -> SessionView:
        """Fresh session/current-account summary established by the middleware."""
        identity = current(request)
        sessions.capabilities.require_capability(
            identity.caller, Capability.READ_OWN_PROFILE
        )
        return session_view(identity)

    @app.delete(route("/auth/session"), operation_id="identity_logout", status_code=204)
    def logout(request: Request) -> Response:
        """Revoke current session and clear its host cookie with matching attributes."""
        sessions.logout(request.cookies.get(policy.session_cookie))
        response = Response(status_code=204)
        response.delete_cookie(
            policy.session_cookie,
            path="/",
            secure=not policy.development,
            httponly=True,
            samesite="lax",
        )
        return response

    @app.patch(
        route("/me/profile"),
        operation_id="identity_update_own_profile",
        response_model=ProfileView,
    )
    def profile(payload: ProfilePatch, request: Request) -> ProfileView:
        """Update only the current actor's reviewed display-name field."""
        json_body(request)
        return sessions.contacts.update_profile(current(request).caller, payload)

    @app.get(
        route("/me/contacts"),
        operation_id="identity_read_own_contacts",
        response_model=OwnContacts,
    )
    def own_contacts(request: Request) -> OwnContacts:
        """Expose source values only to their authenticated current owner."""
        return sessions.contacts.read_contacts(current(request).caller)

    @app.put(
        route("/me/contacts/{contact_kind}"),
        operation_id="identity_set_own_contact",
        status_code=204,
    )
    def set_contact(
        contact_kind: ContactField, payload: ContactValueRequest, request: Request
    ) -> Response:
        """Validate/update one own field; never use it as login identity."""
        json_body(request)
        sessions.contacts.set_contact(
            current(request).caller, contact_kind, payload.value
        )
        return Response(status_code=204)

    @app.delete(
        route("/me/contacts/{contact_kind}"),
        operation_id="identity_delete_own_contact",
        status_code=204,
    )
    def delete_contact(contact_kind: ContactField, request: Request) -> Response:
        """Delete immediately/idempotently; copied encrypted shares are unchanged."""
        sessions.contacts.delete_contact(current(request).caller, contact_kind)
        return Response(status_code=204)

    app.state.identity_http_installed = True
