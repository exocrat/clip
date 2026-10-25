# Development Workstation Record

## Mohit's repository-local native SQL setup — SE-01, 2026-10-24

PostgreSQL 18.6 was built with existing Clang 14/make and installed only under
`.tools/native-db/pgsql`; dbmate 2.36.0's checksum-verified ARM64 binary is under
`.tools/native-db/downloads/`. Source/build/download logs occupy about 300 MiB.
The earlier `/tmp/clip-pd08-native.pKC5jz` tools were gone. No global/Homebrew
service, Docker, PATH/system Python edit or cloud action. The native harness's
fresh TCP-disabled private clusters were stopped; logs/data remain under printed
`/tmp/clip-pd08-native-check.*` directories. Four real database cases, three pre-connect guards and the
schema round trip passed; [evidence](../evaluation/domain/se-01/native-postgres/result.json).
This is Mac UTF-8/C/no-ICU scope, not production/Linux/TLS/resource equivalence.


## Mohit's semantic-runtime feasibility check — 2026-10-24

Read-only `sw_vers` confirms macOS 13.7.8 (build 22H730), ARM64; local project
Python remains 3.14.3. Published ONNX Python 3.14 ARM64 wheels target macOS 14.
Mohit subsequently verified the separate project-local helper probe. Python
3.13.12, its isolated environment, 24 locked packages and verified model files
are now under `.tools/semantic/` (about 528 MiB including caches). The API retains
Python 3.14.3/root lock; no global links, OS changes or system Python edits.
The [feasibility plan/result](../architecture/semantic-search-feasibility.md)
records successful local inference and the remaining production/Linux/native gates.


## Mohit's repository-local Node setup — SE-01, 2026-10-24

Node 24.22.0 and its bundled npm 11.19.1 are under `.tools/node/` on this macOS
ARM64 checkout. The archive SHA-256 matched the official v24.22.0 checksum list:
`6a9724d9b50a5f22b4816cded441b5a8d9ddae546191a5e5b7efa5a5e2ee26d5`.
Root `npm ci --no-audit --no-fund` installed the committed lockfile with cache
at `.tools/npm-cache/`; no manifest/lockfile or global PATH/system tool changed.
Commands set process-local PATH and disable user npm configuration explicitly:

```bash
PATH="$PWD/.tools/node/bin:$PATH" NPM_CONFIG_CACHE="$PWD/.tools/npm-cache" NPM_CONFIG_USERCONFIG=/dev/null .tools/node/bin/npm run check
```

The same prefix runs `npm ci`, `npm run dev`, or the registered checks. No
Docker install was performed. See the web guide for the labelled UI-only
preview and pending real backend/browser checks.

## Mohit's repository-local Python setup — SE-01, 2026-10-24

This macOS ARM64 checkout uses uv 0.10.7 at `.tools/uv/uv` and Python
3.14.3 under `.tools/python/`, with project packages in `.venv/` and the uv
cache in `.tools/cache/`. These directories are Git-ignored. Python was
installed with `--no-bin`: no global executable links, PATH edits, or system
Python replacement. The prior broken `.venv` was preserved at
`.tools/venv-before-se01/`; its interpreter had pointed into a deleted `/tmp`
directory. The interrupted Homebrew attempt left no installed uv formula.

From the repository root, keep subsequent Python downloads/cache local:

```bash
UV_PYTHON_INSTALL_DIR="$PWD/.tools/python" UV_CACHE_DIR="$PWD/.tools/cache" .tools/uv/uv sync --locked --python 3.14.3
```

After synchronization, `.venv/bin/python` runs the local interpreter directly.
Docker and Node/npm are not installed by this setup; database, browser and
aggregate checks remain pending until their real prerequisites are available.

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
