"""
Win7 兼容打包 — 使用 Nuitka 编译为原生 exe（不依赖 Python 运行时）。

Nuitka 把 Python 代码编译成 C++，再链接为原生 Windows exe，
能直接运行在 Win7 上，不需要额外的 dll 或运行时。

前置条件（一次性）:
  1. 安装 Visual Studio 2022 Build Tools (只需 C++ 编译器)
     https://visualstudio.microsoft.com/visual-cpp-build-tools/
     安装时勾选: "C++桌面开发" (MSVC v143, Windows 11 SDK)

  2. 安装 Python 3.8 32位 (已有则跳过)

用法:
  1. 先装依赖 (联网):
     python38_32 -m pip install -r requirements.txt
     python38_32 -m pip install nuitka ordered-set zstandard

  2. 打包:
     python38_32 build_win7_nuitka.py

  产物: dist/xlsx_tools-win7-32.exe (原生exe, 可直接在Win7 32位运行)
"""

import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")


def build():
    print("=" * 60)
    print("Nuitka 原生编译打包 (Win7 兼容)")
    print("Python: {} {} {}".format(
        sys.version_info.major, sys.version_info.minor,
        "32位" if sys.maxsize <= 2**32 else "64位"
    ))
    print("=" * 60)

    arch = "32" if sys.maxsize <= 2**32 else "64"

    # 清理
    for d in ["build", DIST]:
        p = os.path.join(ROOT, d)
        if os.path.exists(p):
            shutil.rmtree(p)
    os.makedirs(DIST, exist_ok=True)

    # Nuitka 编译命令
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--windows-disable-console",
        "--enable-plugin=pyside2",          # PyQt5 兼容
        "--include-package=src",
        "--include-package=src.core",
        "--include-package=src.gui",
        "--include-package=src.utils",
        "--include-package=openpyxl",
        "--include-package=pandas",
        "--include-package=duckdb",
        "--include-package=PyQt5",
        "--include-data-dir=" + os.path.join(ROOT, "src") + "=src",
        "--output-dir=" + os.path.join(ROOT, "build"),
        "--output-filename=xlsx_tools-win7-{}".format(arch),
        "--assume-yes-for-downloads",
        os.path.join(ROOT, "main.py"),
    ]

    print("编译中 (可能需要 5-15 分钟)...")
    print(" ".join(cmd))
    subprocess.check_call(cmd, timeout=1800, cwd=ROOT)

    # Nuitka 输出在 build/main.dist/
    src_exe = os.path.join(ROOT, "build", "main.dist", "main.exe")
    dst_exe = os.path.join(DIST, "xlsx_tools-win7-{}.exe".format(arch))
    if os.path.exists(src_exe):
        shutil.copy2(src_exe, dst_exe)
        # 也复制依赖 dll
        for f in os.listdir(os.path.dirname(src_exe)):
            if f.endswith(".dll"):
                shutil.copy2(
                    os.path.join(os.path.dirname(src_exe), f),
                    os.path.join(DIST, f)
                )
        size_mb = os.path.getsize(dst_exe) / (1024 * 1024)
        print("\n打包成功: {} ({:.1f} MB)".format(dst_exe, size_mb))
        print("注意: 运行时需要同目录下的 dll 文件一起分发")
    else:
        print("\n打包失败: 未找到编译产物")


if __name__ == "__main__":
    build()
