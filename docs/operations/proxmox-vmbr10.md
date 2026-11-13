# Create and activate vmbr10 through Ansible

Status: implemented and locally checked; not executed against Proxmox.

The [playbook](../../ansible/playbooks/proxmox/configure-vmbr10.yml) runs on the
Ansible controller via HTTPS, not SSH into the host. It uses built-in uri tasks
so it can inspect Proxmox's top-level pending network diff and poll activation.
No extra Ansible collection is needed. Use a recent ansible-core (>=2.14).

## Scope and safeguards

It creates only vmbr10 on pve: Linux bridge, autostart, no physical ports, no
host IP or gateway. It never connects this bridge to vmbr0 or changes vmbr0.
Settings are in [proxmox-network.yml](../../ansible/vars/proxmox-network.yml);
the bridge name is intentionally fixed to prevent accidental broad targeting.
The older SSH inventory address is not used by this localhost play.

It refuses pre-existing pending edits, incompatible existing vmbr10 settings,
unexpected interface changes and unexpected additions/deletions in the staged
diff. A correct active bridge is a no-op. A compatible inactive one is activated.
Diff formatting differences may cause conservative refusal: inspect the pending
configuration rather than weakening the guard blindly.

Network activation is NODE-WIDE. Have physical/out-of-band console access and
a known-good backup of /etc/network/interfaces before running. Proxmox must have
its supported ifupdown2 package installed. Freeze concurrent UI/API/SDN network
changes during execution: there is no API-wide transaction spanning the checks
and activation, and a race cannot be fully excluded. SDN state is not audited
by this playbook; ensure no unrelated SDN configuration is awaiting activation.
No automatic rollback, network restart over SSH, deletion or reboot is performed.

## Credentials and permissions

Use a dedicated HOST configuration token, not the Packer/Terraform token.
The API requires Sys.Modify on /nodes/pve for creation/reload; give Sys.Audit
for inspection and appropriate task visibility. On releases filtering bridge
visibility, grant the required SDN.Audit/SDN.Use visibility for local bridges
(including vmbr0 and vmbr10). Verify exact paths against your installed API
viewer. Sys.Modify is broader than one bridge; code guards are not an ACL.
Both the user and a privilege-separated token need their effective permissions.

Supply these environment variables to the controller:

- PROXMOX_HOST_API_TOKEN_ID: full user@realm!token identity.
- PROXMOX_HOST_API_TOKEN_SECRET: secret value, provided securely; never in Git.
- PROXMOX_CA_PATH: absolute path to the verified CA PEM on the controller.
  Omit only if its OS trust store already trusts Proxmox.

In a future workflow, expose corresponding GitHub variable/secret only to the
Ansible step and materialize PROXMOX_CA_PEM in a restricted temporary file.
The manual workflow below delivers these values for pipeline runs. Ansible does
not retrieve GitHub secrets when run manually. Do not reuse the broader token
in PR jobs.

## Run through GitHub Actions

The [Configure Proxmox vmbr10 workflow](../../.github/workflows/proxmox-network.yml)
runs only on private GabiBM12/homelab-platform main using runner labels
self-hosted, Linux and homelab-management. It has no push/PR trigger. Management
must already have Ansible (ansible-core >=2.14), Python 3 and OpenSSL installed,
and resolve the API hostname. No sudo or Proxmox SSH key is needed by the job.

Configure these in the PRIVATE repository under Settings → Secrets and
variables → Actions:

| Type | Name | Value |
|---|---|---|
| Variable | PROXMOX_HOST_API_TOKEN_ID | Full dedicated host token identity, e.g. host-config@pve!network |
| Secret | PROXMOX_HOST_API_TOKEN_SECRET | Its token secret; not the Packer/Terraform token |
| Secret | PROXMOX_CA_PEM | Existing verified Proxmox CA certificate contents |

The endpoint and target node come from ansible/vars/proxmox-network.yml, not
Terraform settings. Review that file before merging. The workflow tests the
guards and playbook syntax without credentials, then exposes the host token
only to the API execution step. CA material is written to a private temporary
directory with normal-exit and unconditional cleanup. Hard crashes may still
leave files; a compromised runner can access runtime tokens.

1. Commit/review the workflow, playbook, filters, tests and variables on private main.
2. Open Actions → Configure Proxmox vmbr10 → Run workflow → main, mode check.
3. Review the read-only check result and current Proxmox networking. This is
   not a saved execution plan and does not test write permissions.
4. Ensure console recovery access, a known-good network backup and an exclusive
   change window. Pause Packer/Terraform jobs and all other network/SDN editing.
5. Start a new run with mode apply, confirmation exactly APPLY vmbr10, and check
   console_and_change_window. The playbook rechecks pending changes before writing.
6. Confirm the successful summary and vmbr10 in Proxmox. Router deployment is separate.

Concurrency serializes this workflow only, not other workflows, manual API calls
or UI changes. The apply confirmation is not an independent approval gate.
Use protected branches and optional environment approvals where supported.
Timeout/cancellation does not guarantee cancellation of a Proxmox background
reload task; inspect task state before retrying. No automatic rollback occurs.

## Execute from administration or management

Resolve pve.home.locl to 192.168.0.50 on the controller. Load token credentials
through your secure session/key manager. In a bash shell, a hidden prompt avoids
putting the secret in command history:

```bash
export PROXMOX_HOST_API_TOKEN_ID='host-config@pve!network'
export PROXMOX_CA_PATH='/absolute/path/to/pve-root-ca.pem'
read -r -s -p 'Host API token secret: ' PROXMOX_HOST_API_TOKEN_SECRET
printf '\n'
export PROXMOX_HOST_API_TOKEN_SECRET
cd ansible
ansible-playbook playbooks/proxmox/configure-vmbr10.yml --check
ansible-playbook playbooks/proxmox/configure-vmbr10.yml -e proxmox_network_confirm=true
unset PROXMOX_HOST_API_TOKEN_SECRET
```

Replace the token identity with yours. Check mode reads API configuration only;
it does not certify write privileges or ifupdown2 readiness. Normal execution
requires explicit confirmation before writes, stages the bridge, validates the
diff, applies it, polls the reload task and verifies the active bridge.
API tasks use no_log to protect headers. On failure, inspect Proxmox task and
network UI/console; do not enable credential logging.

If creation succeeds but activation fails, staged changes may remain. A retry
will deliberately refuse them. Inspect/resolve the specific pending changes in
Proxmox and restore connectivity through console if needed. Do not blindly
revert all node networking or delete vmbr10 if guests are already attached.

## Next steps

This is an isolated switch on ONE host, not a router, DHCP server or firewall.
Router VM deployment, routing/NAT/firewall configuration and management routes
are separate work. The control-plane and worker Terraform stacks target vmbr10;
this playbook does not renumber or move existing guests. Configure the router and
management connectivity before guest configuration. Multi-host connectivity needs a shared path
such as a VLAN, not merely matching bridge names.

Source: [Proxmox network API implementation](https://github.com/proxmox/pve-manager/blob/master/PVE/API2/Network.pm).
