from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


root = Path(SPEC).parent
package = root / "src" / "paperflow"

a = Analysis(
    [str(package / "desktop.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(package / "static"), "paperflow/static")]
          + collect_data_files("pymupdf4llm")
          # pymupdf-layout loads its YAML and ONNX models by filesystem path at
          # runtime. PyInstaller cannot infer these non-Python resources from
          # the hidden import, so include the parent package's data explicitly.
          + collect_data_files("pymupdf"),
    hiddenimports=["pymupdf4llm", "pymupdf.layout", "webview.platforms.edgechromium"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "transformers", "tkinter", "IPython", "matplotlib", "pandas", "pytest", "ruff"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PaperFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(root / "branding" / "PaperFlow.ico"),
    version=str(root / "installer" / "version_info.txt"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PaperFlow",
)
