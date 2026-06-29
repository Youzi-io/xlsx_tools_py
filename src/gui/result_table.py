"""结果表格视图 — 以 QTableView + pandas Model 展示查询结果。"""

import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView,
    QHeaderView, QGroupBox, QAbstractItemView,
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt5.QtGui import QColor, QFont


class PandasTableModel(QAbstractTableModel):
    """将 pandas DataFrame 适配为 Qt 表格模型。"""

    def __init__(self, df=None, parent=None):
        super().__init__(parent)
        self._df = df if df is not None else pd.DataFrame()

    def setDataFrame(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def getDataFrame(self):
        return self._df

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row, col = index.row(), index.column()

        if role == Qt.DisplayRole:
            val = self._df.iloc[row, col]
            if pd.isna(val):
                return ""
            elif isinstance(val, float):
                if abs(val) >= 1e6 or (abs(val) < 1e-4 and val != 0):
                    return "{:.4e}".format(val)
                elif val == int(val):
                    return str(int(val))
                else:
                    return "{:.4f}".format(val).rstrip("0").rstrip(".")
            else:
                return str(val)

        elif role == Qt.TextAlignmentRole:
            val = self._df.iloc[row, col]
            if isinstance(val, (int, float)) and not pd.isna(val):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.BackgroundRole:
            if row % 2 == 0:
                return QColor("#F8F8F8")
            return QColor("#FFFFFF")

        elif role == Qt.FontRole:
            return QFont("Microsoft YaHei", 10)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section]) if section < len(self._df.columns) else ""
            else:
                return str(section + 1)

        elif role == Qt.FontRole:
            font = QFont("Microsoft YaHei", 10)
            font.setBold(True)
            return font

        elif role == Qt.BackgroundRole:
            if orientation == Qt.Horizontal:
                return QColor("#E8E8E8")

        return None

    def sort(self, column, order=Qt.AscendingOrder):
        if self._df.empty or column < 0 or column >= len(self._df.columns):
            return
        self.layoutAboutToBeChanged.emit()
        col_name = self._df.columns[column]
        ascending = order == Qt.AscendingOrder
        self._df = self._df.sort_values(col_name, ascending=ascending)
        self._df = self._df.reset_index(drop=True)
        self.layoutChanged.emit()


class ResultTableWidget(QWidget):
    """结果表格面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = PandasTableModel()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        group = QGroupBox("查询结果")
        group_layout = QVBoxLayout(group)

        self._title_label = QLabel("数据预览")
        self._title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        group_layout.addWidget(self._title_label)

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setSortingEnabled(True)

        h_header = self._table.horizontalHeader()
        h_header.setStretchLastSection(True)
        h_header.setSectionResizeMode(QHeaderView.Interactive)

        v_header = self._table.verticalHeader()
        v_header.setDefaultSectionSize(24)
        v_header.setMinimumWidth(60)

        group_layout.addWidget(self._table)
        layout.addWidget(group)

    def set_data(self, df, title=""):
        self._model.setDataFrame(df)
        if title:
            self._title_label.setText(title)
        else:
            self._title_label.setText(
                "查询结果 ({} 行 x {} 列)".format(len(df), len(df.columns))
            )
        self._table.resizeColumnsToContents()

    def get_data(self):
        return self._model.getDataFrame()

    def clear(self):
        self._model.setDataFrame(pd.DataFrame())
        self._title_label.setText("无数据")
