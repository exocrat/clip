# Campus Marketplace — Existing WSL, Codex and First Session

**Version:** 3.1 · **Date:** 2026-10-14 · **Canonical path:** `docs/environment/wsl-and-first-session.md`

## What this setup does

You already have WSL. Reuse it; do not reinstall or reset the distribution. The project repository already exists at **https://github.com/exocrat/clip**. The agent clones/preserves that repository; it does not create a second GitHub repository. This guide distinguishes the downloaded documentation bundle, the real Git clone and the later running application.

Recommended Windows route: Linux Codex CLI inside the existing WSL 2 distribution, with the working clone at `~/src/clip` in the Linux filesystem. A WSL-connected editor is optional. Linux containers are the cloud runtime baseline; ECS may manage compute without a team-managed VM. WSL is a useful local environment, but CI/deployed tests are still required.

## One-time access before an agent can operate

The human only performs the actions needed to give the agent filesystem/terminal access and complete account/device prompts. After the agent is running, it handles routine clone, document installation and project setup through numbered tasks and human verification. These access steps are not a claim that BOOT-00 or a PD task is complete.

1. Open Windows PowerShell and inspect the existing distributions:

   ```powershell
   wsl --list --verbose
   ```

   Expected: your existing distribution is listed with VERSION 2. Open that distribution's terminal. If it is VERSION 1, unavailable or broken, ask for a repair/conversion plan; do not uninstall it. Use its actual name rather than assuming `Ubuntu`.

2. In that WSL terminal check the shell and basic access tools:

   ```bash
   uname -s
   pwd
   command -v git
   command -v curl
   command -v codex
   ```

   Expected: Linux; a readable Linux user path; Linux Git/curl and, if already installed, Codex. Check `type -a git curl codex` if a command resolves through `/mnt/c/` or a Windows `.exe`. Use Linux binaries for repository work. If Git/curl are missing on an Ubuntu/Debian distribution, install only those prerequisites through the distribution package manager; a sudo password is entered locally, never in chat:

   ```bash
   sudo apt-get update
   sudo apt-get install git curl ca-certificates
   ```

   For another distribution, use its official equivalent. Application Python/Node/dependency versions are selected by PD-02; do not independently reinstall or pin the whole project toolchain here.

3. If Linux Codex is already available, run `codex --version` and reuse it. Otherwise use the current official Linux CLI installer. One way to review it before running is:

   ```bash
   curl -fsSL https://chatgpt.com/codex/install.sh -o /tmp/clip-codex-install.sh
   less /tmp/clip-codex-install.sh
   sh /tmp/clip-codex-install.sh
   ```

   Follow the installer's PATH instructions, reopen the WSL terminal if needed, and verify `command -v codex` and `codex --version`. Do not use sudo merely to bypass a user-install permission problem. If installation or sign-in differs from these instructions, consult the official CLI page linked below and ask rather than guess.

4. Create a Linux staging location for the downloaded bundle:

   ```bash
   mkdir -p ~/clip-bootstrap
   cd ~/clip-bootstrap
   explorer.exe .
   ```

   In the opened File Explorer window extract the downloaded v3 ZIP here. Expected: `~/clip-bootstrap/campus-marketplace-documents/README.md`, `AGENTS.md`, `CONTRIBUTING.md` and `docs/`. The archive's top folder is intentional. This is a documentation source folder, not the Git clone. Windows Downloads is fine for receiving the ZIP; active builds/virtual environments/node_modules belong in the Linux clone, not `/mnt/c/...`.

5. Start the Linux CLI from that extracted source folder:

   ```bash
   cd ~/clip-bootstrap/campus-marketplace-documents
   codex
   ```

   Complete the displayed ChatGPT or supported account sign-in locally. Confirm the session directory is the extracted Linux folder. Never paste passwords, login codes, tokens or keys into the project chat/files. Use the CLI interactively; an unattended execution command does not provide the required verify-after-every-step cycle.

6. Copy the complete reusable prompt from `docs/prompts/reusable-task-prompt.md`, then add:

   ```text
   This folder is the supplied documentation bundle. WSL is already installed.
   The existing target repository is https://github.com/exocrat/clip.
   Use ~/src/clip as the proposed working clone, preserving any existing files.
   Execute BOOT-00: inspect read-only, explain the full task sequence, and wait.
   Execute one numbered step per verification. Ask about every uncertainty.
   ```

   The agent reads the bundle and BOTH supplied checklists immediately. You verify its full-task understanding, then its individual steps. BOOT-00 performs the clone/folder/document/Git work and verifies the actual remote state.

