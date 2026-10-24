"""Ephemeral signed-token fixtures; no private key/token is written or sent."""

import json

import jwt

from app.domains.identity.microsoft import (
    CLIENT_ID,
    DISCOVERY,
    ISSUER,
    JWKS,
    MicrosoftKeys,
    MicrosoftTokenValidator,
)

TENANT = "11111111-2222-4333-8444-555555555555"
NONCE = "synthetic-server-bound-login-nonce"
EMAIL = "clip-test-fixture-do-not-send@iisc.ac.in"


class SignedTokens:
    """Sign synthetic claims with explicit in-memory key/time; permit negatives."""

    def __init__(self, clock, key):
        """Use explicitly controlled UTC and shared ephemeral signing material."""
        self.clock = clock
        self.key = key
        self.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        self.jwk.update(kid="synthetic-key", use="sig", issuer=ISSUER)

    def claims(self):
        now = int(self.clock().timestamp())
        return {
            "iss": ISSUER.replace("{tenantid}", TENANT),
            "tid": TENANT,
            "ver": "2.0",
            "aud": CLIENT_ID,
            "sub": "synthetic-subject",
            "iat": now - 2,
            "nbf": now - 2,
            "exp": now + 300,
            "nonce": NONCE,
            "email": EMAIL,
        }

    def token(self, overrides=None, remove=(), *, key=None, headers=None):
        claims = self.claims() | (overrides or {})
        for field in remove:
            claims.pop(field, None)
        return jwt.encode(
            claims,
            key or self.key,
            algorithm="RS256",
            headers={"kid": "synthetic-key", **(headers or {})},
        )

    def document(self, url):
        if url == DISCOVERY:
            return {
                "issuer": ISSUER,
                "jwks_uri": JWKS,
                "id_token_signing_alg_values_supported": ["RS256"],
            }
        assert url == JWKS
        return {"keys": [self.jwk]}

    def validator(self):
        return MicrosoftTokenValidator(MicrosoftKeys(self.document))
