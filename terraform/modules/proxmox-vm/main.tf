resource "proxmox_virtual_environment_vm" "this" {
  name        = var.name
  node_name   = var.node.proxmox_node
  vm_id       = var.node.vm_id
  description = "Terraform-managed Ubuntu guest; Ansible role: ${var.node.role}"
  tags        = ["terraform", var.node.role == "router" ? "networking" : "kubernetes", replace(var.node.role, "_", "-")]
  started     = true
  on_boot     = true

  clone {
    vm_id        = var.node.template_id
    node_name    = var.node.template_node
    full         = true
    datastore_id = var.node.datastore
  }

  cpu {
    cores = var.node.cores
    type  = "x86-64-v2-AES"
  }

  memory {
    dedicated = var.node.memory_mib
    floating  = 0
  }

  agent {
    enabled = true
    timeout = "5m"
  }

  disk {
    interface    = "scsi0"
    datastore_id = var.node.datastore
    size         = var.node.disk_gib
    file_format  = "raw"
    iothread     = true
  }

  network_device {
    bridge = var.node.bridge
    model  = "virtio"
  }

  dynamic "network_device" {
    for_each = var.additional_networks
    content {
      bridge = network_device.value.bridge
      model  = "virtio"
    }
  }

  initialization {
    datastore_id = var.node.datastore
    interface    = "ide2"
    dns {
      servers = var.dns_servers
    }
    ip_config {
      ipv4 {
        address = var.node.ipv4_cidr
        gateway = var.node.gateway
      }
    }
    dynamic "ip_config" {
      for_each = var.additional_networks
      content {
        ipv4 {
          address = ip_config.value.ipv4_cidr
        }
      }
    }
    user_account {
      username = var.admin_username
      keys     = [for key in var.ssh_public_keys : trimspace(key)]
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
