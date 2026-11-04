mock_provider "proxmox" {}
variables {
  proxmox_endpoint = "https://pve.example.invalid:8006/"
  admin_username   = "ansible"
  ssh_public_keys  = ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDummyValidationOnly test"]
  dns_servers      = ["192.0.2.1"]
  nodes = {
    test-node = {
      role          = "control_plane"
      vm_id         = 201
      proxmox_node  = "pve"
      template_id   = 9000
      template_node = "pve"
      cores         = 2
      memory_mib    = 4096
      disk_gib      = 40
      ipv4_cidr     = "10.20.10.11/24"
      gateway       = "10.20.10.1"
    }
  }
}
run "inventory" {
  command = plan
  assert {
    condition     = output.ansible_inventory.all.children.k3s_server.hosts["test-node"].ansible_host == "10.20.10.11"
    error_message = "Inventory must contain this role's desired address."
  }
}
run "reject_wrong_role" {
  command = plan
  variables {
    nodes = { for name, node in var.nodes : name => merge(node, { role = "router" }) }
  }
  expect_failures = [var.nodes]
}
run "add_node" {
  command = plan
  variables {
    nodes = merge(var.nodes, { test-node-02 = merge(var.nodes["test-node"], { vm_id = 202, ipv4_cidr = "10.20.10.12/24" }) })
  }
  assert {
    condition     = length(output.vms) == 2
    error_message = "Adding a map entry must retain the existing node."
  }
}
run "duplicate_id" {
  command = plan
  variables {
    nodes = merge(var.nodes, { test-node-02 = merge(var.nodes["test-node"], { ipv4_cidr = "10.20.10.12/24" }) })
  }
  expect_failures = [var.nodes]
}
