# PyInstaller spec — one-dir build bundling the FastAPI backend + built React SPA.
# Build with scripts/build_release.ps1 (which builds frontend/dist first).
#
#   pip install -e ".[directml]" pyinstaller
#   cd frontend && npm ci && npm run build && cd ..
#   pyinstaller argos.spec --noconfirm

from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
    (str(ROOT / "models" / "registry.yaml"), "models"),
]

# onnxruntime / opencv ship native DLLs (incl. DirectML.dll) that must be collected.
binaries = collect_dynamic_libs("onnxruntime") + collect_dynamic_libs("cv2")

hiddenimports = (
    collect_submodules("argos")
    + collect_submodules("uvicorn")
    + ["sse_starlette", "paho.mqtt.client", "anyio"]
)

a = Analysis(
    ["run.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["torch", "matplotlib", "tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Argos",
    console=True,       # console shows the API key + logs
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Argos",
)
