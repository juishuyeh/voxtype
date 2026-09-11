# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包設定：macOS 產生 VoxType.app，Windows 產生 VoxType.exe。

    uv run pyinstaller voxtype.spec --noconfirm
"""

import sys

MACOS = sys.platform == "darwin"

hiddenimports = [
    "keyring.backends.chainer",
    "keyring.backends.fail",
]
if MACOS:
    hiddenimports += ["pystray._darwin", "keyring.backends.macOS"]
else:
    hiddenimports += ["pystray._win32", "keyring.backends.Windows"]

a = Analysis(
    ["run_voxtype.py"],
    pathex=["src"],
    hiddenimports=hiddenimports,
    excludes=["numpy", "matplotlib", "pandas", "pytest", "PyInstaller"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VoxType",
    console=False,          # 不要黑色主控台視窗
    debug=False,
    strip=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="VoxType",
)

if MACOS:
    app = BUNDLE(
        coll,
        name="VoxType.app",
        bundle_identifier="com.jsyeh.voxtype",
        info_plist={
            "LSUIElement": True,  # 只待在 menu bar，不要 Dock 圖示
            "NSMicrophoneUsageDescription": "VoxType 需要麥克風才能把你說的話轉成文字。",
            "NSAppleEventsUsageDescription": "VoxType 用系統通知顯示狀態。",
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
