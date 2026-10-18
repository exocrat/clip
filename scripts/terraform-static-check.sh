#!/usr/bin/env bash

# Run Terraform formatting and backend-free validation for every root
# configuration, without reading remote state or invoking cloud operations.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
terraform_bin="${TERRAFORM_BIN:-terraform}"
expected_version="$(tr -d '\r\n' < "${repo_root}/.terraform-version")"
actual_version="$("${terraform_bin}" version | sed -n '1s/^Terraform v//p')"

if [[ "${actual_version}" != "${expected_version}" ]]; then
  printf 'Expected Terraform %s, found %s.\n' "${expected_version}" "${actual_version:-unknown}" >&2
  exit 1
fi

infra_root="${repo_root}/infra/terraform"
"${terraform_bin}" -chdir="${repo_root}" fmt -check -recursive infra/terraform

mapfile -t config_dirs < <(find "${infra_root}" -type f -name '*.tf' -exec dirname {} \; | sort -u)
if ((${#config_dirs[@]} == 0)); then
  printf 'No Terraform root configurations found under %s.\n' "${infra_root}" >&2
  exit 1
fi

for config_dir in "${config_dirs[@]}"; do
  printf 'Backend-free initialization and validation: %s\n' "${config_dir#"${repo_root}/"}"
  "${terraform_bin}" -chdir="${config_dir}" init -backend=false -input=false -no-color
  "${terraform_bin}" -chdir="${config_dir}" validate -no-color
done
