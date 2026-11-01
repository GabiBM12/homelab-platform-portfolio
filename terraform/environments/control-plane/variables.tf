variable "proxmox_endpoint" {
  type        = string
  description = "Certificate-valid base URL, e.g. https://pve.home.locl:8006/"
  validation {
    condition     = can(regex("^https://[A-Za-z0-9.-]+(:[0-9]+)?/?$", var.proxmox_endpoint))
    error_message = "Use an HTTPS base URL without credentials, query parameters or /api2/json."
  }
}

variable "admin_username" {
  type = string
}
variable "ssh_public_keys" {
  type = list(string)
}
variable "dns_servers" {
  type = list(string)
}
