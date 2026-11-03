"""Actual RSA verification and fixed-origin cache safety, without provider I/O."""

from datetime import UTC, timedelta
import json

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from app.core.config import ConfigurationError, Settings, load_settings
from app.core.errors import PublicError
from app.domains.identity.microsoft import (
    CLIENT_ID,
    DISCOVERY,
    ISSUER,
    JWKS,
    MicrosoftKeys,
    MicrosoftTokenValidator,
    fetch_document,
)
from app.domains.identity.microsoft_accounts import MicrosoftAccountService
from apps.api.tests.domains.identity.microsoft_fixtures import EMAIL, NONCE, TENANT


def denied(validator, token, *, status=401, nonce=NONCE):
    with pytest.raises(PublicError) as exc:
        validator.verify(token, expected_nonce=nonce)
    assert exc.value.spec.status == status
    assert str(exc.value) in {"unauthenticated", "dependency_unavailable"}
    assert token not in str(exc.value) and EMAIL not in str(exc.value)


def test_valid_signed_identity_and_private_repr(signed_tokens):
    value = signed_tokens.validator().verify(
        signed_tokens.token(), expected_nonce=NONCE
    )
    assert value.issuer == ISSUER.replace("{tenantid}", TENANT)
    assert value.subject == "synthetic-subject" and value.email == EMAIL
    assert value.expires_at.tzinfo == UTC
    assert EMAIL not in repr(value) and value.subject not in repr(value)


@pytest.mark.parametrize(
    "claim", ["exp", "iat", "iss", "aud", "sub", "tid", "ver", "nonce", "email"]
)
def test_missing_required_claim(signed_tokens, claim):
    denied(signed_tokens.validator(), signed_tokens.token(remove=[claim]))


@pytest.mark.parametrize(
    "change",
    [
        {"aud": "other-client"},
        {"aud": [CLIENT_ID]},
        {"iss": "https://issuer.example.invalid"},
        {"iss": ISSUER.replace("{tenantid}", "common")},
        {"tid": "../untrusted"},
        {"ver": "1.0"},
        {"sub": ""},
        {"sub": 123},
        {"email": None},
        {"email": "x@iisc.ac.in.attacker.invalid"},
        {"email": "x@sub.iisc.ac.in"},
        {"email": "x@iisc.ac.in@attacker.invalid"},
        {"email": "x@іisc.ac.in"},
        {"email": "@iisc.ac.in"},
        {"email": "x@iisc.ac.in "},
        {"email": "x\n@iisc.ac.in"},
        {"email": "Person <x@iisc.ac.in>"},
        {"nonce": "wrong-nonce"},
        {"exp": True},
        {"iat": False},
        {"nbf": True},
    ],
)
def test_invalid_claims_are_generic(signed_tokens, change):
    denied(signed_tokens.validator(), signed_tokens.token(change))


def test_expired_future_dates_and_bad_lifetime(signed_tokens):
    now = int(signed_tokens.clock().timestamp())
    for change in [
        {"exp": now - 1, "iat": now - 100},
        {"iat": now + 60},
        {"nbf": now + 60},
        {"iat": now - 1, "exp": now - 2},
    ]:
        denied(signed_tokens.validator(), signed_tokens.token(change))


def test_wrong_signature_and_unsigned_token(signed_tokens):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    denied(signed_tokens.validator(), signed_tokens.token(key=other))
    unsigned = jwt.encode(
        signed_tokens.claims(), None, algorithm="none", headers={"kid": "synthetic-key"}
    )
    denied(signed_tokens.validator(), unsigned)
    denied(signed_tokens.validator(), "not-a-jwt")


def test_domain_case_and_distinct_tenants_are_supported(signed_tokens):
    validator = signed_tokens.validator()
    assert (
        validator.verify(
            signed_tokens.token({"email": EMAIL.upper()}), expected_nonce=NONCE
        ).email
        == EMAIL.upper()
    )
    other_tenant = "66666666-7777-4888-8999-000000000000"
    value = validator.verify(
        signed_tokens.token(
            {"tid": other_tenant, "iss": ISSUER.replace("{tenantid}", other_tenant)}
        ),
        expected_nonce=NONCE,
    )
    assert value.issuer.endswith(other_tenant + "/v2.0")


def test_no_username_or_unsigned_email_fallback(signed_tokens):
    denied(
        signed_tokens.validator(),
        signed_tokens.token({"preferred_username": EMAIL}, remove=["email"]),
    )
    denied(
        signed_tokens.validator(),
        signed_tokens.token(
            {"email": "x@example.invalid", "preferred_username": EMAIL}
        ),
    )


