#!/usr/bin/env python3
"""Private runner entry point. Standard library only; no Proxmox SSH required."""
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class BuildError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise BuildError(message)


def vm_id(value):
    require(bool(re.fullmatch(r'[1-9][0-9]{2,8}', value)), 'VM ID must be 100..999999999.')
    return int(value)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BuildError('Refusing API redirect; check PROXMOX_API_URL.')


class API:
    def __init__(self, url, identity, token, ca=None):
        parsed = urllib.parse.urlsplit(url)
        require(parsed.scheme == 'https' and parsed.hostname and
                parsed.path.rstrip('/') == '/api2/json' and not parsed.username
                and not parsed.query and not parsed.fragment, 'Set a valid HTTPS API URL ending /api2/json.')
        require(bool(re.fullmatch(r'[^\s!]+@[^\s!]+![A-Za-z0-9_-]+', identity)),
                'Set PACKER_PROXMOX_API_TOKEN_ID, e.g. packer@pve!image-build.')
        require(bool(token) and not any(c.isspace() for c in token), 'Missing or invalid API secret.')
        self.url = url.rstrip('/')
        self.auth = f'PVEAPIToken={identity}={token}'
        context = ssl.create_default_context()
        if ca:
            context.load_verify_locations(cadata=ca)
        self.opener = urllib.request.build_opener(
            NoRedirect(), urllib.request.HTTPSHandler(context=context))

    def get(self, path):
        request = urllib.request.Request(self.url + path, headers={'Authorization': self.auth})
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)['data']
        except urllib.error.HTTPError as error:
            raise BuildError(f'Proxmox GET {path} returned HTTP {error.code}; check ACLs/resource state.') from None
        except (urllib.error.URLError, ssl.SSLError):
            raise BuildError('Proxmox connection/TLS failed; verify routing, CA trust and certificate SAN.') from None


def choose_iso(content, config, reuse):
    expected = f"{config['iso_storage']}:iso/{config['iso_filename']}"
    matches = [entry for entry in content if entry.get('volid') == expected]
    if not matches:
        return ''
    require(reuse, 'Ubuntu ISO already exists. Verify its provenance, then explicitly enable reuse_verified_iso; no overwrite is attempted.')
    require(int(matches[0].get('size', 0)) == config['iso_size'], 'Existing ISO size differs; investigate it manually.')
    print('Reusing operator-approved ISO. Remote contents are NOT independently checksum-verified by this preflight.')
    return expected


def preflight(api, config, identifier, reuse):
    version = api.get('/version')
    print('Proxmox version:', version.get('version', 'unknown'))
    # Unlike filtered VM listings, nextid?vmid checks whether the ID is occupied.
    free = api.get(f'/cluster/nextid?vmid={identifier}')
    require(int(free) == identifier, 'Requested VM ID is not free.')
    node = config['node']
    status = api.get(f'/nodes/{node}/status')
    require(status.get('cpuinfo', {}).get('cpus', 0) >= config['cores'], 'Insufficient host CPU count.')
    require(status.get('memory', {}).get('free', 0) >= config['memory_mib'] * 1024**2,
            'Insufficient reported free host RAM for the build.')
    networks = api.get(f'/nodes/{node}/network')
    require(any(n.get('iface') == config['bridge'] and n.get('type') == 'bridge' for n in networks),
            'Expected Proxmox bridge is missing.')
    for storage, content, minimum in [
        (config['iso_storage'], 'iso', 8 * 1024**3),
        (config['disk_storage'], 'images', config['disk_size_gib'] * 1024**3),
    ]:
        info = api.get(f'/nodes/{node}/storage/{storage}/status')
        require(info.get('active') and info.get('enabled', 1), f'Storage {storage} is inactive/disabled.')
        require(content in info.get('content', '').split(','), f'Storage {storage} must support {content}.')
        require(info.get('avail', 0) >= minimum, f'Insufficient available space on {storage}.')
    media = api.get(f"/nodes/{node}/storage/{config['iso_storage']}/content?content=iso")
    return choose_iso(media, config, reuse)


def seed(public_key, password_hash):
    # JSON is valid YAML: prefix provides the cloud-init content type without a YAML dependency.
    answer = {'autoinstall': {
        'version': 1,
        'refresh-installer': {'update': False},
        'locale': 'en_US.UTF-8',
        'keyboard': {'layout': 'us'},
        'identity': {'hostname': 'ubuntu-packer-build', 'username': 'packer', 'password': password_hash},
        'ssh': {'install-server': True, 'allow-pw': False, 'authorized-keys': [public_key.strip()]},
        'network': {'version': 2, 'ethernets': {'build': {'match': {'name': 'en*'}, 'dhcp4': True}}},
        'storage': {'layout': {'name': 'direct'}},
        'packages': ['qemu-guest-agent', 'cloud-init', 'python3', 'sudo'],
        'late-commands': ['curtin in-target --target=/target -- systemctl enable qemu-guest-agent'],
        'user-data': {
            'disable_root': True,
            'ssh_pwauth': False,
            'write_files': [{'path': '/etc/sudoers.d/90-packer', 'permissions': '0440',
                             'content': 'packer ALL=(ALL) NOPASSWD: ALL\n'}],
            'runcmd': [['systemctl', 'start', 'qemu-guest-agent']],
        },
    }}
    return '#cloud-config\n' + json.dumps(answer, indent=2) + '\n'


