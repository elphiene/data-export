# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Ink Density Tool.

Build:
    pyinstaller build.spec

Output: dist/InkDensityTool.exe
"""

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle the assets directory so runner.jsx and template.xlsx
        # are available inside the frozen exe at runtime.
        ("assets", "assets"),
    ],
    hiddenimports=[
        "openpyxl",
        "pypdf",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="InkDensityTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # uncomment and add icon.ico if desired
)
