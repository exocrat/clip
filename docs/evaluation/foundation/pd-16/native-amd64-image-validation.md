# Native AMD64 API-image validation

**Observed:** 2026-10-19 15:37:20 UTC · **Contributor:** Suraj (B).

## Source and artifact

| Field | Observed result |
|---|---|
| Source | `68d6179db03dcf983278b290d22a939af625bba1`, branch `task/pr7-review-fixes`; clean before build and after validation. This is the local, human-verified PR #7 correction commit, not a published or merged revision. |
| Engine | Native Linux x86_64, Docker client/server 29.1.3. No emulation or Buildx plugin. |
| Context | Only tracked `pyproject.toml`, `uv.lock`, API application source, Dockerfile and its ignore file, extracted from that exact Git commit. 110.1 kB sent to the daemon. No credentials, dotenv files, Git metadata, untracked bytecode, virtual environments or datasets. |
| Build | Exit 0 after 35.47 seconds; Python `3.14.8-slim-trixie`, uv `0.10.7`, unchanged source/lock/pins. |
| Local tag | `clip-api:pd16-amd64-68d6179db03d` |
| Local image ID | `sha256:8f07c52fdfd5a15c29eedae5b7189e6923e5ab0c622459568f70f6d7581a2bed` |
| Platform | `linux/amd64`; runtime Python reported machine `x86_64`. |
| Runtime | Python 3.14.8; configured user `10001:10001`, observed UID 10001. |
| Local image size | 49,478,035 bytes as reported by `docker image inspect`; not registry compressed storage or a cost measurement. |
| HTTP | `http://127.0.0.1:8000/health` returned HTTP 200 and exactly `{"status":"ok"}`. |
| Docker health | `healthy` using the Dockerfile's own health check. |
| Cleanup | Owned smoke container removed with exit 0; temporary context/archive removed. No running test container remains. Validated image deliberately retained locally for handoff. |

This validates the native AMD64 image and process health. It does not independently establish why historical emulated builds failed, or accept macOS/whole-lifecycle checks, private RDS/ECS/SSM integration, ECR upload, NFRs, PD-16 completion or PRE-00. Suraj subsequently verified the build result and approved the named local evidence commit (recorded 2026-10-19 15:41:43 UTC). Publication and subsequent hosted/independent peer review remain pending. The user selected Git pushes only at the end.

## Commands and provenance

The session-local helper was `python3 /tmp/clip-pr7-tools/build-amd64-api.py`. Its temporary location is not a durable tool prerequisite. The exact invocation, results, context inventory and safe logs are preserved below; the following commands describe what ran, not approval to repeat it against another target.

Recorded `git rev-parse HEAD`, `git status --porcelain=v1`, `docker info --format '{{.OSType}}/{{.Architecture}}'` and Docker client/server versions. The Git status was empty. Created the restricted context with:

```sh
git archive 68d6179db03dcf983278b290d22a939af625bba1 pyproject.toml uv.lock apps/api/app apps/api/Dockerfile apps/api/Dockerfile.dockerignore
```

The archive was written outside the context and extracted with `tar -xf <source.tar> -C <context>`. Its SHA-256 was `cbcea5c983a451dda28c40e2408f26537b476bd44982d5fe2cc35a464e879933`. Docker build ran with only the normal local PATH/HOME and the explicit legacy-builder selection:

```sh
DOCKER_BUILDKIT=0 docker build --platform linux/amd64 --file /tmp/clip-api-amd64-68d6179-db77y3b1/context/apps/api/Dockerfile --tag clip-api:pd16-amd64-68d6179db03d /tmp/clip-api-amd64-68d6179-db77y3b1/context
```

Inspected the image platform, ID, user and size with `docker image inspect`. Executed Python in a separate `docker run --rm --network none --entrypoint python` invocation to confirm native architecture, Python version and UID. Created the smoke container with `docker create --publish 127.0.0.1:8000:8000 clip-api:pd16-amd64-68d6179db03d`, started it, and checked HTTP through Python's standard-library HTTP client. Polled `docker inspect --format '{{.State.Health.Status}}' <owned-container-id>` until healthy. Saved its logs and removed that exact owned container with `docker rm --force <owned-container-id>`; the full ID and cleanup status are in the result manifest. The image was retained and no registry push occurred.

## Preserved evidence

- [Result manifest](amd64-68d6179/result.json), SHA-256 `8fecb3a720e5e30b56fb68598bfb026337de83ad6d3bc31d2eaae31aa02f4be1`.
- [Raw build output](amd64-68d6179/build.log), SHA-256 `8af085b6711aa3138ebf94d167272363eac2c011c50337ee2ad5376975539587`. ANSI/progress whitespace is preserved; the exact log path has a Git whitespace-check exception.
- [Context file inventory](amd64-68d6179/context-files.json), SHA-256 `d6a0e564bb520b654c6db098b691e550def657be5600c119ab1da853df048ca9`.
- [Smoke container output](amd64-68d6179/container.log), containing health-only process/request metadata.

Original session copies remain under `/tmp/clip-api-amd64-68d6179-db77y3b1/`; continued availability is not assumed. The copied evidence remains in the local worktree until its separately approved commit. A local image ID or local RepoDigests entry is not verified ECR publication evidence: before any later upload, agree the exact account/Region/repository/tag and publishable manifest digest, obtain authorization, then verify the remote digest.
