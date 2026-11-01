# Azure-backed Terraform deployment

The workflow keeps CI on GitHub-hosted runners without secrets and runs selected
router/control-plane/worker plan and apply steps on the management runner.
Unchecked toggles skip stacks; they never delete VMs.

## Storage and authentication

The three active roots use the azurerm backend with GitHub OIDC and Entra data
authorization. State keys are homelab/router.tfstate,
homelab/control-plane.tfstate and homelab/workers.tfstate in the configured
container. Azure Blob leases provide Terraform locking. The runner still uses
a filesystem lock and workflow concurrency to serialize local plan handling.

Required private-repository variables:
- AZURE_CLIENT_ID
- AZURE_TENANT_ID
- TF_STATE_STORAGE_ACCOUNT
- TF_STATE_CONTAINER
- TERRAFORM_PROXMOX_API_TOKEN_ID

Required secrets remain TERRAFORM_PROXMOX_API_TOKEN_SECRET and PROXMOX_CA_PEM.
Only the deployment job has id-token: write. No Azure client secret, storage
access key, Azure CLI, or azure/login step is needed. The identity must have
Storage Blob Data Contributor on the container and exact GitHub federation.
Use the normal Azure public-cloud blob endpoint. The storage firewall must
allow management's outbound connection; OIDC does not bypass network rules.
No subscription-wide role is needed for this data-plane configuration.

## Scripts

| Script | Responsibility |
| --- | --- |
| validate.sh | Backend-disabled validation and mocked tests; no cloud access |
| preflight.sh | Tools, confirmations, all selected configs, Azure state reads and saved-plan guards |
| remote-state.py | Short-lived OIDC exchange and read-only state fingerprint; errors are not treated as missing state |
| plan.sh | Initialize Azure backend, create reviewed plan, reject deletion/replacement |
| apply.sh | Recheck backend/revision/state, apply saved plan, export inventory |
| common.sh | Shared paths, authentication setup, locks, temporary-file cleanup |
| check-plan.py | Reject deletion/replacement before saving and applying |
| deploy-homelab.sh | Optional single-stack compatibility wrapper |

State is NOT stored in /var/lib/homelab-terraform anymore. Local files under
/var/lib/homelab-terraform/STACK/ are saved plans, attempt markers and Ansible
inventory only. Keep the designated terraform-homelab runner for plan/apply.
Prepare its mode-0700 directory using prepare-terraform-runner.yml if necessary.
Plans contain sensitive data: protect the management disk and do not publish
plans or state in logs/artifacts. Losing a plan means creating/reviewing a new one;
losing the runner no longer loses the authoritative state.

## First deployment

1. Confirm the four Azure variables, federation, container-level RBAC and storage
   network access. Enable Azure blob versioning/soft delete and bounded retention
   separately; the pipeline does not create or configure the storage account.
2. Fill public-key placeholders and reserve unique VM IDs/IPs in the selected
   STACK.tfvars. The current endpoint must resolve on management.
3. Merge reviewed changes and lock files to private main.
4. Run Deploy homelab VMs: select router, mode plan, first_deployment=true, and
   confirm_network=true. No accept_local_state input remains.
5. Review the successful plan log and note its workflow run ID.
6. Run apply at the SAME commit, select router and supply that plan_run_id.
   first_deployment is only needed when planning missing state.
7. Verify router VM health, then configure routing/NAT/firewall using separate
   Ansible automation before configuring Kubernetes guests. Deploy control
   planes/workers with their own toggles using the same plan/review/apply process.

All selected plans must come from the supplied plan run. Applying a subset is
allowed. Adding a worker requires retaining existing map entries and adding one
new stable key; only differences in the selected stack are applied.

## Safety and recovery

Saved plans bind to the tenant, storage account, container, stack key, Git commit,
and remote state fingerprint. Changed backend variables require a NEW plan.
Terraform additionally checks plan/state consistency under its Azure lease.
A failed/attempted plan cannot be reused. A local azure-apply-started marker
prevents silently recreating missing remote state after an apply attempt.
A truly missing blob (or Azure's initial empty lease placeholder) requires explicit
first-deployment confirmation. Authentication failures, missing containers,
network errors and malformed state fail closed. This confirmation is not a reset:
if state is lost, restore a version or perform reviewed import/reconciliation.

No automatic state migration occurs: legacy local state/initialized markers and
errored.tfstate block deployment. Since no VMs have been deployed, no migration
should be necessary. If those files exist, stop and inspect; never delete them
to bypass the guard. Keep any emergency state written after an Azure upload
failure. It is not removed by temporary-directory cleanup.

Azure versioning/soft-delete replace the script's local state-copy backups;
configure and test recovery yourself. Do not restore old versions while a job
is active. Multi-stack apply is not a transaction: successful stacks stay applied
if a later stack fails. Review partial state and make a new plan for remaining
stacks. Never force-unlock an active job.

Ansible inventories remain at /var/lib/homelab-terraform/STACK/inventory.local.yml.
Supply both Kubernetes inventory files for cluster-wide configuration.
Terraform does not use guest SSH private keys.

References:
- https://developer.hashicorp.com/terraform/language/backend/azurerm
- https://learn.microsoft.com/en-us/azure/terraform/terraform-backend
