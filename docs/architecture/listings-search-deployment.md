# Listings and Search deployment handoff

This is the merge-plan Step 7 handoff. The combined application uses the same
PostgreSQL database and existing API process for Listings, Search, Wanted and
Saved. The local walkthrough exercised real Listings/Search behavior with
synthetic Identity. Cloud testing belongs to the later integrated deployment.

## Connections already implemented

| Connection | Normal application behavior |
|---|---|
| Listings → Search | `app.main` constructs `ListingsSearchAccess` on the command pool and injects it into Wanted/draft/Saved route dependencies. All five public operations are real. |
| Listings create/edit → Hybrid | Database triggers queue/invalidate generations for building/serving pipelines. The enabled durable dispatcher publishes real vectors; Hybrid checks their current source version. |
| Images → Discover/Saved/detail | The same Listings image-delivery component requests authorized S3 URLs. Only the local browser harness substitutes temporary local storage. |
| Website → API | With `CLIP_SERVE_WEB_APP=true`, the ordinary image serves the built website and `/api` routes together. This setting does not activate a test caller. The Vite development proxy remains a local alternative. |
| Wanted/Saved persistence | Search's stores use the same configured database pool; there is no separate Search database, HTTP bridge or data-copy job. |

## Image builds

The ordinary API Dockerfile remains the Keyword-only image. The optional
`apps/api/Dockerfile.hybrid` extends a freshly built API image with the existing
offline CPU helper, its frozen Linux AMD64 wheels, pinned model artifacts and
the pipeline operator command. It leaves the isolated LI-02 image build and
Terraform configuration unchanged.

Build from the repository root on Linux AMD64. The three named artifact contexts
must contain the reviewed CPython 3.13.12 standalone distribution, the wheels
selected by `scripts/evaluation/semantic/requirements-linux-x86_64.txt`, and the
model artifacts pinned by `embedding_pipeline.json`. The local combined demo
already prepared these under ignored `.tools/semantic/`; these directories are
build inputs, not committed files. Do not point a context at an entire home,
credential or project directory.

```sh
docker build --platform linux/amd64 -f apps/api/Dockerfile -t clip-api:local .
docker build --platform linux/amd64 -f apps/api/Dockerfile.hybrid \
  --build-arg API_IMAGE=clip-api:local \
  --build-context semantic-python=.tools/semantic/python/cpython-3.13.12-linux-x86_64-gnu \
  --build-context semantic-wheels=.tools/semantic/wheels \
  --build-context semantic-model=.tools/semantic/model \
  -t clip-api:hybrid-local .
```

The helper installation and inference build steps have networking disabled.
The build checks interpreter version, all wheel hashes, exact model/tokenizer
hashes and runtime pins, and executes real 384-dimensional inference as the
non-root runtime user. Runtime startup downloads nothing. This image currently
supports Linux AMD64; another architecture needs its own compatible wheel set.

For a fresh Linux build machine, install CPython 3.13.12 with the repository's
pinned uv into `.tools/semantic/python` (`UV_PYTHON_INSTALL_DIR`), and download
the exact lock's binary wheels into `.tools/semantic/wheels`. A pinned
`python:3.14.8-slim-trixie` container's `python -m pip download --require-hashes
--only-binary :all: --no-deps` can prepare the wheel directory, using
`--python-version 3.13 --implementation cp --abi cp313 --abi abi3 --abi none`
and Linux x86_64 platforms `manylinux_2_28_x86_64`, `manylinux_2_27_x86_64`,
`manylinux_2_17_x86_64` and `manylinux2014_x86_64`. The last explicit platform
is required by the pinned protobuf binary wheel; omitting it can select a
different universal wheel whose hash is correctly rejected by this lock.
Retrieve `onnx/model.onnx` and `tokenizer.json` from the
immutable model/revision in `embedding_pipeline.json`; the build refuses changed
bytes. Existing [semantic artifact documentation](../../scripts/evaluation/semantic/README.md)
explains provenance and the earlier Mac probe. That Mac-specific fetch script
does not prepare the Linux wheel set.

On the Arch workstation, use pip from the already present standalone Python;
keep the helper's Python 3.13 virtual environment separate from the API's Python
3.14 environment. With public-PyPI artifact downloads explicitly authorized:

```sh
.tools/semantic/python/cpython-3.13.12-linux-x86_64-gnu/bin/python3.13 -m pip \
  --isolated --disable-pip-version-check download \
  --index-url https://pypi.org/simple --require-hashes --only-binary :all: --no-deps \
  --python-version 3.13 --implementation cp --abi cp313 --abi abi3 --abi none \
  --platform manylinux_2_28_x86_64 --platform manylinux_2_27_x86_64 \
  --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 \
  --dest .tools/semantic/wheels --no-cache-dir --timeout 20 --retries 0 --no-input \
  -r scripts/evaluation/semantic/requirements-linux-x86_64.txt
