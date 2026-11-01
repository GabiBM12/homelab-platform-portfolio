# Router deployment

This independent Terraform root clones Ubuntu template 9000 into router01.
It reuses the VM module but has its own state and `routers` Ansible inventory.
It does not install router software or enable packet forwarding.

Review `router.tfvars`: replace both PUBLIC key placeholders, reserve VM ID 200
and proposed home-LAN IP 192.168.0.200, and check for subnet overlap with VPNs,
home networks and future Kubernetes Pod/Service CIDRs. Confirm DNS at 192.168.0.1.
Both vmbr0 and the active portless vmbr10 must exist on pve.

NIC 0 is WAN/home LAN (vmbr0); NIC 1 is lab LAN (vmbr10, 10.20.10.1/24).
Only WAN has a default gateway. Do not assume guest interface names: discover
them before writing Ansible firewall/routing configuration.

## Deployment order

1. Commit reviewed settings and provider lock files to private main.
2. Run **Deploy homelab VMs**, toggle **deploy_router**, mode **plan**. Confirm first
   deployment only if this stack has never been deployed and has no state.
3. Review the plan, then run **apply**, toggle **deploy_router**, supplying that plan's
   run ID at the same main commit. Existing state/confirmation safeguards apply.
4. Run a separate router Ansible playbook (not implemented here), connecting
   from management to the router's home-LAN IP. Configure persistent IPv4
   forwarding, a default-deny forwarding firewall, established/related return
   traffic, approved management-to-lab access, and lab-to-WAN masquerading.
   Permit necessary outbound DNS, NTP, package and container registry access.
   Keep SSH restricted to approved administration/management source addresses.
5. Add a persistent route on management and any administration laptop that
   needs direct lab access: 10.20.10.0/24 via the reserved router WAN address.
   Do not expose SSH or Proxmox through internet port forwarding.
6. Run the workflow with **deploy_control_plane** and/or **deploy_workers**,
   plan then reviewed apply. Their
   tfvars attach all three nodes to vmbr10 with gateway 10.20.10.1.
7. Verify reachability, DNS and outbound access before separate Kubernetes
   Ansible configuration. Terraform output is not proof of guest health.

Router state is stored in Azure at homelab/router.tfstate. Saved plans and
inventory remain under /var/lib/homelab-terraform/router/. See the
[pipeline guide](../../scripts/README.md) for OIDC variables and recovery.
All stacks share the local runner lock and use Azure backend locking.
No local state migration is automatic; stop if legacy state is detected.

The workflow's Terraform token creates VMs through the API; it does not need
SSH private keys. Later Ansible jobs fetch the matching private keys from
GitHub Secrets and use the separate inventories. Never put private keys in tfvars.

This setup is single-host networking: a portless vmbr10 on another host does
not connect to this LAN. Cross-host placement needs a VLAN/physical network
design first. Router shutdown will interrupt lab routing; it is not HA.
