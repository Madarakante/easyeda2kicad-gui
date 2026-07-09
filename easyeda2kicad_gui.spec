# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the EasyEDA2KiCad GUI (one-folder, windowed).
# Build with:  python -m PyInstaller easyeda2kicad_gui.spec --noconfirm

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Only Windows uses the .ico here; macOS expects .icns and Linux ignores it.
APP_ICON = "app.ico" if sys.platform.startswith("win") else None

# Bundle easyeda2kicad fully: its data files (default footprint/3d templates),
# submodules, and any hidden imports it pulls in.
e2k_datas, e2k_binaries, e2k_hidden = collect_all("easyeda2kicad")

hiddenimports = list(set(e2k_hidden + collect_submodules("easyeda2kicad")))

a = Analysis(
    ["easyeda2kicad_gui.py"],
    pathex=[],
    binaries=e2k_binaries,
    datas=e2k_datas + [("app.ico", "."), ("app.png", ".")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EasyEDA2KiCad",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed app, no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=APP_ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="EasyEDA2KiCad",   # -> dist/EasyEDA2KiCad/EasyEDA2KiCad.exe
)
