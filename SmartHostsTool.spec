# -*- mode: python ; coding: utf-8 -*-

import sys
import os

# 获取项目根目录
try:
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    PROJECT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

a = Analysis(
    [os.path.join(PROJECT_DIR, 'main_modern.py')],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[
        (os.path.abspath('头像.jpg'), '.'),
        (os.path.abspath('presets.json'), '.'),
        (os.path.abspath('icon.ico'), '.'),
        (os.path.abspath('utils.py'), '.'),
        (os.path.abspath('ui_components.py'), '.')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmartHostsTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SmartHostsTool',
)
