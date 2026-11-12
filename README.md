# CLIP — Campus Listing and Item Platform

The site is live at [clip-iisc.site](https://clip-iisc.site).

CLIP is an IISc-focused marketplace for finding and listing items, posting wanted requests, and communicating privately with other members. It supports seller-controlled availability, saved listings, offers, and deliberate contact sharing. The platform does not process payments or verify item quality, delivery, or handover.

The repository contains the React web client, FastAPI service, PostgreSQL migrations, infrastructure and evaluation tooling. Some features require configured external providers; a successful local startup or synthetic preview does not establish production readiness. See the [work log](docs/status/work-log.md) for current evidence.

## Documentation

- [Product requirements (PRD)](PRD.md) — original goals, requirements, and acceptance targets.
- [Developer guide](dev.md) — architecture, code map, workflows, and checks.
- [Contributing](CONTRIBUTING.md) — ownership, review, and Git process.
- [Documentation index](docs/README.md) — canonical decisions, task status, and operational guides.

## Prerequisites

Run commands from the repository root in Bash on a supported Linux or macOS setup. You need Git, GNU Make, Python 3.14, [uv](https://docs.astral.sh/uv/), Node.js 24 with npm 11 (CI uses Node 24.22.0 and npm 11.19.1), and a local Docker Engine with Compose v2 for database-dependent work. Internet access is needed to download dependencies and container images. See the [environment guide](docs/environment/README.md) for platform notes and troubleshooting; Windows users should follow the [WSL guide](docs/environment/wsl-and-first-session.md) when using WSL.

```bash
# Clone if you do not already have the repository.
git clone https://github.com/exocrat/clip.git
cd clip
make setup
```

`make setup` runs `uv sync --locked` and `npm ci`; it does not start services. Contributors can install the project Git hook separately with `make install-hooks`.

## Run the web app and API

In separate terminals, from the repository root:

```bash
make start-api   # FastAPI: http://127.0.0.1:8000
```

```bash
make start-web   # Vite: http://127.0.0.1:5173
```

Open **http://127.0.0.1:5173**. Vite forwards `/api` requests to the local API. Check API liveness with `curl --fail http://127.0.0.1:8000/health`. Stop each server with Ctrl+C. The web server and a healthy API alone do not provide signed-in marketplace data: database wiring, identity, email, and image providers need the appropriate configuration. The API reads its process environment; `.env.example` is a reference, not an automatically loaded configuration file. Consult the [API settings guide](apps/api/README.md) and [identity setup](docs/environment/identity-provider-setup.md); never commit secrets.

### Local database

To use the local retained PostgreSQL database, provide a local-only password in the current shell (the wrapper accepts ASCII letters, digits, `_`, `.`, `~`, and `-`):

```bash
read -r -s -p 'Local-only PostgreSQL password: ' CLIP_LOCAL_POSTGRES_PASSWORD
printf '\n'
export CLIP_LOCAL_POSTGRES_PASSWORD
make start-db
make migrate
make migration-status
```

Reuse the initialization password when restarting an existing volume. `make stop-db` stops the database without deleting its data. Migrations include the catalogue; they do not create marketplace users or listings. This database is not automatically connected to the API by `make start-api`: see the [database guide](database/README.md) and [API guide](apps/api/README.md) for configuration and provider requirements.

### Explore with synthetic accounts

For a local walkthrough without real accounts, use the isolated inspection launcher. It requires the locked dependencies, local Docker, a built web bundle, and the local Hybrid interpreter and model at the paths documented in the [inspection command guide](docs/environment/commands.md#next-03-complete-local-inspection). It creates a disposable PostgreSQL database and synthetic users, mail, and photo storage; it does not send real mail or use AWS.

```bash
npm run build
CLIP_ENVIRONMENT=test CLIP_API_READ_REQUESTS_PER_MINUTE=100000 \
  CLIP_API_WRITE_REQUESTS_PER_MINUTE=100000 \
  .venv/bin/python scripts/marketplace_inspection.py --synthetic-inspection
```

The temporary rate-limit overrides allow the launcher's synthetic setup sweep to finish; they apply only to this process. Open **http://127.0.0.1:5174/__inspection** and choose a sample account. If that port is occupied, append `--port 5175` or `--port 5176` to the command and use the corresponding port in the URL. The launcher runs a setup/action sweep before serving; Ctrl+C cleans up its temporary database and files. The launcher binds to loopback and is for local inspection only. A normal HTTP LAN address is not a secure browser context for encrypted messaging; use localhost or a properly configured HTTPS origin for real cryptographic flows.

## Using CLIP

Once signed in with an eligible account, use Discover to browse sale listings or wanted requests, search and filter results, and open details. Save listings for later, or contact a seller from an eligible listing. Regular IISc accounts can create and manage sale listings; temporary accounts have restricted capabilities and expire after 14 days. Conversations support messages and offers; share contact information only deliberately from the conversation. Sellers control listing availability. Browser-held encryption keys cannot be restored by the server if lost.

## Checks

```bash
npm run check         # frontend lint, tests, typecheck, and build
make check            # full local CI-equivalent gates and disposable DB checks
```

`make check` requires the tools and local Docker described in the [command index](docs/environment/commands.md). Skips, missing prerequisites, and failures are not passing evidence. See [dev.md](dev.md) for focused commands, provider boundaries, and review requirements.

## Red-team testing baseline

- Baseline tag: `rt-baseline`
- Baseline commit: `acb449366b881127677740111146297c5f2cd62b`
- [View baseline code](https://github.com/exocrat/clip/tree/rt-baseline)

Report original findings against `rt-baseline`.
For retests, identify the specific fix commit or pull request tested.
