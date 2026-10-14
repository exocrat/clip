# Development Workstation Record

**Observed:** 2026-10-14 · **Recorded for:** BOOT-00 step 5

This records the existing Linux WSL environment used for the documentation bootstrap. It contains no credentials and is not evidence of application, CI, cloud, or NFR execution.

| Area | Observed fact |
|---|---|
| Distribution | Ubuntu 26.04 LTS (`WSL_DISTRO_NAME=Ubuntu`) under WSL2; Linux kernel reports `6.18.33.2-microsoft-standard-WSL2`. |
| Repository root | `/home/suraj/src/clip` |
| Agent | Codex CLI 0.162.1 at `/home/suraj/.local/bin/codex`. The CLI runs; startup reported it could not create PATH aliases because the filesystem is read-only. |
| Git | `/usr/bin/git`, version 2.53.0. Configured author: `suraj` / `surajfb2004@gmail.com`. |
| HTTP client | `/usr/bin/curl`, version 8.18.0. |
| GitHub client and credential route | `/usr/bin/gh`, version 2.46.0. Local `gh` sign-in is active and Git operations use HTTPS. Credential values are not recorded. |
| Container route | `/usr/bin/docker`, version 29.1.3, using context `default`. The local engine responded as Ubuntu 26.04 LTS, version 29.1.3, with Docker root `/var/lib/docker`. No Podman executable was found. |

## Current gaps

- No application startup, stop, migration, seed, or check commands are registered yet; PD-13 owns their implementation and verification.
- Cloud account, role, region, and shared cloud resource facts have not been inspected. PD-14–PD-16 own those checks; this record does not imply cloud access or approval.
- The Codex PATH-alias warning is recorded above. Its executable remains available at the observed path.

These are workstation observations from BOOT-00, not a pinned team-wide toolchain or proof that project commands have been tested.
