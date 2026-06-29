"""导出对话框 — 支持将查询结果导出为 xlsx / csv。"""

import pandas as pd

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QCheckBox, QGroupBox,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt


class ExportDialog(QDialog):
    """导出对话框。"""

    def __init__(self, parent, df, default_format="xlsx"):
        super().__init__(parent)
        self._df = df
        self._default_format = default_format

        self.setWindowTitle("导出结果")
        self.setMinimumSize(450, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 导出格式
        fmt_group = QGroupBox("导出格式")
        fmt_layout = QHBoxLayout(fmt_group)
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["Excel (.xlsx)", "CSV (.csv)"])
        fmt_map = {"xlsx": 0, "csv": 1}
        self._fmt_combo.setCurrentIndex(fmt_map.get(self._default_format, 0))
        self._fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        fmt_layout.addWidget(self._fmt_combo)
        fmt_layout.addStretch()
        layout.addWidget(fmt_group)

        # 列选择
        col_group = QGroupBox("导出列")
        col_layout = QVBoxLayout(col_group)

        select_all_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        select_all_layout.addWidget(select_all_btn)

        deselect_btn = QPushButton("取消全选")
        deselect_btn.clicked.connect(self._deselect_all)
        select_all_layout.addWidget(deselect_btn)
        select_all_layout.addStretch()
        col_layout.addLayout(select_all_layout)

        self._col_list = QListWidget()
        for col in self._df.columns:
            item = QListWidgetItem(str(col))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self._col_list.addItem(item)
        col_layout.addWidget(self._col_list)
        layout.addWidget(col_group)

        # CSV 选项
        self._csv_group = QGroupBox("CSV 选项")
        csv_layout = QHBoxLayout(self._csv_group)
        csv_layout.addWidget(QLabel("编码:"))
        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems(["utf-8", "utf-8-sig", "gbk", "gb2312"])
        csv_layout.addWidget(self._encoding_combo)
        csv_layout.addWidget(QLabel("分隔符:"))
        self._sep_combo = QComboBox()
        self._sep_combo.addItems([", (逗号)", "; (分号)", "\\t (制表符)"])
        csv_layout.addWidget(self._sep_combo)
        self._csv_group.setVisible(self._fmt_combo.currentIndex() == 1)
        layout.addWidget(self._csv_group)

        # 预览
        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout(preview_group)
        preview_label = QLabel(
            "共 {} 行 x {} 列\n前 5 行预览:\n{}".format(
                len(self._df), len(self._df.columns),
                self._df.head(5).to_string()
            )
        )
        preview_label.setStyleSheet("font-family: Consolas; font-size: 10px;")
        preview_layout.addWidget(preview_label)
        layout.addWidget(preview_group)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _get_selected_columns(self):
        cols = []
        for i in range(self._col_list.count()):
            item = self._col_list.item(i)
            if item.checkState() == Qt.Checked:
                cols.append(item.text())
        return cols

    def _select_all(self):
        for i in range(self._col_list.count()):
            self._col_list.item(i).setCheckState(Qt.Checked)

    def _deselect_all(self):
        for i in range(self._col_list.count()):
            self._col_list.item(i).setCheckState(Qt.Unchecked)

    def _on_format_changed(self, idx):
        self._csv_group.setVisible(idx == 1)

    def _on_export(self):
        fmt_idx = self._fmt_combo.currentIndex()

        selected_cols = self._get_selected_columns()
        if not selected_cols:
            QMessageBox.warning(self, "警告", "请至少选择一列。")
            return

        export_df = self._df[selected_cols]

        if fmt_idx == 0:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出为 Excel", "export.xlsx",
                "Excel 文件 (*.xlsx);;所有文件 (*.*)"
            )
            if filepath:
                try:
                    export_df.to_excel(filepath, index=False, engine="openpyxl")
                    QMessageBox.information(
                        self, "导出成功",
                        "数据已导出至:\n{}\n{} 行 x {} 列".format(
                            filepath, len(export_df), len(export_df.columns)
                        )
                    )
                    self.accept()
                except Exception as e:
                    QMessageBox.critical(self, "导出失败", str(e))

        elif fmt_idx == 1:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出为 CSV", "export.csv",
                "CSV 文件 (*.csv);;所有文件 (*.*)"
            )
            if filepath:
                try:
                    encoding = self._encoding_combo.currentText()
                    sep_text = self._sep_combo.currentText()
                    sep_map = {", (逗号)": ",", "; (分号)": ";", "\\t (制表符)": "\t"}
                    sep = sep_map.get(sep_text, ",")

                    export_df.to_csv(filepath, index=False,
                                    encoding=encoding, sep=sep)
                    QMessageBox.information(
                        self, "导出成功",
                        "数据已导出至:\n{}\n{} 行 x {} 列".format(
                            filepath, len(export_df), len(export_df.columns)
                        )
                    )
                    self.accept()
                except Exception as e:
                    QMessageBox.critical(self, "导出失败", str(e))
