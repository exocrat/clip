#!/bin/bash
# Operator-only build on one approved disposable x86_64 host. No AWS API or push.
# SSM/source transfer must finish first; source is an allowlisted git archive.
set -euo pipefail
umask 077
[[ $# == 3 ]] || exit 2
run_dir=$1
source_sha=$2
revision=$3
[[ $run_dir =~ ^/var/tmp/clip-id01-build-[0-9a-f]{12}$ ]] || exit 2
[[ $source_sha =~ ^[0-9a-f]{64}$ && $revision =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ $run_dir == "/var/tmp/clip-id01-build-${revision:0:12}" ]] || exit 2
[[ $(uname -m) == x86_64 && $EUID == 0 ]] || exit 2
[[ -d $run_dir && ! -L $run_dir && -f $run_dir/source.tar ]] || exit 2
[[ ! -e $run_dir/context && ! -e $run_dir/result.json ]] || exit 2
[[ $(df --output=avail -B1 "$run_dir" | tail -1) -ge 10737418240 ]] || exit 2
[[ $(wc -l < /proc/swaps) -eq 1 ]] || exit 2
printf '%s  %s\n' "$source_sha" "$run_dir/source.tar" | sha256sum --check --status

# Reject traversal, symlinks/devices, unexpected context roots and oversized input
# before extraction. Python is the host stdlib, not the application's interpreter.
python3 - "$run_dir" <<'PY'
from pathlib import Path, PurePosixPath
import sys, tarfile
root = Path(sys.argv[1])
allowed = ('apps/api/app/', 'apps/web/', 'contracts/generated/')
exact = {'pyproject.toml', 'uv.lock', 'package.json', 'package-lock.json',
         'apps/api/Dockerfile', 'apps/api/Dockerfile.dockerignore'}
with tarfile.open(root / 'source.tar') as archive:
    members = archive.getmembers()
    assert sum(m.size for m in members) <= 100 * 1024 * 1024
    for member in members:
        name = PurePosixPath(member.name)
        assert not name.is_absolute() and '..' not in name.parts
        assert member.isdir() or member.isfile()
        if member.isfile():
            assert member.name in exact or member.name.startswith(allowed)
    (root / 'context').mkdir(mode=0o700)
    archive.extractall(root / 'context', members=members)
PY

image="clip-api:id01-${revision:0:12}"
container="clip-id01-build-${revision:0:12}"
swap_file="$run_dir/build.swap"
# Remove only this owned smoke container and swap; final host termination is the
# fallback if swapoff or a daemon-side build cannot be cancelled safely.
cleanup() {
  docker rm --force "$container" >/dev/null 2>&1 || true
  if [[ -f $swap_file ]]; then
    if swapoff "$swap_file"; then rm -f "$swap_file"; fi
  fi
}
! docker image inspect "$image" >/dev/null 2>&1 || exit 2
! docker container inspect "$container" >/dev/null 2>&1 || exit 2
[[ ! -e $swap_file ]] || exit 2
trap cleanup EXIT
fallocate -l 2G "$swap_file"
chmod 0600 "$swap_file"
mkswap "$swap_file" >/dev/null
swapon "$swap_file"
# Legacy Docker25 builds execute stages sequentially. A failed/OOM build is a
# failed trial; never increase the host class or bypass limits automatically.
timeout --signal=TERM --kill-after=30s 2700s env DOCKER_BUILDKIT=0 \
  docker build --platform linux/amd64 --memory=512m --memory-swap=1536m \
  --rm --force-rm --build-arg VITE_LISTINGS_PUBLIC_DEMO=false \
  --build-arg VITE_MICROSOFT_SIGN_IN_ENABLED=true \
  --file "$run_dir/context/apps/api/Dockerfile" --tag "$image" "$run_dir/context"
docker run --rm --network none --memory=256m --memory-swap=256m \
  --entrypoint python "$image" -c \
  'import os,platform; assert os.getuid()==10001 and platform.machine()=="x86_64"'
docker run --detach --name "$container" --memory=512m --memory-swap=512m \
  --publish 127.0.0.1:18080:8000 "$image" >/dev/null
# Validate health and bundled UI without Identity activation or real credentials.
python3 - "$container" <<'PY'
import json, subprocess, sys, time, urllib.request
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen('http://127.0.0.1:18080/health', timeout=2) as r:
            assert json.load(r) == {'status': 'ok'}
        with urllib.request.urlopen('http://127.0.0.1:18080/', timeout=2) as r:
            assert r.status == 200 and b'<html' in r.read(1024).lower()
        state = json.loads(subprocess.check_output(['docker','inspect',sys.argv[1]]))[0]['State']
        assert not state['OOMKilled']
        if state['Health']['Status'] == 'healthy': break
    except (OSError, AssertionError):
        pass
    time.sleep(2)
else:
    raise SystemExit('Bounded image health/UI check failed')
PY
docker rm --force "$container" >/dev/null
docker save --output "$run_dir/image.part" "$image"
mv "$run_dir/image.part" "$run_dir/image.tar"
# Write completion marker last so the private transfer cannot expose partial data.
python3 - "$run_dir" "$image" "$revision" "$source_sha" <<'PY'
from pathlib import Path
import hashlib, json, subprocess, sys
root, image, revision, source = Path(sys.argv[1]), *sys.argv[2:]
info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', image]))[0]
assert info['Architecture']=='amd64' and info['Os']=='linux' and info['Config']['User']=='10001:10001'
digest = hashlib.sha256()
with (root / 'image.tar').open('rb') as f:
    for chunk in iter(lambda: f.read(1024*1024), b''): digest.update(chunk)
result = dict(source_commit=revision,source_archive_sha256=source,image_id=info['Id'],
              image_tag=image,architecture='amd64',os='linux',user=info['Config']['User'],
              image_size_bytes=info['Size'],archive_sha256=digest.hexdigest(),
              health_and_ui=True,identity_runtime_tested=False,registry_published=False)
(root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
PY
