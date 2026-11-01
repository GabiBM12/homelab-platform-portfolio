# Only this role is managed by this state. Keep stable map keys.
variable "nodes" {
  type = map(object({
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
    bridge        = optional(string, "vmbr10")
  }))
  validation {
    condition     = length(var.nodes) > 0
    error_message = "Define at least one explicitly approved VM."
  }
  validation {
    condition     = length(distinct([for n in values(var.nodes) : n.vm_id])) == length(var.nodes)
    error_message = "VM IDs must be unique across the cluster."
  }
  validation {
    condition     = length(distinct([for n in values(var.nodes) : split("/", n.ipv4_cidr)[0]])) == length(var.nodes)
    error_message = "Guest IP addresses must be unique."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : !contains([for t in values(var.nodes) : t.template_id], n.vm_id)])
    error_message = "A guest ID cannot be any source template ID."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : n.role == "worker"])
    error_message = "This stack only manages worker nodes."
  }
}