@pytest.mark.parametrize(
    "change",
    [
        {"issuer": "https://other.example.invalid"},
        {"kty": "EC"},
        {"use": "enc"},
        {"alg": "HS256"},
    ],
)
def test_signing_key_must_bind_to_issuer_and_algorithm(signed_tokens, change):
    def documents(url):
        return (
            {"keys": [signed_tokens.jwk | change]}
            if url == JWKS
            else signed_tokens.document(url)
        )

    denied(MicrosoftTokenValidator(MicrosoftKeys(documents)), signed_tokens.token())


def test_literal_key_issuer_cannot_sign_another_tenant(signed_tokens):
    def documents(url):
        key = signed_tokens.jwk | {"issuer": ISSUER.replace("{tenantid}", TENANT)}
        return {"keys": [key]} if url == JWKS else signed_tokens.document(url)

    validator = MicrosoftTokenValidator(MicrosoftKeys(documents))
    validator.verify(signed_tokens.token(), expected_nonce=NONCE)
    other = "66666666-7777-4888-8999-000000000000"
    denied(
        validator,
        signed_tokens.token({"tid": other, "iss": ISSUER.replace("{tenantid}", other)}),
    )


def test_cache_refresh_and_unknown_kid_are_bounded(signed_tokens):
    calls = []
    clock = [0.0]

    def documents(url):
        calls.append(url)
        return signed_tokens.document(url)

    keys = MicrosoftKeys(documents, lambda: clock[0])
    validator = MicrosoftTokenValidator(keys)
    for _ in range(3):
        validator.verify(signed_tokens.token(), expected_nonce=NONCE)
    assert calls == [DISCOVERY, JWKS]
    for _ in range(5):
        denied(validator, signed_tokens.token(headers={"kid": "unknown"}))
    assert len(calls) == 2
    clock[0] = 31
    denied(validator, signed_tokens.token(headers={"kid": "unknown"}))
    assert len(calls) == 4
    clock[0] = 332
    validator.verify(signed_tokens.token(), expected_nonce=NONCE)
    assert len(calls) == 6


@pytest.mark.parametrize(
    "document",
    [
        {
            "issuer": ISSUER,
            "jwks_uri": "http://127.0.0.1/private",
            "id_token_signing_alg_values_supported": ["RS256"],
        },
        {},
        {
            "issuer": ISSUER,
            "jwks_uri": JWKS,
            "id_token_signing_alg_values_supported": ["HS256"],
        },
    ],
)
def test_discovery_failure_is_safe_and_does_not_follow_urls(signed_tokens, document):
    calls = []

    def documents(url):
        calls.append(url)
        return document

    denied(
        MicrosoftTokenValidator(MicrosoftKeys(documents)),
        signed_tokens.token(),
        status=503,
    )
    assert calls == [DISCOVERY]


def test_provider_failure_has_no_account_side_effect(signed_tokens):
    def unavailable(url):
        raise RuntimeError("PRIVATE_PROVIDER_PAYLOAD")

    class Accounts:
        def get_or_create(self, identity):
            pytest.fail("Account write before validation")

    service = MicrosoftAccountService(
        MicrosoftTokenValidator(MicrosoftKeys(unavailable)), Accounts()
    )
    with pytest.raises(PublicError) as exc:
        service.authenticate(signed_tokens.token(), expected_nonce=NONCE)
    assert exc.value.spec.status == 503 and "PRIVATE" not in str(exc.value)


def test_fixed_fetch_refuses_untrusted_url():
    with pytest.raises(PublicError) as exc:
        fetch_document("http://127.0.0.1/private")
    assert exc.value.spec.status == 503


def test_disabled_and_production_configuration_are_closed(monkeypatch):
    with pytest.raises(PublicError):
        MicrosoftTokenValidator.from_settings(Settings())
    monkeypatch.setenv("CLIP_ENVIRONMENT", "production")
    monkeypatch.setenv("CLIP_IDENTITY_PROVIDER", "microsoft")
    with pytest.raises(ConfigurationError):
        load_settings()
    validator = MicrosoftTokenValidator.from_settings(
        Settings(environment="test", identity_provider="microsoft")
    )
    assert isinstance(validator, MicrosoftTokenValidator)


