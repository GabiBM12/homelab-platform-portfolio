module "vm" {
  source   = "../../modules/proxmox-vm"
  for_each = var.nodes

  name            = each.key
  node            = each.value
  admin_username  = var.admin_username
  ssh_public_keys = var.ssh_public_keys
  dns_servers     = var.dns_servers
}
