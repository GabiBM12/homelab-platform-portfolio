output "vm" {
  description = "Desired address and role for the Ansible handoff; not a guest health check."
  value = {
    vm_id        = proxmox_virtual_environment_vm.this.vm_id
    name         = var.name
    proxmox_node = var.node.proxmox_node
    role         = var.node.role
    ipv4_address = split("/", var.node.ipv4_cidr)[0]
    ansible_user = var.admin_username
  }
}
