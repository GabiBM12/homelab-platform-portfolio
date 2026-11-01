import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location("remote_state", Path(__file__).resolve().parents[1] / "scripts/remote-state.py")
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)


class RemoteStateTests(unittest.TestCase):
    def test_fingerprint(self):
        state = {"version": 4, "serial": 1, "lineage": "test", "resources": []}
        self.assertEqual(remote.fingerprint(json.dumps(state).encode()), remote.fingerprint(json.dumps(state, indent=2).encode()))
        self.assertEqual(remote.fingerprint(b""), "absent")
        for body in (b"invalid", b"{}", b"[]"):
            with self.assertRaises(ValueError):
                remote.fingerprint(body)

    def test_blob_not_found_only(self):
        env = {
            "TF_STATE_STORAGE_ACCOUNT": "testaccount", "TF_STATE_CONTAINER": "tfstate",
            "ARM_TENANT_ID": "00000000-0000-0000-0000-000000000001",
            "ARM_CLIENT_ID": "00000000-0000-0000-0000-000000000002",
            "ACTIONS_ID_TOKEN_REQUEST_URL": "https://example.invalid/oidc?existing=yes",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "fake-request-token",
        }
        for status, code in ((404, "BlobNotFound"), (404, "ContainerNotFound"), (403, "AuthorizationPermissionMismatch"), (500, "ServerError")):
            with patch.dict(os.environ, env), patch.object(remote, "request", side_effect=[
                io.BytesIO(b'{"value":"fake-assertion"}'),
                io.BytesIO(b'{"access_token":"fake-access"}'),
                HTTPError("https://example.invalid", status, "error", {"x-ms-error-code": code}, None),
            ]) as mock:
                if code == "BlobNotFound":
                    self.assertEqual(remote.probe("homelab/workers.tfstate"), "absent")
                else:
                    with self.assertRaises(HTTPError):
                        remote.probe("homelab/workers.tfstate")
                self.assertIn("audience=api%3A%2F%2FAzureADTokenExchange", mock.call_args_list[0].args[0])


if __name__ == "__main__":
    unittest.main()
