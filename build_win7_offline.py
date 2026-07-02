"""
Win7 离线打包 — 两步走：
  步骤1: 用主 Python (3.14) 下载所有 wheel (指定32或64位)
  步骤2: 用 Python 3.8 离线安装 + 打包

用法:
  python build_win7_offline.py download 32    # 下载32位wheel
  python build_win7_offline.py download 64    # 下载64位wheel
  python38_32 build_win7_offline.py build     # 32位打包
  python38_64 build_win7_offline.py build     # 64位打包 (需安装 Python 3.8 64位)
"""

import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
WHEEL_DIR = os.path.join(ROOT, "_wheels")
DIST_DIR = os.path.join(ROOT, "dist")

PACKAGES = [
    "PyQt5==5.15.9",
    "PyQt5-sip",
    "openpyxl==3.0.10",
    "pandas==1.5.3",
    "duckdb==0.8.1",
    "python-dateutil",
    "pytz",
    "six",
    "et-xmlfile",
    "numpy==1.24.4",
    "pyinstaller==4.10",
    "pyinstaller-hooks-contrib",
    "altgraph",
    "pywin32-ctypes",
    "importlib-metadata",
    "zipp",
]


def step_download(arch):
    """步骤1: 用主 Python 下载所有 wheel 到 _wheels/"""
    if os.path.exists(WHEEL_DIR):
        shutil.rmtree(WHEEL_DIR)
    os.makedirs(WHEEL_DIR, exist_ok=True)

    platform = "win_amd64" if arch == "64" else "win32"

    print("=" * 60)
    print("步骤1: 下载 wheel 文件 (目标: Python 3.8 {}位)".format(arch))
    print("主 Python: {} {}".format(sys.version_info.major, sys.version_info.minor))
    print("=" * 60)

    base_args = [
        sys.executable, "-m", "pip", "download",
        "--dest", WHEEL_DIR,
        "--python-version", "38",
        "--platform", platform,
        "--only-binary", ":all:",
    ]

    for pkg in PACKAGES:
        print("下载 {} ...".format(pkg))
        try:
            subprocess.check_call(base_args + [pkg])
        except Exception as e:
            print("  二进制下载失败, 尝试纯Python: {}".format(e))
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "download",
                    "--dest", WHEEL_DIR, pkg
                ])
            except Exception:
                print("  跳过")

    pure_pkgs = ["matplotlib==3.5.3", "cycler", "kiwisolver", "pyparsing",
                  "fonttools==4.38.0", "pillow==9.5.0", "packaging"]
    for pkg in pure_pkgs:
        print("下载 {} (纯Python) ...".format(pkg))
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "download",
                "--dest", WHEEL_DIR,
                "--python-version", "38",
                "--platform", platform,
                "--only-binary", ":all:",
                pkg
            ])
        except Exception:
            print("  跳过")

    wheels = [f for f in os.listdir(WHEEL_DIR) if f.endswith(".whl")]
    print("\n下载完成: {} 个文件 -> {}".format(len(wheels), WHEEL_DIR))
    print()
    py_cmd = "python38_64" if arch == "64" else "python38_32"
    print("接下来运行: {} build_win7_offline.py build".format(py_cmd))


