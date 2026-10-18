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
Aditya (A) owns the eventual ID-01 implementation; Identity/security affected-owner review remains pending. Store no raw OTPs, passwords or session bearer tokens. Exact password hashing scheme/parameters, verifier/token design, normalization/cross-key non-renewal guard, attempt/resend/login limits and active-session lifetime require review. Terminal-record cleanup follows the approved retention decision. Reset revocation must serialize with concurrent sign-in so it cannot leave a pre-reset session usable. Bind an OTP to its target and purpose; initial-verification OTPs cannot authorize password reset or routine login. Login identifiers are separate from editable shareable contact fields. Application-owned state does not select an email provider or authorize live email, cloud resources or account setup. Microsoft authentication continues to require signed-token verification; this does not introduce passwords for regular Microsoft accounts.

## Approver
Mohit (C): “Application-owned for now,” followed by password login with email OTP only for initial verification and forgotten-password reset. This records Mohit's direction, not an independent approval by Aditya or Rahul.

## Supersedes
None; resolves the ownership alternative left open in the initial schema draft.
