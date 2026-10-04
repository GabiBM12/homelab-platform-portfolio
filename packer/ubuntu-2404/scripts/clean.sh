#!/usr/bin/env bash
# Final guest step. Packer subsequently stops the guest through the API.
set -euo pipefail
test "$(id -u)" -eq 0
test "$(hostname)" = ubuntu-packer-build
test "$(cat /etc/homelab-image/base)" = ubuntu-2404
# Leave an inert build account; cloud-init creates the clone's real administrator.
usermod --password '!' --expiredate 1 --shell /usr/sbin/nologin packer
gpasswd -d packer sudo >/dev/null 2>&1 || true
rm -f /etc/sudoers.d/90-packer /home/packer/.ssh/authorized_keys /root/.ssh/authorized_keys
rm -f /home/packer/.bash_history /root/.bash_history
# Installer artifacts can contain the temporary password hash/public key.
rm -rf /var/log/installer
rm -f /etc/cloud/cloud.cfg.d/99-installer.cfg /etc/cloud/cloud.cfg.d/subiquity-disable-cloudinit-networking.cfg
rm -f /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
rm -f /etc/netplan/00-installer-config.yaml /etc/netplan/50-cloud-init.yaml
rm -f /etc/ssh/ssh_host_*
cloud-init clean --logs --machine-id --seed
rm -f /var/lib/dbus/machine-id
ln -s /etc/machine-id /var/lib/dbus/machine-id
apt-get clean
test ! -e /home/packer/.ssh/authorized_keys
test ! -e /etc/sudoers.d/90-packer
test "$(getent shadow packer | cut -d: -f2)" = '!'
# Remove this uploaded script before returning on the existing SSH session.
rm -f -- "$0"
sync
