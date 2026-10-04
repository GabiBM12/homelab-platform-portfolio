packer {
  required_version = ">= 1.11.0, < 2.0.0"
  required_plugins {
    proxmox = {
      version = "= 1.2.4"
      source  = "github.com/hashicorp/proxmox"
    }
  }
}

variable "api_url" { type = string }
variable "token_id" { type = string }
variable "token_secret" {
  type      = string
  sensitive = true
}
variable "vm_id" { type = number }
variable "template_name" { type = string }
variable "build_directory" { type = string }
variable "existing_iso" {
  type    = string
  default = ""
}
variable "source_revision" { type = string }

locals {
  config = jsondecode(file("${path.root}/build.json"))
}

source "proxmox-iso" "ubuntu" {
  proxmox_url              = var.api_url
  username                 = var.token_id
  token                    = var.token_secret
  insecure_skip_tls_verify = false
  node                     = local.config.node
  vm_id                    = var.vm_id
  vm_name                  = var.template_name
  template_name            = var.template_name
  template_description     = "Ubuntu 24.04.4; source ${var.source_revision}; ISO SHA256 ${local.config.iso_sha256}"
  tags                     = "packer;ubuntu-2404"
  os                       = "l26"
  bios                     = "seabios"
  cores                    = local.config.cores
  memory                   = local.config.memory_mib
  scsi_controller          = "virtio-scsi-single"
  qemu_agent               = true
  onboot                   = false

  boot_iso {
    type             = "ide"
    index            = "2"
    iso_file         = var.existing_iso != "" ? var.existing_iso : null
    iso_url          = var.existing_iso == "" ? local.config.iso_url : null
    iso_checksum     = "sha256:${local.config.iso_sha256}"
    iso_storage_pool = local.config.iso_storage
    iso_target_path  = "${var.build_directory}/${local.config.iso_filename}"
    iso_download_pve = false
    unmount          = true
  }

  additional_iso_files {
    type             = "ide"
    index            = "0"
    cd_files         = ["${var.build_directory}/seed/user-data", "${var.build_directory}/seed/meta-data"]
    cd_label         = "cidata"
    iso_storage_pool = local.config.iso_storage
    unmount          = true
  }

  disks {
    type         = "scsi"
    disk_size    = "${local.config.disk_size_gib}G"
    storage_pool = local.config.disk_storage
    format       = "raw"
    io_thread    = true
  }

  network_adapters {
    model  = "virtio"
    bridge = local.config.bridge
  }

  boot      = "order=scsi0;ide2;net0"
  boot_wait = "10s"
  boot_command = [
    "c<wait>",
    "linux /casper/vmlinuz autoinstall ds=nocloud ---<enter><wait>",
    "initrd /casper/initrd<enter><wait>",
    "boot<enter>"
  ]

  communicator                 = "ssh"
  ssh_username                 = "packer"
  ssh_private_key_file         = "${var.build_directory}/build-key"
  ssh_agent_auth               = false
  ssh_disable_agent_forwarding = true
  ssh_timeout                  = "45m"
  task_timeout                 = "15m"
  cloud_init                   = true
  cloud_init_storage_pool      = local.config.disk_storage
  cloud_init_disk_type         = "ide"
}

build {
  sources = ["source.proxmox-iso.ubuntu"]

  provisioner "shell" {
    script          = "${path.root}/scripts/provision.sh"
    execute_command = "sudo -n /bin/bash '{{ .Path }}'"
  }

  provisioner "shell" {
    script            = "${path.root}/scripts/clean.sh"
    execute_command   = "sudo -n /bin/bash '{{ .Path }}'"
    skip_clean        = true
    expect_disconnect = false
  }
}
