"""Build a loopback-only probe configuration from one existing proxy node."""
import copy


def build_config(node, port):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Listener must use a nonprivileged TCP port')
    if not isinstance(node, dict):
        raise ValueError('Expected one existing proxy node')
    if any(not isinstance(node.get(key), str) or not node[key] for key in ('type', 'server')):
        raise ValueError('Incomplete existing node')
    if type(node.get('port')) is not int or not 1 <= node['port'] <= 65535:
        raise ValueError('Invalid existing node port')
    if 'dialer-proxy' in node:
        raise ValueError('Referenced upstream nodes are outside this isolated probe')
    selected = copy.deepcopy(node)
    selected['name'] = 'probe-node'
    return {
        'mixed-port': port, 'bind-address': '127.0.0.1', 'allow-lan': False,
        'mode': 'rule', 'log-level': 'silent', 'ipv6': False,
        'find-process-mode': 'off', 'external-controller': '',
        'tun': {'enable': False}, 'dns': {'enable': False},
        'proxies': [selected],
        'rules': ['DOMAIN,chatgpt.com,probe-node',
                  'DOMAIN,codex-cloud-backend.chatgpt.com,probe-node',
                  'MATCH,REJECT'],
    }
