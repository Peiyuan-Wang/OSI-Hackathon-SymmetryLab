# Build a portable Windows x64 application using Python 3.12.
param([switch]$Full, [switch]$NoSsg)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
function Invoke-Checked { & $args[0] $args[1..($args.Length-1)]; if ($LASTEXITCODE -ne 0) { throw "Command failed: $($args[0])" } }
if (!(Test-Path '.venv/Scripts/python.exe')) { Invoke-Checked py -3.12 -m venv .venv }
$python = (Resolve-Path '.venv/Scripts/python.exe').Path
Invoke-Checked $python -m pip install -r requirements.lock -r requirements-desktop.lock
if ($Full) { Invoke-Checked $python -m pip install -r requirements-physics.lock }
Invoke-Checked $python -m pip install --no-build-isolation --no-deps -e .
$env:SYMMETRYLAB_LITE = if ($Full) { '0' } else { '1' }
$env:SYMMETRYLAB_BUNDLE_SSG = if ($NoSsg) { '0' } else { '1' }
if (!$NoSsg) {
  $catalog = 'data/ssg/SSGReciprocalOffline-0.1.5.sqlite'
  if (!(Test-Path $catalog)) { Invoke-Checked $python scripts/fetch_ssg_catalog.py }
  if (!(Test-Path $catalog)) { throw "Missing $catalog after download. Build with -NoSsg to omit it." }
  $expected = ((Get-Content 'data/ssg/manifest.json' -Raw | ConvertFrom-Json).files | Where-Object { $_.file -like '*.sqlite' }).sha256
  if ((Get-FileHash $catalog -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'SSG catalog hash mismatch with data/ssg/manifest.json' }
}
Invoke-Checked $python -m PyInstaller --noconfirm --clean --distpath dist --workpath build/pyinstaller packaging/SymmetryLab.spec
$check = @('scripts/check_frozen.py', 'dist/SymmetryLab/SymmetryLab.exe'); if (!$NoSsg) { $check += '--require-ssg' }
Invoke-Checked $python @check
Write-Host 'Built dist/SymmetryLab/SymmetryLab.exe. Keep the entire folder together.'
