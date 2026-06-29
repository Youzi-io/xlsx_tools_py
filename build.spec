# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置。

用法:
    pyinstaller build.spec

生成单一 .exe 文件，包含所有依赖。
"""

import sys
import os

# SPEC 是 PyInstaller 注入的变量，指向当前 spec 文件路径
_spec_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(_spec_dir, 'main.py')],
    pathex=[_spec_dir],
    binaries=[],
    datas=[
        # 不包含额外数据文件（matplotlib 字体等由 PyInstaller 自动处理）
    ],
    hiddenimports=[
        'openpyxl',
        'pandas',
        'duckdb',
        'matplotlib',
        'PyQt5.sip',
        'src',
        'src.core',
        'src.gui',
        'src.utils',
        'src.core.xlsx_reader',
        'src.core.header_detector',
        'src.core.data_manager',
        'src.core.query_engine',
        'src.core.stats_engine',
        'src.gui.main_window',
        'src.gui.file_panel',
        'src.gui.header_view',
        'src.gui.query_builder',
        'src.gui.sql_editor',
        'src.gui.result_table',
        'src.gui.export_dialog',
        'src.utils.merger',
        'src.utils.formatter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'http',
        'xmlrpc',
        'pydoc',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='xlsx_tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台窗口（方便查看日志）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可添加图标路径
)
