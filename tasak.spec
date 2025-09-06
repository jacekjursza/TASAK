# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for TASAK

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['tasak/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('README.md', '.'),
        ('tasak/templates', 'tasak/templates'),
    ],
    hiddenimports=[
        'tasak',
        'tasak.main',
        'tasak.config',
        'tasak.app_runner',
        'tasak.mcp_client',
        'tasak.mcp_remote_runner',
        'tasak.mcp_remote_pool',
        'tasak.curated_app',
        'tasak.python_plugins',
        'tasak.admin_commands',
        'tasak.init_command',
        'tasak.auth',
        'yaml',
        'importlib.metadata',
    ],
    hookspath=['pyinstaller-hooks'],
    hooksconfig={},
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
    name='tasak',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
