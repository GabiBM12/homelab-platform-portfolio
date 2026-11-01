#!/usr/bin/env bash
# Shared functions only. Source from a step script; never enable shell tracing.
set -euo pipefail
umask 077
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
base_state=/var/lib/homelab-terraform

select_stack() {
  stack="${1:-}"
  case "$stack" in router|control-plane|workers) ;; *) fail "Unknown stack: $stack" ;; esac
  root="$repo/terraform/environments/$stack"
  config="$root/$stack.tfvars"
  state_dir="$base_state/$stack"
  state="$state_dir/terraform.tfstate"
  state_key="homelab/$stack.tfstate"
}

selected_stacks() {
  [[ "${SELECT_ROUTER:-false}" != true ]] || printf 'router\n'
  [[ "${SELECT_CONTROL_PLANE:-false}" != true ]] || printf 'control-plane\n'
  [[ "${SELECT_WORKERS:-false}" != true ]] || printf 'workers\n'
  return 0
}

check_inputs() {
  [[ -n "$(selected_stacks)" ]] || fail "Select at least one deployment toggle."
  [[ "${DEPLOY_MODE:-}" == plan || "${DEPLOY_MODE:-}" == apply ]] || fail "Invalid deployment mode."
  [[ "${CONFIRM_NETWORK:-false}" == true ]] || fail "Confirm IP reservations, VM IDs, routing and capacity."
  [[ "${GITHUB_SHA:-}" =~ ^[a-f0-9]{40}$ && "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ && "${GITHUB_RUN_ATTEMPT:-}" =~ ^[0-9]+$ ]] || fail "Missing GitHub run identity."
  if [[ "$DEPLOY_MODE" == apply ]]; then
    [[ "${PLAN_RUN_ID:-}" =~ ^[0-9]+$ ]] || fail "Provide a successful plan run ID."
  fi
}

check_config() {
  [[ -f "$config" ]] || fail "Missing $config"
  ! grep -q REPLACE_WITH "$config" || fail "Replace public-key placeholders for $stack."
  [[ ! -e "$root/terraform.tfvars" && ! -e "$root/terraform.tfvars.json" ]] || fail "Unexpected auto-loaded terraform.tfvars."
  if compgen -G "$root/*.auto.tfvars*" >/dev/null; then fail "Unexpected auto-loaded tfvars."; fi
}

check_state() {
  # This switch is for a new deployment. Never discard/import old state implicitly.
  [[ ! -e "$base_state/terraform.tfstate" && ! -e "$base_state/initialized" && ! -e "$state" && ! -e "$state_dir/initialized" && ! -e "$root/terraform.tfstate" && ! -e "$root/errored.tfstate" ]] ||
    fail "Local/legacy or emergency state found. Stop for reviewed recovery/migration; do not delete it."
  remote_fingerprint="$(remote_state_fingerprint)"
  if [[ "$remote_fingerprint" == absent ]]; then
    [[ ! -e "$state_dir/azure-apply-started" ]] || fail "Remote state missing after an apply attempt; recover it before continuing."
    if [[ "$DEPLOY_MODE" == plan ]]; then
      [[ "${FIRST_DEPLOYMENT:-false}" == true ]] || fail "Confirm FIRST deployment for missing $stack state."
    fi
  fi
}

check_azure() {
  [[ -n "${ARM_CLIENT_ID:-}" && -n "${ARM_TENANT_ID:-}" && -n "${TF_STATE_STORAGE_ACCOUNT:-}" && -n "${TF_STATE_CONTAINER:-}" ]] || fail "Configure all four Azure repository variables."
  [[ -n "${ACTIONS_ID_TOKEN_REQUEST_URL:-}" && -n "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ]] || fail "GitHub OIDC is unavailable; deployment job needs id-token: write."
  export ARM_USE_OIDC=true ARM_USE_AZUREAD=true ARM_USE_CLI=false ARM_USE_MSI=false
  unset ARM_ACCESS_KEY ARM_SAS_TOKEN ARM_CLIENT_SECRET ARM_CLIENT_CERTIFICATE_PATH ARM_OIDC_TOKEN ARM_OIDC_TOKEN_FILE_PATH
}

remote_state_fingerprint() {
  python3 "$repo/terraform/scripts/remote-state.py" "$state_key"
}

backend_identity() {
  printf '%s\n' "$ARM_TENANT_ID/$TF_STATE_STORAGE_ACCOUNT/$TF_STATE_CONTAINER/$state_key"
}

check_saved_plan() {
  plan_dir="$state_dir/plans/$PLAN_RUN_ID"
  [[ -f "$plan_dir/ready" && -s "$plan_dir/deployment.tfplan" && ! -e "$plan_dir/apply-started" ]] || fail "$stack plan missing or already attempted; create a new plan."
  [[ "$(cat "$plan_dir/revision")" == "$GITHUB_SHA" ]] || fail "Commit changed since $stack plan; re-plan."
  [[ -f "$plan_dir/backend" && "$(cat "$plan_dir/backend")" == "$(backend_identity)" ]] || fail "Plan belongs to a different backend (or old local backend); re-plan."
  expected="$(cat "$plan_dir/state-fingerprint")"
  [[ "$(remote_state_fingerprint)" == "$expected" ]] || fail "$stack remote state changed since plan; re-plan."
}

lock_state() {
  [[ "$(uname -s)" == Linux && "$(id -u)" != 0 ]] || fail "Use the unprivileged Linux runner."
  [[ -d "$base_state" && ! -L "$base_state" && -O "$base_state" ]] || fail "Run prepare-terraform-runner.yml first."
  [[ "$(stat -c %a "$base_state")" == 700 ]] || fail "State base must have mode 0700."
  exec 9>"$base_state/deployment.lock"
  flock -n 9 || fail "Another deployment owns the state lock."
}

prepare_terraform() {
  # Each step gets fresh temporary files and releases its lock on exit.
  check_inputs
  check_azure
  selected_stacks | grep -Fxq "$stack" || fail "$stack was not selected by a deployment toggle."
  check_config
  lock_state
  [[ ! -L "$state_dir" ]] || fail "State directory cannot be a symlink."
  mkdir -p "$state_dir"
  [[ -O "$state_dir" && "$(stat -c %a "$state_dir")" == 700 ]] || fail "State directory must be owned by runner with mode 0700."
  check_state
  [[ -n "${TERRAFORM_TOKEN_ID:-}" && -n "${TERRAFORM_TOKEN_SECRET:-}" && -n "${PROXMOX_CA_PEM:-}" ]] || fail "Missing API token or Proxmox CA."
  [[ -d "${RUNNER_TEMP:-}" ]] || fail "RUNNER_TEMP is missing."
  work="$(mktemp -d "$RUNNER_TEMP/homelab-terraform.XXXXXX")"
  trap 'rm -rf -- "$work"' EXIT
  export TF_DATA_DIR="$work/tfdata" TF_IN_AUTOMATION=1 TF_INPUT=0 TF_WORKSPACE=default CHECKPOINT_DISABLE=1
  # Prevent inherited arguments/variables changing the reviewed invocation.
  for env_name in $(compgen -e); do
    case "$env_name" in TF_CLI_ARGS*|TF_VAR_*|TF_LOG*) unset "$env_name" ;; esac
  done
  export PROXMOX_VE_API_TOKEN="$TERRAFORM_TOKEN_ID=$TERRAFORM_TOKEN_SECRET"
  unset TERRAFORM_TOKEN_SECRET
  printf '%s\n' "$PROXMOX_CA_PEM" > "$work/proxmox-ca.pem"
  openssl x509 -in "$work/proxmox-ca.pem" -noout >/dev/null
  cat /etc/ssl/certs/ca-certificates.crt "$work/proxmox-ca.pem" > "$work/ca-bundle.pem"
  export SSL_CERT_FILE="$work/ca-bundle.pem"
  unset PROXMOX_CA_PEM
  terraform -chdir="$root" init -input=false -lockfile=readonly -reconfigure \
    -backend-config="storage_account_name=$TF_STATE_STORAGE_ACCOUNT" \
    -backend-config="container_name=$TF_STATE_CONTAINER" \
    -backend-config="key=$state_key"
  terraform -chdir="$root" validate
  mkdir -p "$state_dir/plans"
}
