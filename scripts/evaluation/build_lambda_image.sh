#!/usr/bin/env bash
# Build the pinned EXP-03 Lambda container from already cached local images.
# This script only builds a local Docker image; it never pulls, runs or pushes.
set -euo pipefail

adapter_image="public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0"
adapter_digest="sha256:17cfd08eff1dfea3f6a9a1e9c65fdac80aa4919b6085e746615530f43f57d2f1"

usage() {
  printf 'Usage: %s clip-exp03-hybrid:local-<revision> clip-exp03-lambda:local-<same-revision>\n' "$0" >&2
}

if [[ ${1:-} == --help ]]; then
  usage
  exit 0
fi

if [[ $# -ne 2 ]]; then
  usage
  exit 2
fi

api_image=$1
lambda_tag=$2
if [[ ! $api_image =~ ^clip-exp03-hybrid:local-([0-9a-f]{7,40})$ ]]; then
  printf 'Expected a commit-tagged local Hybrid API image.\n' >&2
  exit 2
fi
source_revision=${BASH_REMATCH[1]}
if [[ $lambda_tag != "clip-exp03-lambda:local-$source_revision" ]]; then
  printf 'Output tag must use the same source revision as the API image.\n' >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  printf 'Docker CLI is required.\n' >&2
  exit 2
fi

# Force Docker's configured default context and refuse non-local endpoints.
# This prevents an active SSH/TCP Docker context from receiving the build.
engine_endpoint=$(docker context inspect default --format '{{ (index .Endpoints "docker").Host }}')
if [[ $engine_endpoint != unix://* ]]; then
  printf 'The default Docker context must use a local Unix socket.\n' >&2
  exit 2
fi

if ! api_platform=$(
  docker --context default image inspect \
    --format '{{.Os}}/{{.Architecture}}' "$api_image" 2>/dev/null
); then
  printf 'Required local Hybrid API image is missing.\n' >&2
  exit 2
fi
if [[ $api_platform != linux/amd64 ]]; then
  printf 'The local Hybrid API image must be linux/amd64.\n' >&2
  exit 2
fi
# A tag can be moved to another image. Require a full, matching revision label
# as an additional declaration; this does not authenticate the image contents.
api_revision=$(docker --context default image inspect \
  --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$api_image")
if [[ ! $api_revision =~ ^[0-9a-f]{40}$ || $api_revision != "$source_revision"* ]]; then
  printf 'Hybrid image needs a matching full OCI revision label.\n' >&2
  exit 2
fi
if ! adapter_platform=$(
  docker --context default image inspect \
    --format '{{.Os}}/{{.Architecture}}' \
    "$adapter_image@$adapter_digest" 2>/dev/null
); then
  printf 'Required pinned Lambda Web Adapter image is not cached locally.\n' >&2
  exit 2
fi
if [[ $adapter_platform != linux/amd64 ]]; then
  printf 'The cached Lambda Web Adapter image must be linux/amd64.\n' >&2
  exit 2
fi
if docker --context default image inspect "$lambda_tag" >/dev/null 2>&1; then
  printf 'Refusing to replace an existing local image tag.\n' >&2
  exit 2
fi

# Both FROM images must already be present. Disable registry pulls and RUN
# networking so the build remains local and reproducible from these inputs.
# Dockerfile.lambda uses COPY --chmod, which requires BuildKit.
DOCKER_BUILDKIT=1 docker --context default build \
  --pull=false \
  --network=none \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  --file apps/api/Dockerfile.lambda \
  --build-arg "API_IMAGE=$api_image" \
  --build-arg "LWA_IMAGE=$adapter_image" \
  --build-arg "LWA_DIGEST=${adapter_digest#sha256:}" \
  --label "org.opencontainers.image.revision=$api_revision" \
  --tag "$lambda_tag" \
  apps/api

docker --context default image inspect \
  --format '{{.Id}} {{.Os}}/{{.Architecture}} {{.Size}}' \
  "$lambda_tag"
