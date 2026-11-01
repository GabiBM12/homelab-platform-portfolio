#!/usr/bin/env bash
# Compatibility entry point; GitHub now calls explicit preflight/plan/apply steps.
set -euo pipefail
case "${DEPLOY_STACK:-}" in
  router|control-plane|workers) ;;
  *) printf 'Choose DEPLOY_STACK=router, control-plane, or workers. The combined kubernetes stack is retired.\n' >&2; exit 1 ;;
esac
export SELECT_ROUTER=false SELECT_CONTROL_PLANE=false SELECT_WORKERS=false
case "$DEPLOY_STACK" in
  router) export SELECT_ROUTER=true ;;
  control-plane) export SELECT_CONTROL_PLANE=true ;;
  workers) export SELECT_WORKERS=true ;;
esac
bash "$(dirname "$0")/preflight.sh"
case "${DEPLOY_MODE:-}" in
  plan|apply) exec bash "$(dirname "$0")/$DEPLOY_MODE.sh" "$DEPLOY_STACK" ;;
  *) exit 1 ;;
esac
