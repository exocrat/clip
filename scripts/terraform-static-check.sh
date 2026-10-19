#!/usr/bin/env bash
# Bash 3.2+ local formatting/provider-schema checks. Never plan/apply, initialize
# a backend or inherit Terraform CLI flags/provider credentials from the shell.
set -euo pipefail
set +x

usage() {
  printf '%s\n' 'Usage: bash scripts/terraform-static-check.sh [format|check-format|validate|check]' \
    'Default: check. Terraform version must match .terraform-version.'
}
[[ $# -le 1 ]] || { usage >&2; exit 2; }
action=${1:-check}
case "$action" in
  -h|--help) usage; exit 0 ;;
  format|check-format|validate|check) ;;
  *) usage >&2; exit 2 ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
terraform_bin="${TERRAFORM_BIN:-terraform}"
expected_version="$(tr -d '\r\n' < "${repo_root}/.terraform-version")"

# Keep public-registry downloads available, but discard ambient TF_CLI_ARGS,
# cloud environment credentials, logging/debug flags and user Terraform config.
local_terraform() {
  env -i PATH="$PATH" HOME="$HOME" TF_CLI_CONFIG_FILE=/dev/null \
    TF_IN_AUTOMATION=1 CHECKPOINT_DISABLE=1 "$terraform_bin" "$@"
}
actual_version="$(local_terraform version | sed -n '1s/^Terraform v//p')"
if [[ "${actual_version}" != "${expected_version}" ]]; then
  printf 'Expected Terraform %s, found %s.\n' "${expected_version}" "${actual_version:-unknown}" >&2
  exit 1
fi
printf 'Local Terraform %s action=%s target=infra/terraform (no backend/cloud operation)\n' "$expected_version" "$action"

case "$action" in
  format) local_terraform -chdir="$repo_root" fmt -recursive infra/terraform; exit 0 ;;
  check-format|check) local_terraform -chdir="$repo_root" fmt -check -recursive infra/terraform ;;
esac
[[ "$action" != check-format ]] || exit 0

infra_root="${repo_root}/infra/terraform"
# A parent-shell read loop works on macOS Bash 3.2 and preserves failing status;
# mapfile requires Bash 4. Root paths containing newlines are unsupported.
config_dirs=$(find "$infra_root" -type f -name '*.tf' -exec dirname {} \; | sort -u)
[[ -n "$config_dirs" ]] || { printf '%s\n' 'No Terraform configurations found.' >&2; exit 1; }
while IFS= read -r config_dir; do
  printf 'Backend-free initialization and validation: %s\n' "${config_dir#"${repo_root}/"}"
  local_terraform -chdir="$config_dir" init -backend=false -input=false -no-color -lockfile=readonly
  local_terraform -chdir="$config_dir" validate -no-color
done <<< "$config_dirs"