def test_expired_key_cache_does_not_fall_back_after_provider_failure(signed_tokens):
    clock = [0.0]
    fail = [False]
    calls = []

    def documents(url):
        calls.append(url)
        if fail[0]:
            raise RuntimeError("PRIVATE_PROVIDER_PAYLOAD")
        return signed_tokens.document(url)

    validator = MicrosoftTokenValidator(MicrosoftKeys(documents, lambda: clock[0]))
    validator.verify(signed_tokens.token(), expected_nonce=NONCE)
    fail[0] = True
    clock[0] = 301
    denied(validator, signed_tokens.token(), status=503)
    clock[0] = 302
    denied(validator, signed_tokens.token(), status=503)
    assert len(calls) == 3


def test_untrusted_jku_never_selects_a_network_origin(signed_tokens):
    calls = []

    def documents(url):
        calls.append(url)
        return signed_tokens.document(url)

    validator = MicrosoftTokenValidator(MicrosoftKeys(documents))
    validator.verify(
        signed_tokens.token(headers={"jku": "http://127.0.0.1/private"}),
        expected_nonce=NONCE,
    )
    assert calls == [DISCOVERY, JWKS]
    denied(validator, signed_tokens.token(headers={"crit": []}))


def test_consumer_tenant_remains_allowed_for_matching_signed_email(signed_tokens):
    tenant = "9188040d-6c67-4c5b-b112-36a304b66dad"
    value = signed_tokens.validator().verify(
        signed_tokens.token(
            {"tid": tenant, "iss": ISSUER.replace("{tenantid}", tenant)}
        ),
        expected_nonce=NONCE,
    )
    assert value.email == EMAIL


@pytest.mark.parametrize(
    "email", [".fixture@iisc.ac.in", "fixture.@iisc.ac.in", "a..fixture@iisc.ac.in"]
)
def test_malformed_local_part_is_rejected(signed_tokens, email):
    denied(signed_tokens.validator(), signed_tokens.token({"email": email}))


@pytest.mark.parametrize("claim", ["exp", "nbf", "iat"])
def test_exact_signed_numeric_date_boundary(signed_tokens, jwt_clock, claim):
    """Real RSA/zero-leeway date verification at an exact controlled boundary."""
    instant = jwt_clock[0]
    token = signed_tokens.token({claim: int(instant.timestamp())})
    validator = signed_tokens.validator()
    if claim == "exp":
        jwt_clock[0] = instant - timedelta(microseconds=1)
        validator.verify(token, expected_nonce=NONCE)
        jwt_clock[0] = instant
        denied(validator, token)
    else:
        jwt_clock[0] = instant - timedelta(microseconds=1)
        denied(validator, token)
        jwt_clock[0] = instant
        validator.verify(token, expected_nonce=NONCE)


def test_signed_fixture_claims_are_reproducible_at_fixed_time(signed_tokens):
    first = signed_tokens.claims()
    assert first == signed_tokens.claims()
    assert first["exp"] - first["iat"] == 302
    assert first["exp"] == 1893456300


def test_test_tenant_requires_signed_exact_username_domain(signed_tokens):
    """Permit users of the specified tenant/domain, never other tenants or domains."""
    tenant = "19d07278-f040-4722-8202-b1174cf3a4d3"
    claims = {
        "tid": tenant,
        "iss": ISSUER.replace("{tenantid}", tenant),
        "oid": "81cc6bfd-631b-4e8e-b941-dcc43f19093e",
        "preferred_username": "clip-test-user@medheadityagmail.onmicrosoft.com",
        "email": "test@example.com",
    }
    validator = signed_tokens.validator()
    assert (
        validator.verify(signed_tokens.token(claims), expected_nonce=NONCE).subject
        == "synthetic-subject"
    )
    assert (
        validator.verify(
            signed_tokens.token(claims, remove=("email",)), expected_nonce=NONCE
        ).email
        is None
    )
    another = claims | {
        "oid": "11111111-2222-4333-8444-555555555555",
        "preferred_username": "another@medheadityagmail.onmicrosoft.com",
    }
    assert (
        validator.verify(
            signed_tokens.token(another, remove=("email",)), expected_nonce=NONCE
        ).email
        is None
    )
    for change in (
        {"preferred_username": "other@other.onmicrosoft.com"},
        {"preferred_username": "user#EXT#@medheadityagmail.onmicrosoft.com"},
        {"oid": "not-a-uuid"},
        {"tid": TENANT, "iss": ISSUER.replace("{tenantid}", TENANT)},
        {"aud": "other"},
    ):
        denied(validator, signed_tokens.token(claims | change))
    denied(validator, signed_tokens.token(claims, remove=("preferred_username",)))
