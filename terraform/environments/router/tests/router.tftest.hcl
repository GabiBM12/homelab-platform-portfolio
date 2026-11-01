mock_provider "proxmox" {}

variables {
  proxmox_endpoint = "https://pve.example.invalid:8006/"
  admin_username   = "ansible"
  ssh_public_keys  = ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDummyValidationOnly test"]
  dns_servers      = ["192.0.2.1"]
  router = {
    vm_id         = 200
    proxmox_node  = "pve"
    template_id   = 9000
    template_node = "pve"
    cores         = 2
    memory_mib    = 2048
    disk_gib      = 32
    ipv4_cidr     = "192.0.2.200/24"
    gateway       = "192.0.2.1"
    lan_cidr      = "10.20.10.1/24"
  }
}

run "router_inventory" {
  command = plan
  assert {
    condition     = output.ansible_inventory.all.children.routers.hosts.router01.ansible_host == "192.0.2.200"
    error_message = "Router bootstrap must use its reachable WAN address."
  }
}

run "reject_same_bridge" {
  command = plan
  variables {
    router = merge(var.router, { lan_bridge = "vmbr0" })
  }
  expect_failures = [var.router]
}
