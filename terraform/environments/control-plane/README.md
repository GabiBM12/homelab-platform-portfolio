# Control-plane VM stack

Edit `control-plane.tfvars` (public keys only). All entries must have role
`control_plane`. Add a stable map entry with a unique VM ID/IP to add a node;
retain existing entries. Select only `deploy_control_plane` to limit deployment
to this state. Unchecking the toggle skips it; it does not delete its VMs.

State is stored in Azure at homelab/control-plane.tfstate. Saved plans and Ansible
inventory remain under `/var/lib/homelab-terraform/control-plane/`. The inventory group is
`k3s_server`. Terraform creates Ubuntu VMs, not K3s membership.
Ansible must configure/join new control planes separately.

See [pipeline steps and migration safeguards](../../scripts/README.md).
Never run this against existing combined-state VMs without state migration.
