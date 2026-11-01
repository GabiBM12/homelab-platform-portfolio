# Reserve the WAN IP and VM ID before applying; these are proposed values.
# Public keys only. Use separate router automation credentials if desired.
proxmox_endpoint = "https://pve.home.locl:8006/"
admin_username   = "ansible"
ssh_public_keys = [
  "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ11icKI4/e+C1tSk8MpfOAT74BjpoqVQHkl5NbTl8nq k8s-ansible-automation",
  "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPS0X4f7Sk7yEvVBrhjDfPncixUeXiGPfvQzDnMjsy0h kubernetes-vm",
]
dns_servers = ["192.168.0.1"]

router = {
  vm_id         = 200
  proxmox_node  = "pve"
  template_id   = 9000
  template_node = "pve"
  cores         = 2
  memory_mib    = 2048
  disk_gib      = 32
  ipv4_cidr     = "192.168.0.200/24"
  gateway       = "192.168.0.1"
  bridge        = "vmbr0"
  lan_bridge    = "vmbr10"
  lan_cidr      = "10.20.10.1/24"
}
