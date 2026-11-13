# Kubernetes playbook boundary

Inventory groups kubernetes, kube_control_plane, and kube_node are populated.
No Kubernetes software is installed by the router playbook.

Next implementations:

- prepare-nodes.yml: shared operating-system preparation using a shared role.
- install-cluster.yml: distribution-specific control-plane and worker roles.

Confirm K3s versus kubeadm before implementing runtime, swap, kernel, cluster
ports, and join procedures. Keep Terraform/cloud-init responsible for initial
addresses and keys. Do not add empty executable playbooks that appear to
configure a cluster successfully.
