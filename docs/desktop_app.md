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

## Windows portable app and automated packages

Download the matching ZIP from the latest GitHub Release. Each package includes the
verified SSG catalog; builds fetch it from the `ssg-data-v0.1.5` data release and check
its SHA-256 before freezing the app.
The Windows artifact contains a ZIP: extract it completely, then double-click
`SymmetryLab/SymmetryLab.exe`. Keep `_internal` beside the executable. Python is bundled.
Windows 10/11 x64 needs Microsoft Edge WebView2 Runtime; install it from Microsoft's
WebView2 download page if absent. The preview is unsigned.

For Apple Silicon Macs, extract `SymmetryLab-macos-arm64.zip` and open `SymmetryLab.app`.
This architecture does not run on Intel Macs; build locally on Intel using the existing script.
The workflow archives the app with `ditto` to preserve its executable permissions.

Build on Windows with Python 3.12 installed:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows_app.ps1
# Optional large package including PhysBERT dependencies:
powershell -ExecutionPolicy Bypass -File scripts/build_windows_app.ps1 -Full
```

Pushes to main/review-fixes build the lightweight edition on native Windows and macOS runners.
Pushing a `v*` tag also publishes both tested ZIPs and their SHA-256 files as a GitHub Release.
Manual workflow dispatch can include PhysBERT dependencies. Lite builds retain exact research,
model connection, local UI and lexical paper ranking; PhysBERT requires a full build.
Packages contain code, interface assets, dependencies and the read-only SSG catalog. They
exclude API keys, local settings, paper history and research records. Configure Connection after
first launch.
Windows user data lives in `%APPDATA%\SymmetryLab`. Its saved key is plaintext protected by the account folder's inherited Windows permissions; POSIX mode 0600 applies only on Unix-like systems.

The workflow runs regression checks and launches each frozen executable with an isolated
`--smoke-test` directory. This checks packaged UI resources and completes an offline MnPt
calculation and experiment design. It does not certify native window rendering on every machine.
Artifacts include SHA256 files and are retained for 30 days. Full model weights are downloaded
on request and are not included in either archive.

## Workspace colors

Theory uses green, experimental research blue, Paper survey warm plum, and Connection settings warm copper. Each palette applies to the navigation and primary controls as well as the page background. Rebuild the desktop package after stylesheet changes; an older installed app keeps its bundled stylesheet.
