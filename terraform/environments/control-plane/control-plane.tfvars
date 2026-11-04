# Paste BOTH PUBLIC keys, review the proposed IPs/IDs, then commit this file.
# Loaded explicitly by the deployment workflow; never add private credentials.
# Proposed addresses/IDs: confirm unused and exclude addresses from router DHCP.
proxmox_endpoint = "https://pve.home.locl:8006/"
admin_username   = "ansible"
ssh_public_keys = [
  "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ11icKI4/e+C1tSk8MpfOAT74BjpoqVQHkl5NbTl8nq k8s-ansible-automation",
  "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPS0X4f7Sk7yEvVBrhjDfPncixUeXiGPfvQzDnMjsy0h kubernetes-vm",
]
dns_servers = ["192.168.0.1"] # Confirm the router serves DNS.

nodes = {
  k3s-cp-01 = {
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
    bridge        = "vmbr10"
  }
}