```

This downloads binary archives for the build without changing a venv or system
packages. The EXP-03 local check downloaded 24 matching archives and installed
them with pip into a disposable Python 3.13 venv using `--no-index`, required
hashes and these local files; `pip check` passed. It does not establish image
startup, model inference or ECS/Lambda integration. Existing installed packages
alone do not substitute for the wheel context used by the image build.

## Configuration and initial pipeline setup

The deployment supplies the existing `CLIP_DATABASE_URL` secret and S3 bucket,
region, prefix and IAM role for Listings images. It can set
`CLIP_SERVE_WEB_APP=true` with production authentication. Keep development auth
and `CLIP_ISOLATED_LISTINGS_TEST_CALLER` disabled in the integrated deployment.
The optional Hybrid image sets both Hybrid read/worker flags and its absolute
interpreter/model paths. It requires a database URL; the ordinary image keeps
Hybrid disabled unless a complete runtime is supplied explicitly.

Run normal migrations first. Then use the packaged
`python scripts/search_pipeline.py` as a separately invoked deployment job:
`prepare`, bounded `queue` batches, worker processing, `status`, then `activate`
only after complete coverage. Each invocation requires the exact expected
host/port/database/role and pinned pipeline ID; mutations require `--execute`.
The pipeline ID is
`4b43fc307151933bf5b0fa80ff4e10f8cb4266194905cd2b15a3d01b2386d9ca`.
Use the approved database secret through the process environment, never the
command line. See [the bootstrap procedure](semantic-pipeline-bootstrap.md).
These operations can be deployment automation steps; normal API startup does
not silently modify pipeline state. After activation, ordinary new listings
and edits queue their vectors automatically. A brief indexing gap returns 503
for Hybrid; Keyword remains available.

Each API process uses at most 10 command connections, 2 Hybrid read connections
and 1 worker connection. It runs one serial model helper shared by query and
worker requests. Start with one API process; size the later ECS task and database
connection budget against the integrated workload. Existing 512 MiB foundation
or isolated-demo task settings are not a measured final sizing result. `/health`
is liveness; deployment verification also needs authenticated create/search and
pipeline coverage checks. Build/inference checks here are local, not cloud NFRs.

## Connections owned by the next domain integrations

Identity supplies server-authenticated `clip.caller`, `GET /me`, and the existing
public eligibility operation used by Listings and Search. Conversations supplies
the reviewed sale/wanted thread, exact-pair lookup, offer, activity and retirement
operations already called through its public boundary. Those implementations
remain the respective domains' work. No Search/Listings database or deployment
redesign is needed to bind them. Once they arrive, repeat regular/temporary/
expired/revoked and participant/privacy checks on the actual implementations.

The current shared foundation Terraform is a foundation service definition,
not an integrated app release: it will need the approved release image, database
secret, S3 role/settings, routing/TLS and measured task resources when that
deployment is selected. Reuse those shared resources. Do not deploy the isolated
LI-02 identity profile as the integrated marketplace.
