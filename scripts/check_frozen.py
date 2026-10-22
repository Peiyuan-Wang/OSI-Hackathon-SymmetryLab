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
    subprocess.run([sys.argv[1], '--smoke-test', str(result)], env=env, check=True, timeout=120)
    report = json.loads(result.read_text())
    assert report['status'] == 'passed' and report['calculations'] > 0 and report['designs'] > 0
    print(json.dumps(report))
