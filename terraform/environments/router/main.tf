variable "router" {
  description = "Dedicated router VM. IDs and WAN address must be reserved before apply."
  type = object({
    vm_id         = number
    proxmox_node  = string
    template_id   = number
    template_node = string
    cores         = number
    memory_mib    = number
    disk_gib      = number
    ipv4_cidr     = string
    gateway       = string
    datastore     = optional(string, "local-lvm")
    bridge        = optional(string, "vmbr0")
    lan_bridge    = optional(string, "vmbr10")
    lan_cidr      = string
  })
  validation {
    condition = (
      var.router.bridge != var.router.lan_bridge &&
      can(cidrnetmask(var.router.lan_cidr)) &&
      try(cidrhost(var.router.ipv4_cidr, 0) != cidrhost(var.router.lan_cidr, 0), false)
    )
    error_message = "Router WAN and LAN must use distinct bridges and networks."
  }
}

module "router" {
  source          = "../../modules/proxmox-vm"
  name            = "router01"
  node            = merge(var.router, { role = "router" })
  admin_username  = var.admin_username
  ssh_public_keys = var.ssh_public_keys
  dns_servers     = var.dns_servers
  additional_networks = [{
    bridge    = var.router.lan_bridge
    ipv4_cidr = var.router.lan_cidr
  }]
}

output "ansible_inventory" {
  description = "Reach the router through its home-LAN address before lab routing exists."
  value = {
    all = {
      children = {
        routers = {
          hosts = {
            router01 = {
              ansible_host = module.router.vm.ipv4_address
              ansible_user = module.router.vm.ansible_user
              proxmox_node = module.router.vm.proxmox_node
              lab_cidr     = var.router.lan_cidr
            }
          }
        }
      }
    }
  }
}
