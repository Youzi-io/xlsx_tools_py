"""
数据库管理面板 — 保存/加载/删除数据集。

信号:
    dataset_loaded(df, name) — 加载数据集
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QListWidget, QListWidgetItem,
    QMessageBox, QInputDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal

from src.core.db_store import DatabaseStore


class DbPanelWidget(QWidget):
    """左侧数据库管理面板。"""

    dataset_loaded = pyqtSignal(object, str)  # df, name

    def __init__(self, db_path: str = None, parent=None):
        super().__init__(parent)
        self._store = DatabaseStore(db_path)
        self._current_df = None        # 主窗口注入的要保存的 DataFrame
        self._current_source = ""      # 来源文件名
        self._current_sheet = ""       # 来源 Sheet
        self._init_ui()
        self._refresh_list()

    # ── 公共方法 ────────────────────────────────

    def set_current_data(self, df, source_file: str = "", sheet_name: str = ""):
        """设置当前可保存的数据（由主窗口调用）。"""
        self._current_df = df
        self._current_source = source_file
        self._current_sheet = sheet_name

    def get_store(self) -> DatabaseStore:
        """获取底层存储对象。"""
        return self._store

    def has_data(self) -> bool:
        """当前是否有可保存的数据。"""
        return self._current_df is not None and len(self._current_df) > 0

    # ── UI ──────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        group = QGroupBox("数据库管理")
        group_layout = QVBoxLayout(group)

        # 保存按钮
        btn_layout = QHBoxLayout()
        self._save_btn = QPushButton("保存当前数据")
        self._save_btn.setToolTip("将当前显示的查询结果/数据保存到数据库")
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)
        group_layout.addLayout(btn_layout)

        # 分隔
        group_layout.addWidget(QLabel("已保存的数据集:"))

        # 数据集列表
        self._list_widget = QListWidget()
        self._list_widget.setAlternatingRowColors(True)
        self._list_widget.setMaximumHeight(200)
        group_layout.addWidget(self._list_widget)

        # 操作按钮
        op_layout = QHBoxLayout()
        self._load_btn = QPushButton("加载")
        self._load_btn.setToolTip("加载选中的数据集")
        self._load_btn.clicked.connect(self._on_load)
        op_layout.addWidget(self._load_btn)

        self._delete_btn = QPushButton("删除")
        self._delete_btn.setToolTip("删除选中的数据集")
        self._delete_btn.clicked.connect(self._on_delete)
        op_layout.addWidget(self._delete_btn)
        group_layout.addLayout(op_layout)

        layout.addWidget(group)

    # ── 内部方法 ────────────────────────────────

    def _refresh_list(self):
        """刷新数据集列表。"""
        self._list_widget.clear()
        datasets = self._store.list_datasets()
        for ds in datasets:
            text = "{}  ({}行 x {}列)".format(
                ds["name"], ds["rows"], ds["cols"]
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ds["name"])
            item.setToolTip(
                "来源: {}\nSheet: {}\n创建: {}".format(
                    ds.get("source_file", "-"),
                    ds.get("sheet_name", "-"),
                    str(ds.get("created_at", "-"))[:19]
                )
            )
            self._list_widget.addItem(item)

    def _get_selected_name(self) -> str:
        """获取列表中选中的数据集名称。"""
        item = self._list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择数据集。")
            return ""
        return item.data(Qt.UserRole)

    def _on_save(self):
        """保存当前数据。"""
        if not self.has_data():
            QMessageBox.information(self, "提示", "没有可保存的数据。请先导入 xlsx 文件。")
            return

        name, ok = QInputDialog.getText(
            self, "保存数据集", "请输入数据集名称:",
            text=self._current_source.rsplit(".", 1)[0] if self._current_source else ""
        )
        if not ok or not name.strip():
            return

        name = name.strip()

        # 检查同名
        if self._store.exists(name):
            reply = QMessageBox.question(
                self, "确认覆盖",
                "数据集 '{}' 已存在，是否覆盖？".format(name),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        try:
            self._store.save_dataset(
                name, self._current_df,
                source_file=self._current_source,
                sheet_name=self._current_sheet
            )
            self._refresh_list()
            QMessageBox.information(
                self, "保存成功",
                "数据集 '{}' 已保存 ({} 行 x {} 列)".format(
                    name, len(self._current_df), len(self._current_df.columns)
                )
            )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_load(self):
        """加载选中的数据集。"""
        name = self._get_selected_name()
        if not name:
            return

        try:
            df = self._store.load_dataset(name)
            self.dataset_loaded.emit(df, name)
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

    def _on_delete(self):
        """删除选中的数据集。"""
        name = self._get_selected_name()
        if not name:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            "确定删除数据集 '{}' 吗？\n此操作不可恢复。".format(name),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._store.delete_dataset(name)
            self._refresh_list()
        except Exception as e:
            QMessageBox.critical(self, "删除失败", str(e))
