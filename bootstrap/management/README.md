# Management bootstrap

Ansible configuration for the Ubuntu management laptop that will host the
private repository's self-hosted GitHub Actions runner.

Run this project from the administration laptop over LAN SSH, both for initial
bootstrap and later management changes. Do not depend on the management runner
to configure or repair itself.

## Start here

- [Management bootstrap runbook](../../docs/operations/management-bootstrap.md):
  prerequisites, inventory, commands, runner registration, verification, recovery.
- [Overall bootstrap sequence](../../docs/operations/bootstrap.md).
- [Why administration-led bootstrap?](../../docs/adr/005-bootstrap-management-from-administration-laptop.md)
- [Documentation wiki](../../docs/README.md).

## Project layout

- `ansible/ansible.cfg`: inventory and role discovery; run from this directory.
- `ansible/inventory/bootstrap/`: host identities and group variables.
- `ansible/playbooks/bootstrap-management.yml`: common hardening and tools.
- `ansible/playbooks/register-github-runner.yml`: separate runner registration.
- `ansible/playbooks/verify-management.yml`: post-registration checks.
- `ansible/roles/`: reusable implementation tasks.

Replace placeholders and establish SSH-key access before running. The bootstrap
restricts incoming SSH and disables password/root authentication; keep console
recovery access. No VPN, public port forwarding, or management deployment
pipeline is required. The runbook is the authoritative procedure.

