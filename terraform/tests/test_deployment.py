"""Offline tests: no API, persistent runner state, or Terraform apply."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("plan_guard", SCRIPTS / "check-plan.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class DeploymentTests(unittest.TestCase):
    def shell(self, code, extra=None):
        env = dict(os.environ)
        env.update(extra or {})
        return subprocess.run(
            ["bash", "-c", 'source "$COMMON"\n' + code],
            env={**env, "COMMON": str(SCRIPTS / "common.sh")},
            capture_output=True, text=True,
        )

    def test_plan_guard(self):
        for actions in (["create"], ["update"], ["no-op"]):
            guard.check({"resource_changes": [{"change": {"actions": actions}}]})
        for actions in (["delete"], ["delete", "create"], ["create", "delete"]):
            with self.assertRaises(ValueError):
                guard.check({"resource_changes": [{"change": {"actions": actions}}]})

    def test_selection(self):
        for flag, expected in (("SELECT_ROUTER", "router"), ("SELECT_CONTROL_PLANE", "control-plane"), ("SELECT_WORKERS", "workers")):
            flags = {"SELECT_ROUTER": "false", "SELECT_CONTROL_PLANE": "false", "SELECT_WORKERS": "false", flag: "true"}
            result = self.shell("selected_stacks", flags)
            self.assertEqual(result.stdout.strip(), expected)
        result = self.shell("select_stack kubernetes")
        self.assertNotEqual(result.returncode, 0)

    def test_missing_state_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            code = 'remote_state_fingerprint() { echo absent; }; base_state="$TEST_DIR"; select_stack workers; DEPLOY_MODE=plan; check_state'
            self.assertNotEqual(self.shell(code, {"TEST_DIR": directory, "FIRST_DEPLOYMENT": "false"}).returncode, 0)
            self.assertEqual(self.shell(code, {"TEST_DIR": directory, "FIRST_DEPLOYMENT": "true"}).returncode, 0)

    def test_legacy_state_blocks_all_stacks(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "terraform.tfstate").write_text('{"resources": []}')
            for stack in ("control-plane", "workers", "router"):
                result = self.shell(f'base_state="$TEST_DIR"; select_stack {stack}; DEPLOY_MODE=plan; check_state', {"TEST_DIR": directory, "FIRST_DEPLOYMENT": "true"})
                self.assertNotEqual(result.returncode, 0)

    def test_saved_plan_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory, "workers", "plans", "123")
            plan.mkdir(parents=True)
            for name, value in {"ready": "", "deployment.tfplan": "test fixture", "revision": "a" * 40, "state-fingerprint": "absent", "backend": "test-backend"}.items():
                (plan / name).write_text(value)
            code = 'remote_state_fingerprint() { echo absent; }; backend_identity() { echo test-backend; }; base_state="$TEST_DIR"; select_stack workers; check_saved_plan'
            env = {"TEST_DIR": directory, "PLAN_RUN_ID": "123", "GITHUB_SHA": "a" * 40}
            self.assertEqual(self.shell(code, env).returncode, 0)
            self.assertNotEqual(self.shell(code, {**env, "GITHUB_SHA": "b" * 40}).returncode, 0)
            self.assertNotEqual(self.shell(code.replace('echo absent', 'echo changed'), env).returncode, 0)
            self.assertNotEqual(self.shell(code.replace('echo test-backend', 'echo other-backend'), env).returncode, 0)
            (plan / "apply-started").touch()
            self.assertNotEqual(self.shell(code, env).returncode, 0)

    def test_script_syntax(self):
        for script in SCRIPTS.glob("*.sh"):
            self.assertEqual(subprocess.run(["bash", "-n", str(script)]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
