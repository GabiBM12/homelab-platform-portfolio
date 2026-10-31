"""Fail-closed guards for creating only the initial, portless vmbr10."""
def network_snapshot(entries):
    return {
        item["iface"]: {k: v for k, v in item.items() if k not in ("active", "exists")}
        for item in entries if item["iface"] != "vmbr10"
    }


def internal_bridge_valid(item):
    return (
        item.get("type") == "bridge"
        and bool(int(item.get("autostart", 0)))
        and item.get("bridge_ports", "") in ("", "none")
        and not int(item.get("bridge_vlan_aware", 0))
        and item.get("method", "manual") == "manual"
        and item.get("method6", "manual") == "manual"
        and not any(item.get(k) for k in
                    ("address", "address6", "cidr", "cidr6", "gateway", "gateway6"))
    )


def bridge_only_diff(diff):
    # Proxmox returns a unified diff in the top-level 'changes' attribute.
    # Reject deletions and any addition other than our exact new bridge stanza.
    # Formatting-only changes may intentionally require manual review.
    allowed = {
        "auto vmbr10", "iface vmbr10 inet manual",
        "bridge-ports none", "bridge-stp off", "bridge-fd 0",
        "bridge-vlan-aware no",
    }
    added = []
    if not isinstance(diff, str) or not diff.strip():
        return False
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ", "@@ ")):
            continue
        if line.startswith("-") and line[1:].strip():
            return False
        if line.startswith("+") and line[1:].strip():
            added.append(line[1:].strip())
    return (
        {"auto vmbr10", "iface vmbr10 inet manual"}.issubset(added)
        and all(line in allowed for line in added)
        and len(added) == len(set(added))
    )


class FilterModule:
    def filters(self):
        return {
            "proxmox_network_snapshot": network_snapshot,
            "proxmox_internal_bridge_valid": internal_bridge_valid,
            "proxmox_bridge_only_diff": bridge_only_diff,
        }
