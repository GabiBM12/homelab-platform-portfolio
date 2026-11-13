"""Offline render/policy regressions; kernel nft validation runs on the router."""
from pathlib import Path
import unittest
import jinja2

TEMPLATE = Path(__file__).resolve().parents[1] / "roles/router_network/templates/router.nft.j2"


class RouterPolicyTests(unittest.TestCase):
    def render(self, api=False):
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters["bool"] = bool
        return env.from_string(TEMPLATE.read_text()).render(
            router_wan_interface="eth0",
            router_lan_interface="et1",
            router_management_cidr="192.168.0.142/32",
            router_admin_cidr="192.168.0.133/32",
            router_private_subnet="10.20.10.0/24",
            router_allow_kubernetes_api=api,
        )

    def test_scope_and_nat(self):
        rules = self.render()
        self.assertNotIn("flush ruleset", rules)
        self.assertIn('oifname "eth0" ip saddr 10.20.10.0/24 masquerade', rules)
        self.assertEqual(rules.count("policy drop"), 2)
        self.assertIn("ct state established,related accept", rules)

    def test_only_management_forwarded_ssh(self):
        forward = self.render().split("chain forward {")[1].split("chain output")[0]
        ssh = [line for line in forward.splitlines() if "dport 22" in line]
        self.assertEqual(len(ssh), 1)
        self.assertIn("ip saddr 192.168.0.142/32", ssh[0])
        self.assertNotIn("192.168.0.133", forward)

    def test_api_opt_in(self):
        self.assertNotIn("dport 6443", self.render())
        self.assertIn("dport 6443", self.render(api=True))


if __name__ == "__main__":
    unittest.main()