## Clone/folder actions performed by BOOT-00

After the numbered-step approval, the agent checks `~/src/clip` before writing. If absent, the intended commands are:

```bash
mkdir -p ~/src
git clone https://github.com/exocrat/clip.git ~/src/clip
```

If access requires GitHub authentication, use the approved local credential-manager/browser/SSH route; never embed a token in the remote URL. A private/inaccessible repo is an access blocker, not permission to create another repo. If the target exists, inspect its Git root, remote, changes and active work; preserve it and ask about any conflicting destination. Do not clone over it or run a second Git initialization inside it.

Copy the **contents** of `campus-marketplace-documents/` into the clone root after conflict inspection. Expected target: `~/src/clip/README.md`, `~/src/clip/AGENTS.md`, `~/src/clip/CONTRIBUTING.md`, `~/src/clip/docs/...` plus the clone's existing `.git`. Do not create `~/src/clip/campus-marketplace-documents/docs/`, overwrite `.git`, or copy Windows environments/credentials. Report the actual changed files before the initial documentation commit/push gate.

For the one-time BOOT-00 documentation seed, the team has approved a direct-to-`main` exception even though the existing repository has a README commit. A separate peer review is not required for this exception; inspect the exact staged diff after the documentation audit and before commit. Do not change hosting protections. The push remains a separate approval gate. Later implementation uses task/milestone branches and peer-reviewed PRs; merge does not deploy infrastructure.

## After BOOT-00 and each later session

1. Exit the staging-folder session after its verified bootstrap handoff. Open the actual clone:

   ```bash
   cd ~/src/clip
   git rev-parse --show-toplevel
   git remote -v
   codex
   ```

   Expected root: the real clone, and `origin` resolves to `exocrat/clip` using the approved HTTPS/SSH spelling. Do not output an embedded-secret URL. An existing local clone may use a different verified Linux path; record it in the workstation record.

2. Paste the same reusable prompt, then say `Continue PD-00` for the first foundation session or `Continue the next required task assigned to [my recorded name/role]` later. The agent checks actual status and the checklists; it does not redo verified steps.
3. If using an editor, open this clone through its WSL connection. For an already configured VS Code WSL installation, `code .` opens the current folder; verify the WSL indicator and Linux terminal. Do not assume a desktop/IDE agent is using Linux just because it can display WSL files: have it report `uname -s`, executable paths and Git root before writes. The CLI route above is sufficient; an editor extension is optional.
4. PD-13 supplies verified application setup/start/stop/migration/seed/check commands. Until then there is no application to launch. Later sessions use those registered commands instead of inventing `npm start` or a guessed container command.

If you already cloned `exocrat/clip` into WSL and installed the bundle correctly, launch from that clone and give the reusable prompt. BOOT-00 reconciles existing facts; it does not clone/copy/commit them again.

## Local toolchain verification within pre-domain

PD-02/04/08/12/13 inspect and document Linux Python/Node versions and managers, pinned Black, database/container access, Git identity/credential route, line endings, executable permissions, case-sensitive imports and local browser/API/database connectivity. For containers choose one verified Docker route: existing Docker Desktop WSL integration or a documented Linux engine. Check `docker version`/the registered Compose route when the chosen setup uses Docker; do not install a second daemon blindly. AWS/Terraform access is checked by PD-14–16. Use localhost for local clients as verified by PD-13; never copy cloud secrets into repo files to make local access work.

The non-secret workstation record created in BOOT-00/extended by PD-02 is `docs/environment/development-workstation.md`: actual distribution/version, Linux repo root, agent/interface/version, executable paths, chosen container route, tested connectivity, installation gaps, expected/observed checks and next owner. No tokens or machine-specific home paths become required global project configuration. Every teammate uses their own clone/worktree.

## Official references checked 2026-10-14

- [OpenAI Codex CLI installation, sign-in and project-directory launch](https://learn.chatgpt.com/docs/codex/cli)
- [Microsoft: Windows/WSL filesystem placement and interoperability](https://learn.microsoft.com/en-us/windows/wsl/filesystems)
- [Microsoft: Git with WSL](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-git)
- [Microsoft: WSL development environment](https://learn.microsoft.com/en-us/windows/wsl/setup/environment)

CLI installation/account UI can change; recheck the official page if the observed behavior differs. These setup instructions have not been executed on the user's computer by this document revision.
