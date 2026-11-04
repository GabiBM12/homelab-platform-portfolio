output "vms" {
  value = { for name, vm in module.vm : name => vm.vm }
}
output "ansible_inventory" {
  value = {
    all = {
      children = {
        k3s_server = {
          hosts = { for name, vm in module.vm : name => {
            ansible_host = vm.vm.ipv4_address
            ansible_user = vm.vm.ansible_user
            proxmox_node = vm.vm.proxmox_node
          } }
        }
      }
    }
  }
}
