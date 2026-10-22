"""Run the frozen diagnostic in isolated temporary storage; no private data is read."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix='symmetrylab-package-') as folder:
    result = Path(folder) / 'result.json'
    env = dict(os.environ, SYMMETRYLAB_HOME=str(Path(folder) / 'data'))
    if '--require-ssg' in sys.argv[2:]:
        env['SYMMETRYLAB_REQUIRE_SSG'] = '1'
    env.pop('SYMMETRYLAB_SSG_CATALOG', None)  # the frozen app must use its bundled copy
    subprocess.run([sys.argv[1], '--smoke-test', str(result)], env=env, check=True, timeout=180)
    report = json.loads(result.read_text())
    assert report['status'] == 'passed' and report['calculations'] > 0 and report['designs'] > 0
    assert report['bond']['adapter_imported'] and report['bond']['ui_available']
    if '--require-ssg' in sys.argv[2:]:
        assert report['ssg']['bundled'] and report['ssg']['verification'] == 'verified'
    print(json.dumps(report))
