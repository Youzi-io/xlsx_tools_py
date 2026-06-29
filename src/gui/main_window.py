"""
主窗口框架 — 程序的顶层 GUI 容器。

布局结构:
┌──────────────┬──────────────────┐
│  左侧面板     │   中央/右侧区域   │
│  (文件+列)   │   (表头+查询+结果)│
└──────────────┴──────────────────┘
"""

import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QMenuBar, QMenu, QToolBar,
    QStatusBar, QMessageBox, QFileDialog, QAction,
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

from src.gui.file_panel import FilePanel
from src.gui.header_view import HeaderViewWidget
from src.gui.query_builder import QueryBuilderWidget
from src.gui.sql_editor import SqlEditorWidget
from src.gui.result_table import ResultTableWidget
from src.gui.export_dialog import ExportDialog
from src.core.data_manager import DataManager


class MainWindow(QMainWindow):
    """主窗口。"""

    APP_NAME = "XLSX 复杂表头分析工具"
    APP_VERSION = "1.0.0"

    def __init__(self):
        super().__init__()
        self._data_manager = DataManager()
        self._current_filepath = None

        self._init_ui()
        self._connect_signals()
        self._restore_window_state()

    # ── UI 初始化 ───────────────────────────────

    def _init_ui(self):
        self.setWindowTitle(self.APP_NAME)
        self.setMinimumSize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(4, 4, 4, 4)

        self._main_splitter = QSplitter(Qt.Horizontal)

        # --- 左侧面板 ---
        self._file_panel = FilePanel()
        self._header_view = HeaderViewWidget()

        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.addWidget(self._file_panel)
        left_splitter.addWidget(self._header_view)
        left_splitter.setStretchFactor(0, 1)
        left_splitter.setStretchFactor(1, 1)

        self._main_splitter.addWidget(left_splitter)

        # --- 右侧面板 ---
        right_splitter = QSplitter(Qt.Vertical)

        self._query_tabs = QTabWidget()
        self._sql_editor = SqlEditorWidget()
        self._query_builder = QueryBuilderWidget()
        self._query_tabs.addTab(self._sql_editor, "SQL 查询")
        self._query_tabs.addTab(self._query_builder, "条件构建器")

        right_splitter.addWidget(self._query_tabs)

        self._result_table = ResultTableWidget()
        right_splitter.addWidget(self._result_table)
        right_splitter.setStretchFactor(0, 0)
        right_splitter.setStretchFactor(1, 1)

        self._main_splitter.addWidget(right_splitter)
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)
        self._main_splitter.setSizes([320, 880])

        root_layout.addWidget(self._main_splitter)

        self._create_menu_bar()
        self._create_toolbar()

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪 — 请打开一个 xlsx 文件")

    def _create_menu_bar(self):
        menubar = self.menuBar()

        # --- 文件菜单 ---
        file_menu = menubar.addMenu("文件(&F)")

        open_action = QAction("打开(&O)...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        export_menu = file_menu.addMenu("导出结果")
        export_xlsx = QAction("导出为 Excel (.xlsx)", self)
        export_xlsx.triggered.connect(lambda: self._on_export("xlsx"))
        export_menu.addAction(export_xlsx)

        export_csv = QAction("导出为 CSV", self)
        export_csv.triggered.connect(lambda: self._on_export("csv"))
        export_menu.addAction(export_csv)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- 视图菜单 ---
        view_menu = menubar.addMenu("视图(&V)")

        self._toggle_left_action = QAction("显示/隐藏左侧面板", self)
        self._toggle_left_action.setCheckable(True)
        self._toggle_left_action.setChecked(True)
        self._toggle_left_action.triggered.connect(self._toggle_left_panel)
        view_menu.addAction(self._toggle_left_action)

        # --- 查询菜单 ---
        query_menu = menubar.addMenu("查询(&Q)")

        run_action = QAction("执行查询(&R)", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self._on_run_query)
        query_menu.addAction(run_action)

        query_menu.addSeparator()

        clear_action = QAction("清空查询", self)
        clear_action.setShortcut("Ctrl+D")
        clear_action.triggered.connect(self._on_clear_query)
        query_menu.addAction(clear_action)

        # --- 帮助菜单 ---
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_btn = QAction("打开", self)
        open_btn.triggered.connect(self._on_open_file)
        toolbar.addAction(open_btn)

        toolbar.addSeparator()

        run_btn = QAction("执行", self)
        run_btn.triggered.connect(self._on_run_query)
        toolbar.addAction(run_btn)

        toolbar.addSeparator()

        export_btn = QAction("导出", self)
        export_btn.triggered.connect(lambda: self._on_export("xlsx"))
        toolbar.addAction(export_btn)

    # ── 信号连接 ────────────────────────────────

    def _connect_signals(self):
        self._file_panel.file_loaded.connect(self._on_file_loaded)
        self._file_panel.sheet_changed.connect(self._on_sheet_changed)
        self._sql_editor.query_executed.connect(self._execute_sql)
        self._query_builder.query_requested.connect(self._on_query_from_builder)

    # ── 事件处理 ────────────────────────────────

    def _on_open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择 xlsx 文件", "",
            "Excel 文件 (*.xlsx);;所有文件 (*.*)"
        )
        if filepath:
            self._load_file(filepath)

    def _load_file(self, filepath):
        try:
            self._current_filepath = filepath
            self._status_bar.showMessage(
                "正在加载 {} ...".format(os.path.basename(filepath))
            )

            self._data_manager.load(filepath)

            file_info = self._data_manager.get_file_info()
            self._file_panel.set_file_info(file_info)

            header_info = self._data_manager.get_header_info()
            self._header_view.set_header_info(header_info)

            columns = self._data_manager.get_columns()
            self._file_panel.set_columns(columns)
            self._query_builder.set_available_columns(columns)

            from src.core.query_engine import QueryEngine
            qe = QueryEngine()
            schema = qe.get_schema_info(self._data_manager.get_dataframe())
            self._sql_editor.set_schema_hint(schema)

            preview = self._data_manager.get_preview(50)
            self._result_table.set_data(preview)

            summary = self._data_manager.get_summary()
            self._status_bar.showMessage(
                "已加载: {} | 行数: {} | 列数: {} | 表头行: {} | 置信度: {:.1%}".format(
                    os.path.basename(filepath),
                    summary['rows'], summary['cols'],
                    summary['header_rows'], summary['header_confidence']
                )
            )

        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))
            self._status_bar.showMessage("加载失败")

    def _on_file_loaded(self, filepath):
        self._load_file(filepath)

    def _on_sheet_changed(self, sheet_name):
        if self._current_filepath:
            self._status_bar.showMessage("正在切换至 {} ...".format(sheet_name))
            try:
                self._data_manager.load(self._current_filepath, sheet_name)
                self._on_data_updated()
                self._status_bar.showMessage("已切换至 {}".format(sheet_name))
            except Exception as e:
                QMessageBox.critical(self, "切换失败", str(e))

    def _on_data_updated(self):
        self._header_view.set_header_info(self._data_manager.get_header_info())
        self._file_panel.set_columns(self._data_manager.get_columns())
        self._query_builder.set_available_columns(self._data_manager.get_columns())

        from src.core.query_engine import QueryEngine
        qe = QueryEngine()
        schema = qe.get_schema_info(self._data_manager.get_dataframe())
        self._sql_editor.set_schema_hint(schema)

        preview = self._data_manager.get_preview(50)
        self._result_table.set_data(preview)

    def _on_run_query(self):
        current_tab = self._query_tabs.currentIndex()
        if current_tab == 0:
            sql = self._sql_editor.get_sql()
            if not sql.strip():
                QMessageBox.warning(self, "提示", "请输入 SQL 查询语句。")
                return
            self._execute_sql(sql)
        elif current_tab == 1:
            self._query_builder.execute()

    def _execute_sql(self, sql):
        try:
            from src.core.query_engine import QueryEngine
            df = self._data_manager.get_dataframe()
            engine = QueryEngine()

            valid, err = engine.validate(df, sql)
            if not valid:
                reply = QMessageBox.question(
                    self, "SQL 验证失败",
                    "SQL 可能有误:\n{}\n\n是否仍然执行？".format(err),
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            result = engine.execute(df, sql)
            self._show_result(result, "SQL 查询结果 ({} 行)".format(len(result)))

        except Exception as e:
            QMessageBox.critical(self, "查询失败", str(e))

    def _on_query_from_builder(self, sql):
        self._sql_editor.set_sql(sql)
        self._execute_sql(sql)

    def _show_result(self, df, title=""):
        self._result_table.set_data(df, title)
        self._status_bar.showMessage(
            "查询完成 | 结果: {} 行 x {} 列".format(len(df), len(df.columns))
        )

    def _on_clear_query(self):
        current = self._query_tabs.currentIndex()
        if current == 0:
            self._sql_editor.clear()
        else:
            self._query_builder.clear()

    def _on_export(self, fmt):
        df = self._result_table.get_data()
        if df is None or len(df) == 0:
            QMessageBox.information(self, "提示", "没有可导出的数据。")
            return
        dialog = ExportDialog(self, df, fmt)
        dialog.exec_()

    def _toggle_left_panel(self, checked):
        left_widget = self._main_splitter.widget(0)
        left_widget.setVisible(checked)

    def _on_about(self):
        QMessageBox.about(
            self,
            "关于 {}".format(self.APP_NAME),
            "<h3>{} v{}</h3>"
            "<p>复杂表头 xlsx 文件分析工具</p>"
            "<p>功能:</p>"
            "<ul>"
            "<li>自动识别复杂表头（多行表头、合并单元格）</li>"
            "<li>SQL 查询和可视化条件构建</li>"
            "<li>数据统计与分析</li>"
            "<li>结果导出 (xlsx/csv)</li>"
            "</ul>".format(self.APP_NAME, self.APP_VERSION)
        )

    # ── 窗口状态管理 ────────────────────────────

    def _restore_window_state(self):
        settings = QSettings("XlsxTools", "MainWindow")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
        sizes = settings.value("splitterSizes")
        if sizes:
            self._main_splitter.setSizes([int(s) for s in sizes])

    def closeEvent(self, event):
        settings = QSettings("XlsxTools", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("splitterSizes",
                          [str(s) for s in self._main_splitter.sizes()])
        self._data_manager.close()
        super().closeEvent(event)
