# -*- mode: python ; coding: utf-8 -*-
import sys, os
_spec_dir = r"D:\code\project\ga\xlsx_tools"

a = Analysis(
    [os.path.join(_spec_dir, 'main.py')],
    pathex=[_spec_dir],
    binaries=[], datas=[],
    hiddenimports=[
        'openpyxl', 'pandas', 'duckdb', 'PyQt5.sip',
        'src', 'src.core', 'src.gui', 'src.utils',
        'src.core.xlsx_reader', 'src.core.header_detector', 'src.core.data_manager',
        'src.core.query_engine', 'src.core.stats_engine', 'src.core.db_store',
        'src.gui.main_window', 'src.gui.file_panel', 'src.gui.header_view',
        'src.gui.db_panel', 'src.gui.query_builder', 'src.gui.sql_editor',
        'src.gui.result_table', 'src.gui.export_dialog',
        'src.utils.merger', 'src.utils.formatter',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'http', 'xmlrpc', 'pydoc'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='xlsx_tools-win7-64',
    debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=True,
    icon=None,
)
