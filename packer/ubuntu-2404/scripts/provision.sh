#!/usr/bin/env bash
# Runs only in the temporary Ubuntu build guest, never on Proxmox/management.
set -euo pipefail
test "$(id -u)" -eq 0
test "$(hostname)" = ubuntu-packer-build
timeout 600 cloud-init status --wait
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_ID" = 24.04
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y cloud-init qemu-guest-agent openssh-server python3 sudo ca-certificates
systemctl enable qemu-guest-agent ssh
systemctl start qemu-guest-agent
systemctl is-active --quiet qemu-guest-agent
sshd -t
cloud-init --version
python3 --version
install -d -m 0755 /etc/homelab-image
printf 'ubuntu-2404\n' > /etc/homelab-image/base
printf 'datasource_list: [ NoCloud, ConfigDrive ]\n' > /etc/cloud/cloud.cfg.d/90-homelab-datasources.cfg
