#!/usr/bin/env bash
# Install every dependency into .venv and build dist/SymmetryLab.app (macOS).
#   scripts/build_mac_app.sh            full build, includes PhysBERT on Apple Silicon
#   scripts/build_mac_app.sh --lite     no PyTorch/PhysBERT (smaller; paper survey uses the offline lexicon)
#   scripts/build_mac_app.sh --deps-only  install dependencies and run tests, no app build
set -euo pipefail
cd "$(dirname "$0")/.."
LITE=0; BUILD=1
for arg in "$@"; do case "$arg" in --lite) LITE=1;; --deps-only) BUILD=0;; *) echo "unknown option $arg"; exit 2;; esac; done
[[ "$(uname -s)" == "Darwin" ]] || { echo "This script builds the macOS app. On Linux/Windows run PyInstaller with packaging/SymmetryLab.spec."; exit 2; }
if [[ "$(uname -m)" != "arm64" && $LITE == 0 ]]; then
  echo "Intel Mac: PyTorch 2.14 has no Intel-macOS wheel, building without PhysBERT (--lite)."; LITE=1
fi

PY=""
for c in python3.12 python3.13 python3.11 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then PY="$c"; break; fi
done
[[ -n "$PY" ]] || { echo "Python 3.11+ is required (e.g. brew install python@3.12)."; exit 2; }

# Reuse .venv only if it works from this folder (it breaks if the project folder was renamed).
if [[ -x .venv/bin/python ]] && ! .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "Existing .venv is unusable; recreating it."; rm -rf .venv
fi
[[ -x .venv/bin/python ]] || "$PY" -m venv .venv
V=.venv/bin/python

echo "==> Installing dependencies"
$V -m pip install --upgrade "pip==26.2.2" >/dev/null
$V -m pip install -r requirements.lock
$V -m pip install -r requirements-desktop.lock
[[ $LITE == 1 ]] || $V -m pip install -r requirements-physics.lock
$V -m pip install --no-build-isolation --no-deps --force-reinstall -e .

echo "==> Running tests"
$V -m pytest -q

if [[ $LITE == 0 ]]; then
  echo "==> Preparing PhysBERT (one-time download, about 440 MB)"
  $V -m symmetrylab.literature.encoders --download || echo "PhysBERT download failed; the app will offer 'Prepare PhysBERT' later."
fi

[[ $BUILD == 1 ]] || { echo "Dependencies installed. Run the app with: .venv/bin/python -m symmetrylab.desktop"; exit 0; }

echo "==> Building SymmetryLab.app"
rm -rf build/pyinstaller dist/SymmetryLab dist/SymmetryLab.app
SYMMETRYLAB_LITE=$LITE $V -m PyInstaller --noconfirm --clean --log-level WARN \
  --distpath dist --workpath build/pyinstaller packaging/SymmetryLab.spec
rm -rf dist/SymmetryLab   # the .app bundle contains everything
echo
echo "Built: $(pwd)/dist/SymmetryLab.app"
echo "Open it with: open dist/SymmetryLab.app   (or drag it to /Applications)"
echo "Data and the saved connection live in: ~/Library/Application Support/SymmetryLab"
