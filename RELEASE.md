# Building a release

Argos ships as a **Windows installer** (or a portable ZIP): the FastAPI backend + the built React
SPA bundled into one binary via PyInstaller, wrapped by Inno Setup. The installed app runs as one
process and opens the UI in your browser.

## Prerequisites (one-time)

```powershell
# Python 3.12+ with the app + build tools
python -m venv .venv; .venv\Scripts\activate
pip install -e ".[directml]" pyinstaller

# Node 18+ (frontend build) — https://nodejs.org
# Inno Setup 6 (installer)
winget install JRSoftware.InnoSetup
```

`ffmpeg` is a **runtime** dependency (RTSP decode + MJPEG live view). It is *not* bundled — the
installer notes it, and users install it with `winget install Gyan.FFmpeg`.

## Build

```powershell
pwsh scripts\build_release.ps1
```

This:
1. builds `frontend/dist` (`npm run build`),
2. runs PyInstaller (`argos.spec`) → `dist/Argos/` (one-dir, includes onnxruntime + DirectML DLLs),
3. runs Inno Setup (`installer/argos.iss`) → `release/ArgosSetup-0.1.0.exe`
   (or, if Inno Setup isn't installed, a portable `release/Argos-portable-0.1.0.zip`).

## What the installer does

- Installs to `Program Files\Argos`.
- Start Menu (and optional desktop) shortcut, with working dir = `%LOCALAPPDATA%\Argos` (where the
  app writes its SQLite DB, crops, and `.env`) — the app is frozen-aware and never writes under
  Program Files.
- Optional Windows Firewall rule to expose the LAN port (8080) to other devices.
- Launches Argos; the console window prints the API key and the local URL.

## After install (end user)

1. `winget install Gyan.FFmpeg` (RTSP/live view).
2. Launch Argos → open the printed URL → paste the API key.
3. **Discovery** page → scan the LAN → add cameras (audits default passwords).
4. Export a detector model for the direct path (`scripts/export_yolo.py`) or point at Frigate.

## GitHub release (optional)

With a GitHub remote configured:

```powershell
gh release create v0.1.0 release\ArgosSetup-0.1.0.exe --title "Argos 0.1.0" --notes-file RELEASE_NOTES.md
```
