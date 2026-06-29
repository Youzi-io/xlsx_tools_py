"""文件面板 — 文件浏览、Sheet 选择、数据摘要、列列表。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QComboBox,
    QGroupBox, QFileDialog, QTextEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

from src.core.xlsx_reader import FileInfo
from src.utils.formatter import format_bytes


class FilePanel(QWidget):
    """左侧文件管理面板。"""

    file_loaded = pyqtSignal(str)
    sheet_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._file_info = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── 文件区 ──
        file_group = QGroupBox("文件")
        file_layout = QVBoxLayout(file_group)

        open_layout = QHBoxLayout()
        self._open_btn = QPushButton("打开文件...")
        self._open_btn.clicked.connect(self._on_open_clicked)
        open_layout.addWidget(self._open_btn)
        file_layout.addLayout(open_layout)

        self._filepath_label = QLabel("未加载文件")
        self._filepath_label.setWordWrap(True)
        self._filepath_label.setStyleSheet("color: gray; font-size: 11px;")
        file_layout.addWidget(self._filepath_label)

        sheet_layout = QHBoxLayout()
        sheet_layout.addWidget(QLabel("Sheet:"))
        self._sheet_combo = QComboBox()
        self._sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        sheet_layout.addWidget(self._sheet_combo)
        file_layout.addLayout(sheet_layout)

        layout.addWidget(file_group)

        # ── 数据摘要区 ──
        summary_group = QGroupBox("数据摘要")
        summary_layout = QVBoxLayout(summary_group)
        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        self._summary_text.setMaximumHeight(150)
        self._summary_text.setStyleSheet("font-size: 11px;")
        summary_layout.addWidget(self._summary_text)
        layout.addWidget(summary_group)

        # ── 列列表 ──
        columns_group = QGroupBox("列列表")
        columns_layout = QVBoxLayout(columns_group)
        self._columns_list = QListWidget()
        self._columns_list.setSelectionMode(QListWidget.ExtendedSelection)
        columns_layout.addWidget(self._columns_list)
        layout.addWidget(columns_group)

        layout.setStretch(2, 1)
        layout.setStretch(3, 2)

    # ── 拖拽支持 ────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.toLocalFile().lower().endswith(".xlsx"):
                event.acceptProposedAction()

    def dropEvent(self, event):
        filepath = event.mimeData().urls()[0].toLocalFile()
        self.file_loaded.emit(filepath)

    # ── 公共方法 ────────────────────────────────

    def set_file_info(self, info):
        self._file_info = info
        self._filepath_label.setText(info.filepath)

        self._sheet_combo.blockSignals(True)
        self._sheet_combo.clear()
        for sheet in info.sheets:
            self._sheet_combo.addItem(sheet.name)
        self._sheet_combo.blockSignals(False)

        self._update_summary(info)

    def set_columns(self, columns):
        self._columns_list.clear()
        for col in columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self._columns_list.addItem(item)

    def get_selected_columns(self):
        selected = []
        for i in range(self._columns_list.count()):
            item = self._columns_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def get_all_columns(self):
        return [self._columns_list.item(i).text()
                for i in range(self._columns_list.count())]

    def get_current_sheet(self):
        return self._sheet_combo.currentText()

    # ── 内部方法 ────────────────────────────────

    def _on_open_clicked(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择 xlsx 文件", "",
            "Excel 文件 (*.xlsx);;所有文件 (*.*)"
        )
        if filepath:
            self.file_loaded.emit(filepath)

    def _on_sheet_changed(self, name):
        if name and self._file_info:
            self.sheet_changed.emit(name)

    def _update_summary(self, info):
        lines = []
        lines.append("文件名: {}".format(info.filename))
        lines.append("Sheet 数: {}".format(info.sheet_count))

        current_sheet = self._sheet_combo.currentText()
        for sheet in info.sheets:
            if sheet.name == current_sheet:
                lines.append("当前 Sheet: {}".format(sheet.name))
                lines.append("行数: {}".format(sheet.rows))
                lines.append("列数: {}".format(sheet.cols))
                if sheet.has_merged_cells:
                    lines.append("合并单元格: {} 个".format(sheet.merged_cells_count))
                else:
                    lines.append("合并单元格: 无")
                break

        self._summary_text.setPlainText("\n".join(lines))
