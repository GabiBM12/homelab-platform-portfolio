"""Local-only integration check: uses installed plugin, never calls Proxmox."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='packer-validate-') as directory:
    work = Path(directory)
    (work / 'seed').mkdir()
    (work / 'seed/user-data').write_text('#cloud-config\n{}\n')
    (work / 'seed/meta-data').write_text('{}\n')
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(work / 'build-key')], check=True)
    variables = {'api_url': 'https://pve.example.invalid:8006/api2/json',
                 'token_id': 'packer@pve!image-build', 'vm_id': 9000,
                 'template_name': 'ubuntu-validation', 'build_directory': directory,
                 'source_revision': 'validation'}
    env = dict(os.environ, CHECKPOINT_DISABLE='1', PKR_VAR_token_secret='dummy-validation-only')
    for iso in ('', 'local:iso/ubuntu-24.04.4-live-server-amd64.iso'):
        variables['existing_iso'] = iso
        varfile = work / 'values.pkrvars.json'
        varfile.write_text(json.dumps(variables))
        subprocess.run(['packer', 'validate', '-var-file=' + str(varfile), str(ROOT)], env=env, check=True)
