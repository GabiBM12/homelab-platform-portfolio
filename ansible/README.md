# Homelab host automation

## Guest networking

Router implementation: [router networking runbook](../docs/operations/router-networking.md).
Run playbooks/router/configure.yml using .github/workflows/router-network.yml.
The router_network role configures persistent forwarding, nftables, and NAT.
Inventory now contains routers and Kubernetes control-plane/worker groups.
See playbooks/kubernetes/README.md for the node preparation/install boundary;
those executable playbooks are deliberately not implemented yet.

Use this Ansible project for API-based Proxmox host configuration and, later,
guest VM and K3s configuration. Keep management preparation and recovery
in [the management bootstrap project](../bootstrap/management/README.md), run
from the administration laptop.

## Execution and credentials

Run host API playbooks on management, manually or through the private repository's
self-hosted runner. Ansible executes locally and calls the Proxmox HTTPS API;
API tasks do not need Proxmox SSH credentials or sudo.

Create pipeline identities and store tokens manually using the
[identity prerequisites](../docs/operations/proxmox-identity-bootstrap.md).
The superseded identity automation and unused standalone SSH diagnostic were
removed. Neither is a prerequisite for Packer, Terraform or host networking.

Read the [API configuration guide](../docs/operations/proxmox-host-configuration.md)
for permissions, ownership and safe network activation. The vmbr10 implementation
belongs to the separate networking feature, not this checkout. Run only
playbooks actually present on the branch being reviewed.

The Proxmox SSH entry remains an example, not a verified target. Guest entries
reflect the current single-host router and three-node lab. Verify before applying.
Do not store private keys, API token secrets or sudo passwords there.
An API play using localhost does not require a Proxmox SSH inventory entry.

## Configuration ownership

- Proxmox host automation creates bridges while preserving management networking.
- Terraform creates VMs and attaches their NICs to existing bridges.
- Cloud-init supplies initial guest addressing and access.
- Ansible manages ongoing guest configuration, router services and K3s.

Management preparation playbooks remain separate from pipeline execution.
Future workload and K3s playbooks should be added when implemented,
not as empty entry points. API workflows must inspect pending changes and
require console recovery access before applying node-network changes.
