"""
一键打包 Win7 兼容 exe。

原理:
  Python 3.9+ 生成的 exe 无法在 Win7 运行。
  所以需要临时下载 Python 3.8 嵌入版，装好依赖后用它的 PyInstaller 打包。

用法:
  python build_win7.py 64    # Win7 64位
  python build_win7.py 32    # Win7 32位
  python build_win7.py all   # 两种都打
"""

import subprocess
import sys
import os
import shutil
import urllib.request
import zipfile
import io

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "_py38_cache")

PY38_URLS = {
    "64": {
        "url": "https://www.python.org/ftp/python/3.8.10/python-3.8.10-embed-amd64.zip",
        "dir": "python38-64",
        "getpip": "https://bootstrap.pypa.io/pip/get-pip.py",
    },
    "32": {
        "url": "https://www.python.org/ftp/python/3.8.10/python-3.8.10-embed-win32.zip",
        "dir": "python38-32",
        "getpip": "https://bootstrap.pypa.io/pip/get-pip.py",
    },
}


def download(url, dest):
    """下载文件，带进度。"""
    print(f"下载: {url}")
    print(f"保存: {dest}")
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as e:
        print(f"下载失败: {e}")
        print("请手动下载并放入 {} 目录".format(CACHE))
        raise


def setup_python38(arch):
    """下载并配置 Python 3.8 嵌入版。"""
    info = PY38_URLS[arch]
    py_dir = os.path.join(CACHE, info["dir"])
    python_exe = os.path.join(py_dir, "python.exe")

    if os.path.exists(python_exe):
        print(f"Python 3.8 {arch}位 已存在: {py_dir}")
        return python_exe, py_dir

    os.makedirs(CACHE, exist_ok=True)

    # 下载嵌入版
    zip_path = os.path.join(CACHE, f"python38-{arch}.zip")
    if not os.path.exists(zip_path):
        download(info["url"], zip_path)

    # 解压
    print(f"解压到: {py_dir}")
    os.makedirs(py_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(py_dir)

    # 嵌入版默认不搜索 site-packages，需要修改 python38._pth
    pth_file = os.path.join(py_dir, "python38._pth")
    if os.path.exists(pth_file):
        with open(pth_file, "r") as f:
            content = f.read()
        # 取消 import site 的注释
        if "#import site" in content:
            content = content.replace("#import site", "import site")
            with open(pth_file, "w") as f:
                f.write(content)
            print("已启用 site-packages")

    # 安装 pip
    getpip_path = os.path.join(CACHE, "get-pip.py")
    if not os.path.exists(getpip_path):
        download(info["getpip"], getpip_path)

    print("安装 pip ...")
    subprocess.check_call([python_exe, getpip_path, "--no-python-version-warning"],
                         cwd=py_dir)

    print(f"Python 3.8 {arch}位 就绪")
    return python_exe, py_dir


def build_win7(arch):
    """用 Python 3.8 打包 Win7 兼容 exe。"""
    print("\n" + "=" * 60)
    print(f"打包 Win7 {arch}位")
    print("=" * 60)

    python_exe, py_dir = setup_python38(arch)

    # 安装依赖
    print("安装依赖 (openpyxl, pandas, duckdb, PyQt5, pyinstaller) ...")
    deps = [
        "openpyxl==3.0.10",
        "pandas==1.5.3",
        "duckdb==0.8.1",
        "PyQt5==5.15.9",
        "pyinstaller==5.13.2",
    ]
    subprocess.check_call(
        [python_exe, "-m", "pip", "install", "--no-python-version-warning"] + deps,
        cwd=py_dir
    )

    # 生成打包 spec（用模板路径）
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import sys
import os
_spec_dir = r"{}"

a = Analysis(
    [os.path.join(_spec_dir, 'main.py')],
    pathex=[_spec_dir],
    binaries=[],
    datas=[],
    hiddenimports=[
        'openpyxl', 'pandas', 'duckdb', 'PyQt5.sip',
        'src', 'src.core', 'src.gui', 'src.utils',
        'src.core.xlsx_reader', 'src.core.header_detector', 'src.core.data_manager',
        'src.core.query_engine', 'src.core.stats_engine',
        'src.gui.main_window', 'src.gui.file_panel', 'src.gui.header_view',
        'src.gui.query_builder', 'src.gui.sql_editor', 'src.gui.result_table',
        'src.gui.export_dialog',
        'src.utils.merger', 'src.utils.formatter',
    ],
    hookspath=[], hooksconfig={{}}, runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'http', 'xmlrpc', 'pydoc'],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='xlsx_tools-win7-{}',
    debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=True,
    disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None,
    codesign_identity=None, entitlements_file=None, icon=None,
)
'''.format(ROOT, arch)

    spec_path = os.path.join(CACHE, f"build_win7_{arch}.spec")
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_content)

    # 清理上次构建
    build_dir = os.path.join(CACHE, "build")
    dist_dir = os.path.join(CACHE, "dist")
    for d in [build_dir, dist_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)

    # 打包
    print("开始 PyInstaller 打包 ...")
    args = [
        python_exe, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", build_dir,
        spec_path,
    ]
    print(" ".join(args))
    subprocess.check_call(args, cwd=py_dir)

    # 结果
    exe_name = f"xlsx_tools-win7-{arch}.exe"
    exe_path = os.path.join(ROOT, "dist", exe_name)
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n打包成功: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"\n打包失败: {exe_path} 不存在")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else ""

    if target in ("64", "32"):
        build_win7(target)
    elif target == "all":
        build_win7("64")
        build_win7("32")
    else:
        print("用法: python build_win7.py [64|32|all]")
        print("  64  - Win7 64位")
        print("  32  - Win7 32位")
        print("  all - 两种都打")
