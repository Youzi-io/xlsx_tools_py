"""
打包构建脚本 — 支持多个目标平台。

用法:
    python build.py win64        # Windows 10+ 64位 (当前环境直接打包)
    python build.py win7-64      # Windows 7+  64位 (需 Python 3.8 64位)
    python build.py win7-32      # Windows 7+  32位 (需 Python 3.8 32位)
    python build.py all          # 全部打包 (需各版本 Python 已安装)

环境要求:
    - win64:      任意 Python 3.9+ 64位 + PyQt5
    - win7-64:    必须 Python 3.8.x 64位 + PyQt5 (最后支持 Win7 的版本)
    - win7-32:    必须 Python 3.8.x 32位 + PyQt5

打包结果在 dist/ 目录下。
"""

import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
SPEC = os.path.join(ROOT, "build.spec")


def check_python():
    """检查当前 Python 版本。"""
    v = sys.version_info
    is_64bit = sys.maxsize > 2**32
    bit = "64位" if is_64bit else "32位"
    print(f"当前 Python: {v.major}.{v.minor}.{v.micro} {bit}")
    return v, is_64bit


def clean():
    """清理上次构建产物。"""
    dirs = ["build", "dist", "__pycache__"]
    for d in dirs:
        path = os.path.join(ROOT, d)
        if os.path.exists(path):
            shutil.rmtree(path)
    for root, dirs, files in os.walk(ROOT):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    print("清理完成")


def ensure_deps():
    """确保依赖已安装。"""
    req = os.path.join(ROOT, "requirements.txt")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("依赖就绪")


def build_exe(name_suffix="", extra_pyi_args=None):
    """
    执行 PyInstaller 打包。

    动态生成一个带 name 的临时 spec 文件，避免参数冲突。
    """
    # 读取原始 spec，替换 name 参数
    spec_content = open(SPEC, "r", encoding="utf-8").read()
    exe_name = f"xlsx_tools{name_suffix}"
    spec_content = spec_content.replace(
        "name='xlsx_tools'",
        f"name='{exe_name}'"
    )

    tmp_spec = os.path.join(ROOT, f"_tmp_{exe_name}.spec")
    with open(tmp_spec, "w", encoding="utf-8") as f:
        f.write(spec_content)

    args = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(tmp_spec),
    ]
    if extra_pyi_args:
        args.extend(extra_pyi_args)

    print(f"打包命令: {' '.join(args)}")
    try:
        subprocess.check_call(args, cwd=ROOT)
    finally:
        # 清理临时 spec
        if os.path.exists(tmp_spec):
            os.remove(tmp_spec)

    # 显示结果
    exe_path = os.path.join(DIST, f"{exe_name}.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n打包成功: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"\n打包失败，未找到: {exe_path}")


def build_win64():
    """Windows 10+ 64位 — 当前环境直接打包。"""
    print("\n" + "=" * 60)
    print("打包目标: Windows 10+ 64位")
    print("=" * 60)

    v, is_64bit = check_python()
    if not is_64bit:
        print("错误: 需要 64位 Python")
        return
    if v < (3, 9):
        print("警告: Python < 3.9 也会打包为 Win10+ exe，Win7 用户请用 win7-64 目标")

    clean()
    ensure_deps()
    build_exe(name_suffix="-win64")


def build_win7_64():
    """Windows 7+ 64位 — 必须用 Python 3.8 64位。"""
    print("\n" + "=" * 60)
    print("打包目标: Windows 7+ 64位")
    print("要求: Python 3.8.x 64位")
    print("=" * 60)

    v, is_64bit = check_python()

    if v.major != 3 or v.minor > 8:
        print(f"\n错误: 当前 Python {v.major}.{v.minor} 不支持 Win7")
        print("请用 Python 3.8.x 64位 执行此命令")
        print("下载: https://www.python.org/downloads/release/python-3810/")
        print("     选择: python-3.8.10-amd64.exe")
        return

    if not is_64bit:
        print("错误: 需要 64位 Python")
        return

    clean()
    ensure_deps()
    build_exe(name_suffix="-win7-64")


def build_win7_32():
    """Windows 7+ 32位 — 必须用 Python 3.8 32位。"""
    print("\n" + "=" * 60)
    print("打包目标: Windows 7+ 32位")
    print("要求: Python 3.8.x 32位")
    print("=" * 60)

    v, is_64bit = check_python()

    if v.major != 3 or v.minor > 8:
        print(f"\n错误: 当前 Python {v.major}.{v.minor} 不支持 Win7")
        print("请用 Python 3.8.x 32位 执行此命令")
        print("下载: https://www.python.org/downloads/release/python-3810/")
        print("     选择: python-3.8.10.exe (32-bit installer)")
        return

    if is_64bit:
        print("错误: 需要 32位 Python")
        return

    clean()
    ensure_deps()
    build_exe(name_suffix="-win7-32")


def build_all():
    """打包所有目标 — 依次调用各 Python 版本。"""
    print("\n" + "=" * 60)
    print("打包所有目标")
    print("=" * 60)

    # 需要手动指定各版本 Python 路径
    python_paths = {
        "win64": sys.executable,           # 当前 Python
        "win7-64": r"C:\Python38-64\python.exe",   # ← 改成你的路径
        "win7-32": r"C:\Python38-32\python.exe",   # ← 改成你的路径
    }

    for target, py_path in python_paths.items():
        if not os.path.exists(py_path):
            print(f"跳过 {target}: Python 不存在 ({py_path})")
            continue
        print(f"\n--- {target} ---")
        subprocess.check_call([py_path, __file__, target])


USAGE = """
用法:
    python build.py win64        # Windows 10+ 64位 (当前环境)
    python build.py win7-64      # Windows 7  64位 (需 Python 3.8 64位)
    python build.py win7-32      # Windows 7  32位 (需 Python 3.8 32位)
    python build.py all          # 全部 (需配置各 Python 路径)
    python build.py clean        # 仅清理构建产物
"""

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else ""

    if target == "win64":
        build_win64()
    elif target == "win7-64":
        build_win7_64()
    elif target == "win7-32":
        build_win7_32()
    elif target == "all":
        build_all()
    elif target == "clean":
        clean()
    else:
        print(USAGE)