def run(command, env):
    process = subprocess.Popen(command, env=env, start_new_session=True)
    try:
        code = process.wait()
        require(code == 0, f'{command[0]} {command[1]} failed (exit {code}). Inspect sanitized output and Proxmox tasks.')
    except BaseException:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        raise


def verify_template(api, config, identifier, name):
    data = api.get(f"/nodes/{config['node']}/qemu/{identifier}/config")
    require(data.get('template') == 1, 'Build result is not a Proxmox template.')
    require(data.get('name') == name, 'Template name differs from this run.')
    require(str(data.get('scsi0', '')).startswith(config['disk_storage'] + ':'), 'Unexpected template disk storage.')
    require(any('cloudinit' in str(v) for k, v in data.items() if re.fullmatch(r'(ide|sata|scsi)\d+', k)),
            'Template has no cloud-init drive.')
    require(not any('.iso' in str(v) for k, v in data.items() if re.fullmatch(r'(ide|sata|scsi)\d+', k)),
            'Installation media remains attached.')


def main():
    os.umask(0o077)
    require(sys.platform.startswith('linux') and os.geteuid() != 0, 'Run as the unprivileged Linux runner.')
    mode = os.environ.get('BUILD_MODE', 'preflight')
    require(mode in ('preflight', 'build'), 'Invalid build mode.')
    identifier = vm_id(os.environ.get('BUILD_VM_ID', '9000'))
    for tool in ('packer', 'ssh-keygen', 'openssl', 'xorriso'):
        require(shutil.which(tool), f'Missing {tool}; update management tools from the administration laptop.')
    config = json.loads((ROOT / 'build.json').read_text())
    ca = os.environ.get('PROXMOX_CA_PEM', '')
    api = API(os.environ.get('PROXMOX_API_URL', ''), os.environ.get('PACKER_TOKEN_ID', ''),
              os.environ.get('PACKER_TOKEN_SECRET', ''), ca)
    existing = preflight(api, config, identifier, os.environ.get('REUSE_VERIFIED_ISO') == 'true')
    runtime_root = os.environ.get('RUNNER_TEMP')
    require(runtime_root and Path(runtime_root).is_dir(), 'RUNNER_TEMP must identify the runner temporary directory.')
    require(shutil.disk_usage(runtime_root).free >= 10 * 1024**3, 'Need at least 10 GiB free on the runner.')
    with tempfile.TemporaryDirectory(prefix='homelab-packer-', dir=runtime_root) as directory:
        work = Path(directory)
        (work / 'seed').mkdir()
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'temporary-packer-build',
                        '-f', str(work / 'build-key')], check=True)
        password_hash = subprocess.run(['openssl', 'passwd', '-6', '-stdin'], input=secrets.token_urlsafe(48),
                                       text=True, capture_output=True, check=True).stdout.strip()
        (work / 'seed' / 'user-data').write_text(seed((work / 'build-key.pub').read_text(), password_hash))
        (work / 'seed' / 'meta-data').write_text(json.dumps({'instance-id': f'packer-{identifier}-{secrets.token_hex(8)}'}))
        revision = os.environ.get('GITHUB_SHA', 'local')
        require(bool(re.fullmatch(r'[A-Za-z0-9-]+', revision)), 'Invalid source revision.')
        name = f'ubuntu-2404-{identifier}-{revision[:8]}'
        variables = {'api_url': api.url, 'token_id': os.environ['PACKER_TOKEN_ID'], 'vm_id': identifier,
                     'template_name': name, 'build_directory': directory,
                     'existing_iso': existing, 'source_revision': revision}
        varfile = work / 'build.pkrvars.json'
        varfile.write_text(json.dumps(variables))
        env = os.environ.copy()
        env['PKR_VAR_token_secret'] = env.pop('PACKER_TOKEN_SECRET')
        env.pop('PROXMOX_CA_PEM', None)
        env.pop('PACKER_LOG_PATH', None)
        env['PACKER_LOG'] = '0'
        env['CHECKPOINT_DISABLE'] = '1'
        env['PACKER_CACHE_DIR'] = str(work / 'cache')
        env['TMPDIR'] = directory
        if ca:
            # Keep public CA roots for Ubuntu/plugin downloads as well as the local CA.
            cafile = work / 'ca-bundle.crt'
            roots = ssl.get_default_verify_paths().cafile
            require(roots and Path(roots).is_file(), 'Cannot find system CA bundle for Packer.')
            cafile.write_text(Path(roots).read_text() + '\n' + ca)
            env['SSL_CERT_FILE'] = str(cafile)
        run(['packer', 'init', str(ROOT)], env)
        run(['packer', 'validate', '-var-file=' + str(varfile), str(ROOT)], env)
        if mode == 'preflight':
            print('Preflight passed: no Proxmox resources changed. Write permissions/installer behavior not tested.')
            return
        # Recheck immediately before Packer's first write. No -force or automatic VM replacement.
        require(int(api.get(f'/cluster/nextid?vmid={identifier}')) == identifier, 'VM ID is now occupied.')
        run(['packer', 'build', '-on-error=cleanup', '-var-file=' + str(varfile), str(ROOT)], env)
        verify_template(api, config, identifier, name)
        print(f'Template verified: node={config["node"]}, VMID={identifier}, name={name}')
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a') as stream:
                stream.write(f'### Ubuntu template built\n\nVM ID: `{identifier}`; name: `{name}`.\n'
                             'Guest checks and API template checks passed. Clone boot test is still required.\n')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        main()
    except (BuildError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Build interrupted. Inspect Proxmox for incomplete VMs/generated seed ISOs before retrying.', file=sys.stderr)
        sys.exit(130)
