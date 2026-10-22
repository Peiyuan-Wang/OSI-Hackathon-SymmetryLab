# Desktop app

SymmetryLab ships as a native window (pywebview over the system web view: WKWebView on macOS) around the same interface, so the layout is identical to the browser version. A private loopback server on a random port serves the window; it is not reachable from other machines. There is no account or login.

## Build on macOS

```bash
cd ~/Desktop/HACKATHON/OSI-Hackathon-SymmetryLab
scripts/build_mac_app.sh          # all dependencies + PhysBERT (Apple Silicon), tests, dist/SymmetryLab.app
scripts/build_mac_app.sh --lite   # without PyTorch/PhysBERT (paper survey uses the offline lexicon)
scripts/build_mac_app.sh --deps-only
open dist/SymmetryLab.app
```

The script needs Python 3.11+ (`brew install python@3.12` if missing), reuses `.venv` when it works and recreates it otherwise, installs `requirements.lock`, `requirements-desktop.lock` and (unless `--lite`) `requirements-physics.lock`, runs the tests, downloads PhysBERT once (~440 MB, Hugging Face cache) and builds with PyInstaller from `packaging/SymmetryLab.spec`. Intel Macs build `--lite` automatically: PyTorch 2.14 has no Intel-macOS wheel. A full build is about 1.1 GB (PyTorch); `--lite` is about 120 MB.

The app is ad-hoc signed by PyInstaller, not notarized. It opens normally on the Mac that built it; if you copy it to another Mac, right-click → Open the first time.

Run without building: `.venv/bin/python -m symmetrylab.desktop`.

## Data

`~/Library/Application Support/SymmetryLab/`: `connection.json` (Base URL, model, protocol, API key; mode 0600, not encrypted), `workbench/` (runs, reports, lessons), `literature/` (paper survey), `webview/` (window storage). Override with `SYMMETRYLAB_HOME`. Runs made earlier with `symmetrylab serve` are in the project's `data/workbench`; copy them into `workbench/` to see them in the app.

## Window behaviour

Markdown/JSON/prompt downloads open a native Save dialog. Links to arXiv, DOIs and other sites open in the default browser. `--server-only` serves the interface without a window (used to verify frozen builds).

## Verified

Frozen Linux builds (lite and full) were started and driven in a browser: Connection save/test, offline experiment run, paper survey; the full build loaded PhysBERT and ranked live arXiv results. The macOS `.app` itself was not built here (no macOS in the build sandbox); `scripts/build_mac_app.sh` must be run on the Mac.
