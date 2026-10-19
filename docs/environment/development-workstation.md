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

- PD-07 Step 1 now supplies the web install/start/stop/typed-build path below. Database/migration/seed and combined setup remain with their creator tasks; PD-13 verifies the combined lifecycle.
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

## Current contributor setup — PD-07 Step 1

**Observed:** 2026-10-17 06:36:53 UTC · **Contributor:** Suraj (B), Stream 2 ·
**Branch:** `task/pd-07-web-foundation`

The workstation remains Linux x86_64 under WSL2 kernel
`6.18.33.2-microsoft-standard-WSL2`. Node/npm were absent from the session PATH
before this step. Installed the official Node 24.22.0 Linux x64 distribution at
`/home/suraj/src/.clip-tools/node-v24.22.0-linux-x64`, outside the repository,
without sudo or shell-startup changes. `node --version` reports `v24.22.0` and
the bundled `npm --version` reports `11.19.1`.

The archive matched the Node release's published SHA-256 value
`cc2f601cee82d9a5a233302fe307abc600727035fd7d2c3a3571755989e95008`
before extraction. This is the current contributor's setup, not an instruction
for other contributors to use a Linux x64 binary on another platform.

For a new shell in this workstation, activate that existing installation:

```bash
export PATH=/home/suraj/src/.clip-tools/node-v24.22.0-linux-x64/bin:$PATH
```

The agent used `NPM_CONFIG_CACHE=/tmp/clip-npm-cache` because its sandbox cannot
write the default user npm cache. This cache override is optional for an ordinary
writable contributor environment. The runtime install persists; the temporary
cache may be recreated. No global npm package or different Node/npm release
was installed.

Verified the root lockfile install and typed Vite production build, rendered the
real bootstrap component through React's server renderer, and checked dev/preview
HTML and JavaScript over loopback. Both listeners bound only to `127.0.0.1`;
the duplicate development-port check failed as intended, and Ctrl+C stopped both
owned servers. The build output and dependency/cache directories are ignored.
This proves the technical mount point, not browser UI workflows or domain
integration; later PD-07 checks and PD-13 clean-teammate setup remain pending.


## PD-16 operator prerequisite — 2026-10-19

Current continuation machine `/home/mainberry/IISc/clip`: Debian 13 ARM64, distinct from the historical WSL workstation above. User approved installation of the official AWS ARM64 Session Manager plugin. HTTPS package metadata was `session-manager-plugin` 1.2.896.0-1, architecture arm64; SHA-256 `914eeca87b18b55356c58be197080f73742b3ca60d3823f0a45670dc9056aa9c`. `sudo dpkg -i` succeeded and `session-manager-plugin --version` returned 1.2.896.0. [Official installation procedure](https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-debian-and-ubuntu.html). No SSM cloud session was opened. PATH Terraform is 1.16.5; use the existing pinned 1.15.9 binary for project planning, not PATH.
