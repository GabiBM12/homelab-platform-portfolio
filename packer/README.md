# Proxmox image builds

The first implementation builds an Ubuntu Server 24.04 template on Proxmox,
coordinated by the management VM's private-repository runner.

- Template and pinned ISO settings: `ubuntu-2404/`
- Workflow: [Build Ubuntu Proxmox template](../.github/workflows/packer-ubuntu.yml)
- Setup, permissions, execution and recovery:
  [Ubuntu image build runbook](../docs/operations/ubuntu-image-build.md)

The workflow defaults to read-only Proxmox preflight. It has not been live-tested
against the owner's host. Review prerequisites before selecting `build`.
