# OTP and conversation recovery isolation — issues #78 and #79

**Date:** 2026-11-19
**Origin:** Suraj-authorized local correction of #78/#79, based on main `973e8b3`.

## OTP recovery

Registration and password reset have separate six-per-target-per-hour budgets
and cooldowns. Suppressed/ineligible requests still consume the same reservations
as eligible addresses within each purpose, preserving non-enumerating responses.
The 100-per-source-per-hour history still covers both purposes.

With the existing Turnstile runtime configured, replacing an unexpired OTP
requires a fresh server-verified challenge. A rejected anonymous replacement
cannot supersede the mailbox owner's existing code. A verified issuance may
exceed a source/target quota or cooldown and starts a fresh three-attempt budget;
it records the reservation and supersedes the previous code atomically.

All four OTP POST operations (issuance and completion for each purpose) join the
existing sign-in recovery allowlist. Only a confirmed-refused 429 offers the
widget and permits one explicit challenge-assisted replay of the same request.
Verification consumes the same cross-worker, one-use token digest as sign-in.
A challenge-assisted completion can check a correct unexpired code despite an
exhausted guess budget. Wrong codes remain rejected and the failure count
saturates at three. Challenge success does not authenticate, renew a temporary
account, revive an expired/revoked account, or bypass OTP ownership/lifecycle
checks. Old/superseded/consumed codes remain unusable. Ordinary requests cannot
clear counters; proof-assisted attempts leave abuse history intact.

No migration, new provider, widget, secret, IAM policy or build argument is
introduced. The existing matching Turnstile pair and trusted hostname remain
required. Without a configured verifier there is no challenge recovery or
protection against anonymous live-code replacement; such a configuration is
not the hardened deployment. Provider outages fail closed; normal below-limit
first-code issuance does not contact the provider. Generic Retry-After defaults
are conservative upper bounds (one hour for issuance, fifteen minutes for other
challenged operations), rather than an exact countdown.

Comprehensive bot protection and protection against sustained/volumetric abuse
remain outside project scope. A human or automation that can obtain fresh valid
provider proofs can request additional codes; Turnstile does not establish
mailbox ownership. Only the emailed OTP establishes that ownership.

## Conversation controls

A retry-request control references the other participant's original message;
the response validator must allow that relationship while preserving sender
binding for content resends and null responses. Invalid recovery metadata,
wrong target/family/original context and unsolicited response families are
explicitly rejected. Validation failures are distinct from local storage and
network failures; none produce a chat bubble or prove message recovery.

Definitively rejected controls cannot hold the visible-message cursor. Other
control failures retain a separate retry scan over server history, with at most
one extra bounded page per refresh. Its fixed horizon prevents incoming traffic
from starving a retry cycle. Only scan positions are retained locally, avoiding
an unbounded in-memory ciphertext queue. After reload, the control scan begins at sequence zero while visible messages
retain their position near the read watermark. This bounded historical scan can
add one page per refresh even before an unresolved control is rediscovered. Account/thread changes reset the scan.

Normal visible payloads still require verification/decryption and durable local
history before advancing their cursor. This change does not skip failed ordinary
message persistence. Controls can remain pending while later valid chat entries
are displayed. Independent recovery retries do not acknowledge user reads.

## Review and deployment

Suraj authorized implementation and local verification, then commit, push and PR
creation with a CI wait. Merge and deployment remain separately gated.
Independent Identity and Conversations owner review remains required.
Local HTTP checks use disposable PostgreSQL and synthetic identities/mail. Tests
of provider failure/replay use a controlled provider boundary; they are not
claims of a new real-provider or deployed retest.
