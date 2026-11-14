"""Offline render/policy regressions; kernel nft validation runs on the router."""
from pathlib import Path
import base64
import json
import re
import unittest
import jinja2
import yaml

TEMPLATE = Path(__file__).resolve().parents[1] / "roles/router_network/templates/router.nft.j2"
TASKS = TEMPLATE.parent.parent / "tasks/main.yml"


class UfwRetirementTests(unittest.TestCase):
    def setUp(self):
        tasks = yaml.safe_load(TASKS.read_text())
        self.ufw = next(t for t in tasks if t["name"] == "Inspect and retire only an unused UFW service")
        self.env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        self.env.filters["b64decode"] = lambda s: base64.b64decode(s).decode()
        self.env.filters["regex_findall"] = lambda s, p: re.findall(p, s)
        self.env.filters["from_json"] = json.loads

    def inactive_allowed(self, status, config):
        guard = next(t for t in self.ufw["block"] if t["name"] == "Require explicitly inactive UFW")
        values = {
            "router_ufw_status": {"stdout": status},
            "router_ufw_config": {"content": base64.b64encode(config.encode()).decode()},
        }
        return all(self.env.compile_expression(expr)(**values)
                   for expr in guard["ansible.builtin.assert"]["that"])

    def test_inactive_explicitly_disabled(self):
        self.assertTrue(self.inactive_allowed("Status: inactive\n", "ENABLED=no\n"))

    def test_active_enabled_missing_or_ambiguous_refused(self):
        for status, config in [
            ("Status: active", "ENABLED=no\n"),
            ("Status: inactive", "ENABLED=yes\n"),
            ("Status: inactive", "# ENABLED=no\n"),
            ("Status: inactive", "ENABLED=no\nENABLED=yes\n"),
        ]:
            with self.subTest(status=status, config=config):
                self.assertFalse(self.inactive_allowed(status, config))

    def test_only_empty_ruleset_permits_retirement(self):
        block = next(t for t in self.ufw["block"] if "block" in t)["block"]
        guard = next(t for t in block if "ansible.builtin.assert" in t)
        expr = self.env.compile_expression(guard["ansible.builtin.assert"]["that"][0])
        for objects, allowed in [
            ([], True),
            ([{"metainfo": {"version": "test"}}], True),
            ([{"table": {"family": "inet", "name": "ufw"}}], False),
            ([{"table": {"family": "inet", "name": "homelab_router"}}], False),
        ]:
            with self.subTest(objects=objects):
                self.assertEqual(bool(expr(router_ufw_ruleset={
                    "stdout": json.dumps({"nftables": objects})})), allowed)

    def test_check_mode_inspection_is_read_only(self):
        block = next(t for t in self.ufw["block"] if "block" in t)["block"]
        disable = next(t for t in block if "ansible.builtin.systemd_service" in t)
        # Never force the modifying task to run during --check.
        self.assertNotIn("check_mode", disable)
        self.assertEqual(disable["ansible.builtin.systemd_service"]["state"], "stopped")


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
