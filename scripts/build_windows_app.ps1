# Build a portable Windows x64 application using Python 3.12.
param([switch]$Full)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
function Invoke-Checked { & $args[0] $args[1..($args.Length-1)]; if ($LASTEXITCODE -ne 0) { throw "Command failed: $($args[0])" } }
if (!(Test-Path '.venv/Scripts/python.exe')) { Invoke-Checked py -3.12 -m venv .venv }
$python = (Resolve-Path '.venv/Scripts/python.exe').Path
Invoke-Checked $python -m pip install -r requirements.lock -r requirements-desktop.lock
if ($Full) { Invoke-Checked $python -m pip install -r requirements-physics.lock }
Invoke-Checked $python -m pip install --no-build-isolation --no-deps -e .
$env:SYMMETRYLAB_LITE = if ($Full) { '0' } else { '1' }
Invoke-Checked $python -m PyInstaller --noconfirm --clean --distpath dist --workpath build/pyinstaller packaging/SymmetryLab.spec
Write-Host 'Built dist/SymmetryLab/SymmetryLab.exe. Keep the entire folder together.'
