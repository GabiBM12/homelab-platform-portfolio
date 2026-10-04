import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildTests(unittest.TestCase):
    def test_id_validation(self):
        self.assertEqual(build.vm_id('9000'), 9000)
        for invalid in ('99', '0', '9000;id', '-1', '1000000000', '9e3'):
            with self.assertRaises(build.BuildError):
                build.vm_id(invalid)

    def test_seed(self):
        value = json.loads(build.seed('ssh-ed25519 PUBLIC', '$6$HASH').split('\n', 1)[1])['autoinstall']
        self.assertFalse(value['ssh']['allow-pw'])
        self.assertEqual(value['ssh']['authorized-keys'], ['ssh-ed25519 PUBLIC'])
        self.assertIn('qemu-guest-agent', value['packages'])
        self.assertEqual(value['identity']['password'], '$6$HASH')

    def test_iso_reuse_requires_consent_and_size(self):
        config = json.loads((ROOT / 'build.json').read_text())
        entry = {'volid': 'local:iso/' + config['iso_filename'], 'size': config['iso_size']}
        self.assertEqual(build.choose_iso([], config, False), '')
        with self.assertRaises(build.BuildError):
            build.choose_iso([entry], config, False)
        self.assertEqual(build.choose_iso([entry], config, True), entry['volid'])
        entry['size'] = 1
        with self.assertRaises(build.BuildError):
            build.choose_iso([entry], config, True)

    def test_no_insecure_or_credentialed_api_url(self):
        for url in ('http://pve/api2/json', 'https://user:pass@pve/api2/json', 'https://pve/api2/json?token=x'):
            with self.assertRaises(build.BuildError):
                build.API(url, 'packer@pve!image-build', 'secret')

    def test_verification_rejects_non_template(self):
        class FakeAPI:
            def get(self, path):
                return {'name': 'test', 'template': 0}
        with self.assertRaises(build.BuildError):
            build.verify_template(FakeAPI(), {'node': 'pve'}, 9000, 'test')

    def test_preflight_stops_at_occupied_id(self):
        class FakeAPI:
            def get(self, path):
                if path == '/version':
                    return {'version': 'test'}
                if path == '/cluster/nextid?vmid=9000':
                    raise build.BuildError('occupied')
                raise AssertionError('Should not proceed after occupied ID')
        with self.assertRaisesRegex(build.BuildError, 'occupied'):
            build.preflight(FakeAPI(), {}, 9000, False)

    def test_verify_template_success_and_attached_media_rejection(self):
        class FakeAPI:
            data = {'name': 'test', 'template': 1, 'scsi0': 'local-lvm:base-9000-disk-0',
                    'ide2': 'local-lvm:vm-9000-cloudinit,media=cdrom'}

            def get(self, path):
                return self.data
        api = FakeAPI()
        config = {'node': 'pve', 'disk_storage': 'local-lvm'}
        build.verify_template(api, config, 9000, 'test')
        api.data['ide0'] = 'local:iso/seed.iso,media=cdrom'
        with self.assertRaises(build.BuildError):
            build.verify_template(api, config, 9000, 'test')


if __name__ == '__main__':
    unittest.main()
