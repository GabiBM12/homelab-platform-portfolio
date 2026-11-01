"""Read-only Azure public-cloud state probe using GitHub OIDC; never log tokens/state."""
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, headers=None, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    return urllib.request.build_opener(NoRedirect()).open(req, timeout=30)


def fingerprint(body):
    # Azure backend can create a zero-byte blob to acquire its first lease.
    # This is not persisted Terraform state; first-deployment/attempt guards apply.
    if not body:
        return "absent"
    state = json.loads(body)
    if not isinstance(state, dict) or state.get("version") != 4 or not isinstance(state.get("serial"), int) or not state.get("lineage"):
        raise ValueError("Invalid Terraform state; restore or investigate the blob.")
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def probe(key):
    account = os.environ["TF_STATE_STORAGE_ACCOUNT"]
    container = os.environ["TF_STATE_CONTAINER"]
    tenant = os.environ["ARM_TENANT_ID"]
    client = os.environ["ARM_CLIENT_ID"]
    if not re.fullmatch(r"[a-z0-9]{3,24}", account) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", container):
        raise ValueError("Invalid storage account or container name.")
    if not all(re.fullmatch(r"[0-9a-fA-F-]{36}", value) for value in (tenant, client)):
        raise ValueError("Azure tenant/client IDs must be GUIDs.")
    if key not in {f"homelab/{stack}.tfstate" for stack in ("router", "control-plane", "workers")}:
        raise ValueError("Unknown state key.")
    oidc_url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    parsed = urllib.parse.urlsplit(oidc_url)
    if parsed.scheme != "https":
        raise ValueError("GitHub OIDC endpoint must use HTTPS.")
    query = dict(urllib.parse.parse_qsl(parsed.query))
    query["audience"] = "api://AzureADTokenExchange"
    oidc_url = urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))
    with request(oidc_url, {"Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]}) as response:
        assertion = json.load(response)["value"]
    form = urllib.parse.urlencode({
        "client_id": client,
        "scope": "https://storage.azure.com/.default",
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": assertion,
    }).encode()
    with request(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                 {"Content-Type": "application/x-www-form-urlencoded"}, form) as response:
        token = json.load(response)["access_token"]
    try:
        with request(f"https://{account}.blob.core.windows.net/{container}/{key}",
                     {"Authorization": "Bearer " + token, "x-ms-version": "2023-11-03"}) as response:
            return fingerprint(response.read())
    except urllib.error.HTTPError as error:
        # Missing container, RBAC, TLS and network failures are NOT a first deployment.
        if error.code == 404 and error.headers.get("x-ms-error-code") == "BlobNotFound":
            return "absent"
        raise


if __name__ == "__main__":
    try:
        print(probe(sys.argv[1]))
    except urllib.error.HTTPError as error:
        sys.exit(f"Azure state/OIDC request failed (HTTP {error.code}); check federation, RBAC and storage firewall. Response suppressed.")
    except (ValueError, KeyError, IndexError, OSError):
        sys.exit("Azure state check failed; check variables, OIDC availability, TLS/network and state integrity. Details suppressed.")
