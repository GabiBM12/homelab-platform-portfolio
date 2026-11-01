variable "name" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,62}$", var.name))
    error_message = "Use a stable lowercase hostname."
  }
}

variable "node" {
  type = object({
    vm_id         = number
    role          = string
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
  })
  validation {
    condition = (
      contains(["control_plane", "worker", "router"], var.node.role) &&
      var.node.vm_id >= 100 && var.node.vm_id <= 999999999 &&
      floor(var.node.vm_id) == var.node.vm_id &&
      var.node.template_id >= 100 && var.node.template_id <= 999999999 &&
      floor(var.node.template_id) == var.node.template_id &&
      var.node.vm_id != var.node.template_id &&
      var.node.cores >= 1 && floor(var.node.cores) == var.node.cores &&
      var.node.memory_mib >= 2048 && floor(var.node.memory_mib) == var.node.memory_mib &&
      var.node.disk_gib >= 32 && floor(var.node.disk_gib) == var.node.disk_gib &&
      can(cidrnetmask(var.node.ipv4_cidr)) &&
      can(cidrnetmask("${var.node.gateway}/32"))
    )
    error_message = "Check role, integer IDs/sizing, IPv4 CIDR and gateway. Disk must be at least the 32 GiB template size."
  }
}

variable "additional_networks" {
  description = "Ordered NICs after the primary NIC; no additional default gateways."
  type = list(object({
    bridge    = string
    ipv4_cidr = string
  }))
  default = []
  validation {
    condition = alltrue([for nic in var.additional_networks :
      can(regex("^vmbr[0-9]+$", nic.bridge)) && can(cidrnetmask(nic.ipv4_cidr))
    ])
    error_message = "Additional NICs require a vmbr bridge and IPv4 CIDR."
  }
}

variable "admin_username" {
  type = string
  validation {
    condition     = can(regex("^[a-z_][a-z0-9_-]*$", var.admin_username)) && !contains(["root", "packer"], var.admin_username)
    error_message = "Choose a non-root administrator other than the disabled image-build account."
  }
}

variable "ssh_public_keys" {
  type = list(string)
  validation {
    condition = length(var.ssh_public_keys) > 0 && alltrue([
      for key in var.ssh_public_keys : can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256) [A-Za-z0-9+/=]+", trimspace(key)))
    ])
    error_message = "Supply at least one OpenSSH public key, never a private key."
  }
}

variable "dns_servers" {
  type = list(string)
  validation {
    condition     = length(var.dns_servers) > 0 && alltrue([for ip in var.dns_servers : can(cidrnetmask("${ip}/32"))])
    error_message = "Supply IPv4 DNS server addresses."
  }
}
