# Terraform VM deployments

One reusable [VM module](modules/proxmox-vm/README.md) is called by three
independent root configurations: router, control-plane, and workers. Each has
its own state, public-key tfvars and Ansible inventory.

The [pipeline guide](scripts/README.md) explains the three deployment toggles,
separate CI/preflight/plan/apply steps, and migration precautions. CI runs on
GitHub-hosted runners without secrets; deployment runs on management. Unchecked
toggles skip stacks; they never destroy VMs. Adding one worker normally creates
only that new worker, not all existing VMs.

Deploy and configure the router first; K3s nodes use vmbr10 on
10.20.10.0/24. Configure each stack through its own tfvars file:

- [Router](environments/router/router.tfvars)
- [Control planes](environments/control-plane/control-plane.tfvars)
- [Workers](environments/workers/workers.tfvars)

Terraform owns full cloning, VM hardware, NIC attachment and initial cloud-init
configuration. Ansible owns ongoing guest configuration and K3s setup.
Argo CD/application manifests are a later layer. Nothing here deploys K3s,
creates a Proxmox cluster, changes host networking, or creates API identities.

Start with a disposable clone to validate the Packer template. The six-VM target
is not preallocated: actual host capacity, guest IP reservations and the final
template ID must be confirmed first.

Active stacks use Azure Blob remote state with GitHub OIDC. Saved plans remain
on management. See the [pipeline guide](scripts/README.md) for required variables,
first deployment and recovery.
