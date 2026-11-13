# Proxmox API configuration

The authoritative guide has moved to
[Proxmox host configuration](../docs/operations/proxmox-host-configuration.md).

The [vmbr10 API playbook](../docs/operations/proxmox-vmbr10.md) now creates and
activates the initial internal bridge with explicit confirmation. It is not
yet live-tested. A manual private-main workflow now supports read-only checks
and explicitly confirmed activation in the networking feature. The unused
standalone SSH diagnostic has been removed and is not a prerequisite.
