import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "network_filters", Path(__file__).resolve().parents[1] / "filter_plugins/proxmox_network.py")
filters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filters)


class NetworkGuards(unittest.TestCase):
    def test_expected_bridge_addition(self):
        diff = "--- old\n+++ new\n@@ -1,1 +1,6 @@\n+auto vmbr10\n+iface vmbr10 inet manual\n+    bridge-ports none\n+    bridge-stp off\n+    bridge-fd 0\n"
        self.assertTrue(filters.bridge_only_diff(diff))
        self.assertFalse(filters.bridge_only_diff(diff + "+address 10.20.10.1/24\n"))
        self.assertFalse(filters.bridge_only_diff(diff + "-gateway 192.168.0.1\n"))
        self.assertFalse(filters.bridge_only_diff(diff + "+iface lo inet loopback\n"))
        self.assertFalse(filters.bridge_only_diff(""))

    def test_bridge_must_be_isolated(self):
        bridge = {"type": "bridge", "autostart": 1, "method": "manual"}
        self.assertTrue(filters.internal_bridge_valid(bridge))
        for change in ({"address": "10.20.10.1"}, {"bridge_ports": "nic0"},
                       {"bridge_ports": "vmbr0"}, {"gateway6": "::1"},
                       {"autostart": 0}, {"method": "dhcp"}, {"bridge_vlan_aware": 1}):
            self.assertFalse(filters.internal_bridge_valid(dict(bridge, **change)))

    def test_snapshot_ignores_only_runtime_and_target(self):
        original = [{"iface": "vmbr0", "address": "192.168.0.50", "active": 1}]
        same = [dict(original[0], active=0, exists=1), {"iface": "vmbr10"}]
        changed = [dict(original[0], address="192.168.1.50")]
        self.assertEqual(filters.network_snapshot(original), filters.network_snapshot(same))
        self.assertNotEqual(filters.network_snapshot(original), filters.network_snapshot(changed))


if __name__ == "__main__":
    unittest.main()
