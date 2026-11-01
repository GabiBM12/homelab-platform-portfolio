# Public Azure Blob endpoint; GitHub OIDC credentials come from the job environment.
# Storage account/container and unique homelab/control-plane.tfstate key supplied by init.
terraform {
  backend "azurerm" {
    use_oidc         = true
    use_azuread_auth = true
    use_cli          = false
  }
}
