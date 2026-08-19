# Build a Windows release of Argos: frontend -> PyInstaller one-dir -> Inno Setup installer.
#
# Prerequisites (one-time):
#   - Python 3.12+, with:  pip install -e ".[directml]" pyinstaller
#   - Node 18+            (for the frontend build)
#   - Inno Setup 6        (winget install JRSoftware.InnoSetup)
#   - ffmpeg is a RUNTIME dependency (not bundled) — users install it separately.
#
# Usage:  pwsh scripts/build_release.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Building frontend" -ForegroundColor Cyan
Push-Location frontend
if (Test-Path package-lock.json) { npm ci } else { npm install }
npm run build
Pop-Location

Write-Host "==> Building backend binary (PyInstaller)" -ForegroundColor Cyan
python -m PyInstaller argos.spec --noconfirm --clean

Write-Host "==> Building installer (Inno Setup)" -ForegroundColor Cyan
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (Test-Path $iscc) {
  & $iscc "installer\argos.iss"
  Write-Host "==> Installer written to release\" -ForegroundColor Green
} else {
  Write-Host "Inno Setup not found — skipping installer. Producing a portable ZIP instead." -ForegroundColor Yellow
  New-Item -ItemType Directory -Force -Path release | Out-Null
  Compress-Archive -Path dist\Argos\* -DestinationPath release\Argos-portable-0.1.0.zip -Force
  Write-Host "==> Portable ZIP written to release\Argos-portable-0.1.0.zip" -ForegroundColor Green
}
