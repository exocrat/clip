# Secret Reference and Access Procedure

**Version:** 3.0 · **Date:** 2026-10-14 · **Canonical path:** `docs/environment/secret-handling.md`

This template contains NO secret values. PD-03 initializes it, PD-14 records the approved shared secret manager/access method, and ID-01/CN-03/other owners add their configured references when actually needed. The agent must not ask the human to paste passwords/MFA/OTP/private keys/access keys/tokens in chat or commit them. Local environment files remain untracked. Real secrets belong in the selected manager/access-controlled channel, never fixtures/logs/evidence.

For each configured reference record only: purpose/name/reference identifier, responsible owner, environment/account, approved access role/procedure, permission scope, rotation/revocation and unavailable-access recovery, task that established it, and non-secret verification evidence. Current shared access method: **not configured**; current provider/database references: **not configured**. Resolve by the named tasks, not by inventing values.

Read approved access procedure before asking; request access just in time only for the assigned step. If human-only account/device work is needed, give exact safe actions and expected non-secret output, wait and verify afterward. A missing access method/prerequisite blocks its dependent operation. Provider setup/auth/permitted-recipient behavior must not weaken production security or send to fabricated real addresses.
