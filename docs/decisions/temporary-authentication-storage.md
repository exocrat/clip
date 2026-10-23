# Application-owned temporary authentication storage

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 Identity storage review.

## Question
Should the provider or CLIP own temporary-account OTP and session state?

## Options considered
- Provider-owned challenge/session state, with CLIP retaining verified identity references and account lifecycle.
- Application-owned challenge/session state, requiring explicit verifier, concurrency, expiry, revocation and cleanup controls.

## Selected choice
Use application-owned OTP challenge and session persistence for now, as directed by Mohit. Include `identity.otp_challenges` and `identity.sessions` in the MVP schema proposal. A future provider-managed replacement requires a reviewed update and migration plan; it is not an implicit fallback.

Temporary users normally sign in with a password. Email OTP is used only for initial verification and forgotten-password reset, not as a routine sign-in alternative. Include a separate temporary credential record with the stable login identifier and password hash. Password reset does not reactivate an expired/revoked account or restart its original 14-day lifetime.

Mohit approved starting that lifetime at first successful initial email verification: exactly 14 × 24 hours from its UTC activation instant. A successful password reset atomically updates the hash, consumes the challenge and revokes all existing sessions; normal password sign-in is then required. Registration/password entry, resend, repeat verification and login do not restart activation.

## Rationale
Records the current implementation direction explicitly so PD-08 does not omit required local authentication state.

## Implications
Aditya (A) owns the eventual ID-01 implementation; the user later confirmed the PD-08 Identity/security affected-owner gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). Store no raw OTPs, passwords or session bearer tokens. Step 5 choices below resolve the approved OTP/password primitives; password-login limits, active-session lifetime and coordinated key-change procedures still require review in their owning increments. Terminal-record cleanup follows the approved retention decision. Reset revocation must serialize with concurrent sign-in so it cannot leave a pre-reset session usable. Bind an OTP to its target and purpose; initial-verification OTPs cannot authorize password reset or routine login. Login identifiers are separate from editable shareable contact fields. Application-owned state does not select an email provider or authorize live email, cloud resources or account setup. Microsoft authentication continues to require signed-token verification; this does not introduce passwords for regular Microsoft accounts.

## Approver
Mohit (C): “Application-owned for now,” followed by password login with email OTP only for initial verification and forgotten-password reset. This records Mohit's direction, not an independent approval by Aditya or Rahul.

## Supersedes
None; resolves the ownership alternative left open in the initial schema draft.

## ID-01 Step 5 approved implementation parameters

Aditya verified the Step 5 plan with the following correction on
2026-10-23 18:47:21 UTC (recording time): allow three failed verifications per
normalized target and purpose, shared across resends, until the latest OTP
expires. Resend preserves failures and moves the window expiry to the newest
code's expiry. At three failures, verification and resend remain blocked until
that expiry; a new request after expiry may start a fresh budget.

Codes are six random decimal digits, valid for ten minutes. Send limits are a
60-second cooldown, six per target per trailing hour and 100 per trusted source
IP per trailing hour. Normalize ASCII addresses by trimming outer whitespace
and lowercasing the whole address, preserving dots and plus aliases. Bind keyed
verifiers and authenticated target encryption to challenge, purpose, target and
expiry, using separate versioned 256-bit keys for lookup, verifier and AES-GCM.
No raw OTP is persisted. No automatic key rotation or live send is authorized.

The verified password plan for Steps 6–7 uses Argon2id with 19 MiB memory,
two iterations and parallelism one, accepting 15–128 characters including
spaces. This record does not claim password activation/login/reset is implemented.
Aditya approved service-lifetime retention of minimal request deduplication
markers on2026-10-23 19:53:44 UTC (recording time). Preserve only the keyed request
digest, key version, challenge ID and original expiry; no email, IP, target
digest, OTP, verifier or target ciphertext. Same-operation retries must never
resend after challenge cleanup. These markers remain sensitive/linkable. The
[canonical retention decision](private-data-retention.md) records this narrow
exception; ordinary private-data windows and destructive cleanup review remain.
No automatic key rotation, cleanup execution or cloud action is authorized.
