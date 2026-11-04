# Proxmox Ubuntu VM module

Creates one full clone through the Proxmox API using bpg/proxmox 0.118.0.
The root supplies the provider. No SSH provisioner, private-key generation,
custom cloud-init snippet upload, or host SSH configuration is used.

Inputs: stable hostname, typed node object (role, IDs, source/target nodes,
CPU/RAM/disk, static IPv4/gateway, storage and bridge), administrator name,
public SSH keys and DNS servers. See variables.tf for the complete contract.
Output vm contains its ID, role, desired address, administrator and placement.

Router guests use role `router` and ordered `additional_networks` for LAN NICs.
Each additional NIC has a matching cloud-init IP configuration, with no extra
default gateway. The primary NIC remains first. Terraform does not enable
forwarding or configure a guest firewall; those belong to router Ansible.

Assumptions match the current Packer image: a >=32 GiB scsi0 disk, SeaBIOS
inherited from the template, cloud-init drive on ide2, working guest agent,
and a clean cloud-init state. Both hosts must support x86-64-v2-AES before
using this CPU model. Full clones avoid linked-clone runtime dependencies.

prevent_destroy blocks replacements/deletions while the resource configuration
remains present. It does not protect against UI/API deletion or removal of the
entire module/resource configuration. Review every plan; do not bypass this
guard to perform routine K3s updates. Changing cloud-init inputs is
not a substitute for ongoing Ansible configuration on already-booted guests.

Network and storage availability, API ACLs, guest sudo behavior, hostname/SSH
host-key regeneration and disk growth must be verified in a disposable clone.
Static output addresses do not prove the guests are reachable.

Provider reference: https://bpg.sh/docs/resources/virtual_environment_vm/
