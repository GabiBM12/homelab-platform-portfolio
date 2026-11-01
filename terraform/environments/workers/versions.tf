terraform {
  required_version = ">= 1.7.0, < 2.0.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "= 0.118.0"
    }
  }
}
