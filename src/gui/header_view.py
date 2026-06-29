"""表头视图 — 以树形结构展示复杂表头的层级关系。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QLabel, QHeaderView,
)
from PyQt5.QtCore import Qt

from src.core.header_detector import HeaderInfo, ColumnDef


class HeaderViewWidget(QWidget):
    """表头结构可视化面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._header_info = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        group = QGroupBox("表头结构")
        group_layout = QVBoxLayout(group)

        self._confidence_label = QLabel("")
        self._confidence_label.setStyleSheet("font-size: 10px; color: gray;")
        group_layout.addWidget(self._confidence_label)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["列名层级", "Excel列", "合并"])
        self._tree.setColumnWidth(0, 200)
        self._tree.setColumnWidth(1, 60)
        self._tree.setColumnWidth(2, 50)
        self._tree.setAlternatingRowColors(True)
        group_layout.addWidget(self._tree)

        layout.addWidget(group)

    def set_header_info(self, info):
        self._header_info = info
        self._rebuild_tree()
        self._confidence_label.setText(
            "表头行: {} 行 | 数据起始行: {} | 置信度: {:.1%}".format(
                len(info.header_rows), info.data_start_row + 1, info.confidence
            )
        )

    def _rebuild_tree(self):
        self._tree.clear()
        if not self._header_info or not self._header_info.columns:
            return

        for col_def in self._header_info.columns:
            hierarchy = col_def.hierarchy
            if not hierarchy:
                QTreeWidgetItem(self._tree, [
                    col_def.flat_name,
                    col_def.original_excel_col,
                    "Y" if col_def.is_merged else "",
                ])
                continue

            current_parent = self._tree
            for i, level_name in enumerate(hierarchy):
                is_last = (i == len(hierarchy) - 1)
                parent_list = (
                    current_parent if current_parent is not self._tree
                    else self._tree
                )

                found = None
                count = (parent_list.topLevelItemCount()
                         if current_parent is self._tree
                         else parent_list.childCount())
                for j in range(count):
                    candidate = (
                        parent_list.topLevelItem(j)
                        if current_parent is self._tree
                        else parent_list.child(j)
                    )
                    if candidate.text(0) == level_name:
                        found = candidate
                        break

                if found:
                    if is_last:
                        child = QTreeWidgetItem(found, [
                            col_def.flat_name,
                            col_def.original_excel_col,
                            "Y" if col_def.is_merged else "",
                        ])
                        child.setToolTip(0, "扁平名: {}\n层级: {}".format(
                            col_def.flat_name, " > ".join(hierarchy)
                        ))
                    current_parent = found
                else:
                    target_parent = (
                        self._tree if current_parent is self._tree
                        else current_parent
                    )
                    new_item = QTreeWidgetItem(target_parent, [
                        level_name,
                        col_def.original_excel_col if is_last else "",
                        "Y" if (col_def.is_merged and is_last) else "",
                    ])
                    new_item.setToolTip(0, "层级: {}".format(
                        " > ".join(hierarchy[:i+1])
                    ))
                    current_parent = new_item

        self._tree.expandAll()
