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

## Current contributor check — PD-02 Step 1

**Observed:** 2026-10-16 · **Recorded by:** kickoff owner (B) · **Repository revision:** `fb10d3d` on `task/pre-domain-foundation`

This is a fresh check of the current contributor's WSL workstation. It does not define the supported team-wide platforms or select project runtime versions.

| Area | Observed fact |
|---|---|
| Host and shell | Ubuntu 26.04 LTS in WSL2; kernel `6.18.33.2-microsoft-standard-WSL2`; architecture `x86_64`; WSL distribution `Ubuntu`; shell `/bin/bash`, version 5.3.9. |
| Repository | `/home/suraj/src/clip`; Git root matches the working directory. Existing documentation changes were present and preserved. |
| Git and HTTP client | `/usr/bin/git`, version 2.53.0; `/usr/bin/curl`, version 8.18.0. |
| Agent | `/home/suraj/.local/bin/codex`, version 0.162.1. Startup reported it could not create PATH aliases because the filesystem is read-only; the executable runs. |
| Python | `/usr/bin/python3`, version 3.14.4. This is the installed workstation version, not a project selection. |
| Node | `node` and `npm` are not installed/on PATH. |
| Python package managers | `uv` and `poetry` are not installed/on PATH. |
| Container route | `/usr/bin/docker`, client and Linux/amd64 Engine version 29.1.3, context `default`; engine responded. Neither the `docker compose` plugin nor standalone `docker-compose` is available. `podman` is not installed/on PATH. No container or project service was started. |

No tools were installed or changed. These observations are for this contributor only; PD-02 must select and document team toolchain/platform support separately.
