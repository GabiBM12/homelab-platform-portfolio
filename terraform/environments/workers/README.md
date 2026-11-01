# Worker VM stack

Edit `workers.tfvars` (public keys only). All entries must have role `worker`.
To add a worker, retain the existing entries and append a stable name with a
globally unique VM ID/IP. Select only `deploy_workers`, plan, review, then apply
that saved plan. Unchanged workers are not recreated; all differences in this
stack are still included in the plan.

State is stored in Azure at homelab/workers.tfstate. Saved plans and Ansible
inventory remain under `/var/lib/homelab-terraform/workers/`.
The inventory group is `kube_node`. Ansible must configure and join the new VM
to Kubernetes separately; Terraform does not perform that operation.

See [pipeline steps and migration safeguards](../../scripts/README.md).
Never run this against existing combined-state VMs without state migration.
