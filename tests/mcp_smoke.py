"""MCP protocol smoke test.

    python tests/mcp_smoke.py <some-project.vpp>

Checks the handshake, the tool list and two read-only calls. Exits 0 on
success; every failed assertion is printed.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(project):
    proc = subprocess.Popen([sys.executable, '-m', 'vpce', 'mcp'],
                            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1)

    def send(payload):
        proc.stdin.write(json.dumps(payload) + '\n')
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    problems = []

    init = send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                 'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                            'clientInfo': {'name': 'smoke', 'version': '0'}}})
    if 'result' not in init or init['result']['serverInfo']['name'] != 'vpce':
        problems.append('initialize: %s' % init)

    proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
    proc.stdin.flush()

    tools = send({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
    names = [t['name'] for t in tools.get('result', {}).get('tools', [])]
    for required in ('vp_status', 'vp_project_summary', 'vp_draw', 'vp_export_images'):
        if required not in names:
            problems.append('missing tool %s (got %s)' % (required, names))

    status = send({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                   'params': {'name': 'vp_status', 'arguments': {}}})
    info = json.loads(status['result']['content'][0]['text'])
    if not os.path.isdir(info['home']):
        problems.append('vp_status home invalid: %s' % info['home'])

    summary = send({'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call',
                    'params': {'name': 'vp_project_summary',
                               'arguments': {'project': project}}})
    payload = json.loads(summary['result']['content'][0]['text'])
    if 'diagrams' not in payload or 'types' not in payload:
        problems.append('summary shape: %s' % payload)

    bad = send({'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call',
                'params': {'name': 'nope', 'arguments': {}}})
    if 'error' not in bad:
        problems.append('unknown tool should be a JSON-RPC error: %s' % bad)

    proc.stdin.close()
    proc.wait(timeout=20)
    err = proc.stderr.read()
    if err.strip():
        problems.append('stderr: %s' % err.strip()[:400])

    if problems:
        print('FAIL')
        for problem in problems:
            print(' -', problem)
        return 1
    print('OK  tools=%d  home=%s' % (len(names), info['home']))
    print('    summary: %s elements, %s diagrams'
          % (payload['model_elements'], len(payload['diagrams'])))
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
