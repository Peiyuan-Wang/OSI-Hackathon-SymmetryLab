"""Exercise frozen resources and exact tools without a display or model credentials."""
import json
from pathlib import Path
from urllib.request import build_opener, ProxyHandler
from symmetrylab.agent_core.workbench import run_agent


def check(server, root, destination):
    opener = build_opener(ProxyHandler({}))
    base = f'http://127.0.0.1:{server.server_port}'
    for route in ('/', '/experiment', '/papers', '/connection', '/app.js'):
        with opener.open(base + route, timeout=10) as response:
            if response.status != 200 or not response.read():
                raise RuntimeError('Frozen resource unavailable: ' + route)
    result = run_agent('Determine the MnPt Neel axis', Path(root) / 'smoke-run',
                       config={'research_profile': {'track': 'experiment', 'material': 'L10 MnPt', 'reuse_lessons': False}})
    if result['status'] != 'completed' or not all(c['certificate_verified'] for c in result['calculations']):
        raise RuntimeError('Frozen offline research failed')
    Path(destination).write_text(json.dumps({'status': 'passed', 'calculations': len(result['calculations']),
                                            'designs': len(result['experiment_designs'])}), encoding='utf-8')
