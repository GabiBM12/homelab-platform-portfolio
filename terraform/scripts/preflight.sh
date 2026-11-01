#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
check_inputs
check_azure
for tool in terraform python3 flock openssl sha256sum; do command -v "$tool" >/dev/null || fail "Missing $tool"; done
lock_state
# Inspect ALL selections before any apply step starts, not just the first one.
while IFS= read -r name; do
  select_stack "$name"
  check_config
  [[ ! -L "$state_dir" ]] || fail "State directory cannot be a symlink."
  check_state
  if [[ "$DEPLOY_MODE" == apply ]]; then check_saved_plan; fi
  printf 'Preflight passed: %s\n' "$stack"
done < <(selected_stacks)
