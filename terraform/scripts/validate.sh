#!/usr/bin/env bash
# CI-only: no Proxmox credentials, backend access, or live resource operations.
source "$(dirname "$0")/common.sh"
command -v terraform >/dev/null || fail "Terraform is required."
work="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/homelab-validate.XXXXXX")"
trap 'rm -rf -- "$work"' EXIT
export TF_IN_AUTOMATION=1 TF_INPUT=0 TF_WORKSPACE=default CHECKPOINT_DISABLE=1
unset PROXMOX_VE_API_TOKEN PROXMOX_VE_USERNAME PROXMOX_VE_PASSWORD
for env_name in $(compgen -e); do
  case "$env_name" in TF_CLI_ARGS*|TF_VAR_*|TF_LOG*) unset "$env_name" ;; esac
done
terraform fmt -check -recursive "$repo/terraform"
for name in router control-plane workers; do
  select_stack "$name"
  export TF_DATA_DIR="$work/$name"
  terraform -chdir="$root" init -backend=false -input=false -lockfile=readonly
  terraform -chdir="$root" validate
  terraform -chdir="$root" test
done