def step_build():
    """步骤2: 用 Python 3.8 离线安装 + 打包"""
    print("=" * 60)
    print("步骤2: 离线安装 + 打包")
    print("当前 Python: {} {} {}".format(
        sys.version_info.major, sys.version_info.minor,
        "32位" if sys.maxsize <= 2**32 else "64位"
    ))
    print("=" * 60)

    if not os.path.exists(WHEEL_DIR):
        print("错误: _wheels/ 目录不存在，请先运行:")
        print("  python build_win7_offline.py download")
        return

    # 清理不兼容的 wheel + 去重（保留最新版本）
    arch = "64" if sys.maxsize > 2**32 else "32"
    keep_arch = "amd64" if arch == "64" else "win32"
    skip_arch = "win32" if arch == "64" else "amd64"

    wheels = [f for f in os.listdir(WHEEL_DIR) if f.endswith(".whl")]
    pkg_versions = {}  # pkg_name -> (version_str, filename)
    for w in wheels:
        wl = w.lower()
        # 纯 Python 包 (py3-none-any, py2.py3-none-any) 保留
        is_pure = ("none-any" in wl)
        # 移除不匹配架构的二进制包
        if not is_pure and skip_arch in wl:
            print("  移除{}位: {}".format("32" if arch == "64" else "64", w))
            os.remove(os.path.join(WHEEL_DIR, w))
            continue
        # 移除 cp3xx（非 cp38 且非 abi3）的包
        if "cp3" in wl and "cp38" not in wl and "abi3" not in wl:
            print("  移除不兼容: {}".format(w))
            os.remove(os.path.join(WHEEL_DIR, w))
            continue
        # 提取包名和版本用于去重
        parts = w.split("-")
        pkg_name = parts[0].lower()
        try:
            ver = parts[1]
        except IndexError:
            ver = "0"
        if pkg_name in pkg_versions:
            old_ver, old_name = pkg_versions[pkg_name]
            if ver > old_ver:
                print("  去重保留: {} (移除旧版 {})".format(w, old_name))
                os.remove(os.path.join(WHEEL_DIR, old_name))
                pkg_versions[pkg_name] = (ver, w)
            else:
                print("  去重移除: {} (已有新版)".format(w))
                os.remove(os.path.join(WHEEL_DIR, w))
        else:
            pkg_versions[pkg_name] = (ver, w)

    wheels = sorted([v[1] for v in pkg_versions.values()])
    print("可用 {} 个 wheel".format(len(wheels)))

    env = os.environ.copy()
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        env.pop(k, None)

    # 让 pip 自己从目录解析依赖
    print("安装 (离线) ...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install",
         "--no-index", "--find-links", WHEEL_DIR,
         "PyQt5", "openpyxl", "pandas", "duckdb", "matplotlib", "pyinstaller"],
        timeout=600, env=env
    )
    print("依赖安装完成")

    # 清理并打包
    for d in [os.path.join(ROOT, "build"), DIST_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)

    arch = "32" if sys.maxsize <= 2**32 else "64"
    spec_path = _generate_spec(arch)

    print("开始 PyInstaller 打包 (onefile 模式) ...")
    subprocess.check_call(
        [sys.executable, "-m", "PyInstaller",
         "--clean", "--noconfirm",
         "--distpath", DIST_DIR,
         "--workpath", os.path.join(ROOT, "build"),
         spec_path],
        timeout=1800, env=env
    )

    exe_name = "xlsx_tools-win7-{}.exe".format(arch)
    exe_path = os.path.join(DIST_DIR, exe_name)
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print("\n打包成功: {} ({:.1f} MB)".format(exe_path, size_mb))
    else:
        print("\n打包失败: {} 不存在".format(exe_path))


def _generate_spec(arch):
    spec = '''# -*- mode: python ; coding: utf-8 -*-
import sys, os
_spec_dir = r"{}"

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
    hookspath=[], hooksconfig={{}}, runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'http', 'xmlrpc', 'pydoc'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='xlsx_tools-win7-{}',
    debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=True,
    icon=None,
)
'''.format(ROOT, arch)
    spec_path = os.path.join(ROOT, "_tmp_win7.spec")
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec)
    return spec_path


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    arg2 = sys.argv[2] if len(sys.argv) > 2 else "32"
    if action == "download":
        step_download(arg2)
    elif action == "build":
        step_build()
    else:
        print("用法:")
        print("  python build_win7_offline.py download 64   # 下载64位依赖")
        print("  python build_win7_offline.py download 32   # 下载32位依赖")
        print("  python38_64 build_win7_offline.py build    # 64位打包")
        print("  python38_32 build_win7_offline.py build    # 32位打包")
