#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
[[ "${DEPLOY_MODE:-}" == apply ]] || fail "apply.sh requires mode=apply."
select_stack "${1:-}"
prepare_terraform
# Recheck under lock; preflight happened in an earlier step.
check_saved_plan
terraform -chdir="$root" show -json "$plan_dir/deployment.tfplan" > "$work/plan.json"
python3 "$repo/terraform/scripts/check-plan.py" "$work/plan.json"
touch "$plan_dir/apply-started" "$state_dir/azure-apply-started"
terraform -chdir="$root" apply -input=false -lock-timeout=60s "$plan_dir/deployment.tfplan"
terraform -chdir="$root" output -json ansible_inventory > "$state_dir/inventory.local.yml"
printf '### %s applied\n\nInventory: `%s/inventory.local.yml`. Ansible guest configuration is separate.\n' "$stack" "$state_dir" >> "$GITHUB_STEP_SUMMARY"
