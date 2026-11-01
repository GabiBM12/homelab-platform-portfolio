# Paste BOTH PUBLIC keys, review the proposed IPs/IDs, then commit this file.
# Loaded explicitly by the deployment workflow; never add private credentials.
# Proposed addresses/IDs: confirm unused and exclude addresses from router DHCP.
proxmox_endpoint = "https://pve.home.locl:8006/"
admin_username   = "ansible"
ssh_public_keys = [
  "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPS0X4f7Sk7yEvVBrhjDfPncixUeXiGPfvQzDnMjsy0h kubernetes-vm",
  "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ11icKI4/e+C1tSk8MpfOAT74BjpoqVQHkl5NbTl8nq k8s-ansible-automation,
]
dns_servers = ["192.168.0.1"] # Confirm the router serves DNS.

nodes = {
  k8s-worker-01 = {
    role          = "worker"
    vm_id         = 211
    proxmox_node  = "pve"
    template_id   = 9000
    template_node = "pve"
    cores         = 2
    memory_mib    = 4096
    disk_gib      = 60
    ipv4_cidr     = "10.20.10.21/24"
    gateway       = "10.20.10.1"
    bridge        = "vmbr10"
  }
  k8s-worker-02 = {
    role          = "worker"
    vm_id         = 212
    proxmox_node  = "pve"
    template_id   = 9000
    template_node = "pve"
    cores         = 2
    memory_mib    = 4096
    disk_gib      = 60
    ipv4_cidr     = "10.20.10.22/24"
    gateway       = "10.20.10.1"
    bridge        = "vmbr10"
  }
}
