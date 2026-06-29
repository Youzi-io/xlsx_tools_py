#!/usr/bin/env python3
"""
XLSX 复杂表头分析工具 — 程序入口。

本地桌面应用，用于分析带有复杂表头（多行表头、合并单元格）的 xlsx 文件。
支持 SQL 查询、可视化条件构建、统计分析和图表展示。

用法:
    python main.py                          # 启动 GUI
    python main.py --file data.xlsx         # 启动并直接加载文件
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("XLSX 复杂表头分析工具")
    app.setOrganizationName("XlsxTools")

    # 高 DPI 支持
    try:
        app.setStyle("Fusion")
    except Exception:
        pass

    window = MainWindow()
    window.show()

    # 如果命令行指定了文件，自动加载
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "--file" and len(sys.argv) > sys.argv.index(arg) + 1:
                filepath = sys.argv[sys.argv.index(arg) + 1]
                if os.path.exists(filepath):
                    window._load_file(filepath)
                break
            elif arg.endswith(".xlsx") and os.path.exists(arg):
                window._load_file(arg)
                break

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
