# Token comes from PROXMOX_VE_API_TOKEN=user@realm!token=secret.
# Trust the verified Proxmox CA via the OS trust store / SSL_CERT_FILE.
# This provider expects the base URL, NOT Packer's /api2/json suffix.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}
