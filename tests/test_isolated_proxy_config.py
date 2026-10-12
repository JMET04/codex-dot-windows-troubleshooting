import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('isolated_proxy_config', Path(__file__).resolve().parents[1] / 'scripts/isolated_proxy_config.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class IsolatedProxyConfigTests(unittest.TestCase):
    def setUp(self):
        self.node = {'name': 'existing-test-node', 'type': 'ss', 'server': 'proxy.example.invalid', 'port': 443, 'cipher': 'aes-128-gcm', 'password': 'synthetic-password', 'plugin-opts': {'host': 'proxy.example.invalid'}}

    def test_listener_is_loopback_and_all_system_capture_is_disabled(self):
        result = MODULE.build_config(self.node, 18123)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['bind-address'], '127.0.0.1')
        self.assertFalse(result['allow-lan'])
        self.assertFalse(result['tun']['enable'])
        self.assertFalse(result['dns']['enable'])
        self.assertEqual(result['external-controller'], '')

    def test_only_fixed_targets_are_routed_and_other_hosts_rejected(self):
        result = MODULE.build_config(self.node, 18123)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['rules'], ['DOMAIN,chatgpt.com,probe-node', 'DOMAIN,codex-cloud-backend.chatgpt.com,probe-node', 'MATCH,REJECT'])
        self.assertNotIn('proxy-providers', result)
        self.assertNotIn('rule-providers', result)

    def test_existing_node_is_deep_copied(self):
        original = copy.deepcopy(self.node)
        result = MODULE.build_config(self.node, 18123)
        self.assertIsInstance(result, dict)
        result['proxies'][0]['plugin-opts']['host'] = 'changed.invalid'
        self.assertEqual(self.node, original)

    def test_invalid_or_privileged_listener_ports_are_rejected(self):
        for port in (0, 443, 65536, True, '18123'):
            with self.subTest(port=port), self.assertRaises(ValueError):
                MODULE.build_config(self.node, port)

    def test_unresolved_dependency_is_rejected(self):
        self.node['dialer-proxy'] = 'another-node'
        with self.assertRaises(ValueError):
            MODULE.build_config(self.node, 18123)

    def test_incomplete_node_is_rejected(self):
        for field in ('type', 'server', 'port'):
            node = copy.deepcopy(self.node)
            del node[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                MODULE.build_config(node, 18123)

if __name__ == '__main__':
    unittest.main()
