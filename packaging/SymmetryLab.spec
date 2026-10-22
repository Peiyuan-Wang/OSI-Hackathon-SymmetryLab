# PyInstaller spec: SymmetryLab desktop app. Build with scripts/build_mac_app.sh (macOS)
# or `pyinstaller --noconfirm packaging/SymmetryLab.spec`. SYMMETRYLAB_LITE=1 leaves out PhysBERT.
import importlib.util
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = os.path.abspath(os.path.join(SPECPATH, '..'))
physics = os.environ.get('SYMMETRYLAB_LITE') != '1' and importlib.util.find_spec('sentence_transformers') is not None
sys.path.insert(0, os.path.join(root, 'src'))
hidden = collect_submodules('symmetrylab') + ['webview']
# The interface files (HTML/CSS/JS) are read from symmetrylab/web/static at runtime.
datas = [(os.path.join(root, 'src', 'symmetrylab', 'web', 'static'), os.path.join('symmetrylab', 'web', 'static'))]
excludes = ['tkinter', 'matplotlib', 'IPython', 'notebook', 'pytest', 'playwright']
if sys.platform == 'darwin':
    excludes += ['gi', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qtpy']
if physics:
    hidden += ['sentence_transformers']
    for pkg in ('torch', 'transformers', 'tokenizers', 'huggingface-hub', 'safetensors', 'sentence-transformers', 'scikit-learn', 'tqdm', 'regex', 'requests', 'packaging', 'filelock', 'numpy', 'pyyaml'):
        try:
            datas += copy_metadata(pkg)
        except Exception:
            pass
else:
    excludes += ['torch', 'transformers', 'sentence_transformers', 'tokenizers', 'sklearn', 'scipy']

a = Analysis([os.path.join(SPECPATH, 'launch.py')], pathex=[os.path.join(root, 'src')], datas=datas,
             hiddenimports=hidden, excludes=excludes, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SymmetryLab', console=False,
          icon=os.path.join(SPECPATH, 'icon.png'), argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, name='SymmetryLab')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='SymmetryLab.app', icon=os.path.join(SPECPATH, 'icon.png'), bundle_identifier='local.symmetrylab.workbench',
                 info_plist={'CFBundleName': 'SymmetryLab', 'CFBundleDisplayName': 'SymmetryLab',
                             'CFBundleShortVersionString': '0.3.0', 'CFBundleVersion': '0.3.0',
                             'NSHighResolutionCapable': True, 'LSMinimumSystemVersion': '11.0',
                             'NSAppTransportSecurity': {'NSAllowsLocalNetworking': True}})
