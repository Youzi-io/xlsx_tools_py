"""条件构建器 — 可视化方式构建查询条件，自动生成 SQL。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QLabel, QScrollArea,
    QGroupBox, QPlainTextEdit, QCheckBox, QSpinBox,
)
from PyQt5.QtCore import Qt, pyqtSignal

from src.core.query_engine import QueryEngine

OPERATORS = [
    ("等于 (=)", "="),
    ("不等于 (!=)", "!="),
    ("大于 (>)", ">"),
    ("大于等于 (>=)", ">="),
    ("小于 (<)", "<"),
    ("小于等于 (<=)", "<="),
    ("包含 (LIKE)", "LIKE"),
    ("不包含 (NOT LIKE)", "NOT LIKE"),
    ("为空", "IS NULL"),
    ("不为空", "IS NOT NULL"),
    ("介于 (BETWEEN)", "BETWEEN"),
]

AGG_FUNCTIONS = [
    ("求和 (SUM)", "SUM"),
    ("平均值 (AVG)", "AVG"),
    ("计数 (COUNT)", "COUNT"),
    ("最大值 (MAX)", "MAX"),
    ("最小值 (MIN)", "MIN"),
    ("去重计数 (DISTINCT COUNT)", "COUNT DISTINCT"),
]

CONNECTORS = ["AND", "OR"]


class ConditionRow(QWidget):
    """单个查询条件的行组件。"""

    removed = pyqtSignal(object)

    def __init__(self, columns, index, parent=None):
        super().__init__(parent)
        self._columns = columns
        self._index = index
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        if self._index > 0:
            self._connector = QComboBox()
            self._connector.addItems(CONNECTORS)
            layout.addWidget(self._connector)
        else:
            self._connector = None
            layout.addWidget(QLabel("WHERE"))

        self._col_combo = QComboBox()
        self._col_combo.addItems(self._columns)
        self._col_combo.setMinimumWidth(60)
        layout.addWidget(self._col_combo)

        self._op_combo = QComboBox()
        for label, _ in OPERATORS:
            self._op_combo.addItem(label)
        self._op_combo.currentIndexChanged.connect(self._on_op_changed)
        layout.addWidget(self._op_combo)

        self._value_edit = QLineEdit()
        self._value_edit.setPlaceholderText("值")
        self._value_edit.setMaximumWidth(120)
        layout.addWidget(self._value_edit)

        self._value_edit2 = QLineEdit()
        self._value_edit2.setPlaceholderText("结束值")
        self._value_edit2.setMaximumWidth(120)
        self._value_edit2.setVisible(False)
        layout.addWidget(self._value_edit2)

        remove_btn = QPushButton("X")
        remove_btn.setFixedWidth(30)
        remove_btn.setToolTip("删除此条件")
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(remove_btn)

        layout.addStretch()

    def _on_op_changed(self, idx):
        op_val = OPERATORS[idx][1]
        self._value_edit2.setVisible(op_val == "BETWEEN")
        if op_val in ("IS NULL", "IS NOT NULL"):
            self._value_edit.setVisible(False)
        else:
            self._value_edit.setVisible(True)

    def to_sql_condition(self):
        col = '"{}"'.format(self._col_combo.currentText())
        op_val = OPERATORS[self._op_combo.currentIndex()][1]
        val = self._value_edit.text().strip()

        if op_val in ("IS NULL", "IS NOT NULL"):
            return "{} {}".format(col, op_val)
        elif op_val == "BETWEEN":
            val2 = self._value_edit2.text().strip()
            return "{} BETWEEN '{}' AND '{}'".format(col, val, val2)
        elif op_val in ("LIKE", "NOT LIKE"):
            return "{} {} '%{}%'".format(col, op_val, val)
        else:
            try:
                float(val)
                return "{} {} {}".format(col, op_val, val)
            except ValueError:
                return "{} {} '{}'".format(col, op_val, val)

    def get_connector(self):
        if self._connector:
            return self._connector.currentText()
        return "AND"


class StatColumnRow(QWidget):
    """统计列行组件。"""

    removed = pyqtSignal(object)

    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self._columns = columns
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self._agg_combo = QComboBox()
        for label, _ in AGG_FUNCTIONS:
            self._agg_combo.addItem(label)
        layout.addWidget(self._agg_combo)

        self._col_combo = QComboBox()
        self._col_combo.addItems(self._columns)
        layout.addWidget(self._col_combo)

        layout.addWidget(QLabel("AS"))
        self._alias_edit = QLineEdit()
        self._alias_edit.setPlaceholderText("别名")
        self._alias_edit.setMaximumWidth(100)
        layout.addWidget(self._alias_edit)

        remove_btn = QPushButton("X")
        remove_btn.setFixedWidth(30)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(remove_btn)

        layout.addStretch()

    def to_sql_select(self):
        func = AGG_FUNCTIONS[self._agg_combo.currentIndex()][1]
        col = '"{}"'.format(self._col_combo.currentText())
        alias = self._alias_edit.text().strip()

        if func == "COUNT DISTINCT":
            expr = "COUNT(DISTINCT {})".format(col)
        else:
            expr = "{}({})".format(func, col)

        if alias:
            return '{} AS "{}"'.format(expr, alias)
        return expr


class QueryBuilderWidget(QWidget):
    """可视化条件构建器。"""

    query_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._columns = []
        self._condition_rows = []
        self._stat_rows = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        top_layout = QHBoxLayout()

        self._run_btn = QPushButton("执行查询")
        self._run_btn.setStyleSheet(
            "QPushButton { background-color: #0078D4; color: white; "
            "padding: 6px 16px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #106EBE; }"
        )
        self._run_btn.clicked.connect(self.execute)
        top_layout.addWidget(self._run_btn)

        self._preview_btn = QPushButton("预览 SQL")
        self._preview_btn.clicked.connect(self._on_preview_sql)
        top_layout.addWidget(self._preview_btn)

        self._clear_btn = QPushButton("重置")
        self._clear_btn.clicked.connect(self.clear)
        top_layout.addWidget(self._clear_btn)

        layout.addLayout(top_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 条件组
        cond_group = QGroupBox("查询条件 (WHERE)")
        self._cond_layout = QVBoxLayout(cond_group)
        self._cond_layout.setAlignment(Qt.AlignTop)
        self._add_cond_btn = QPushButton("+ 添加条件")
        self._add_cond_btn.clicked.connect(self._add_condition)
        self._cond_layout.addWidget(self._add_cond_btn)
        scroll_layout.addWidget(cond_group)

        # 统计列组
        stat_group = QGroupBox("统计列 (SELECT)")
        self._stat_layout = QVBoxLayout(stat_group)
        self._stat_layout.setAlignment(Qt.AlignTop)
        self._add_stat_btn = QPushButton("+ 添加统计列")
        self._add_stat_btn.clicked.connect(self._add_stat_column)
        self._stat_layout.addWidget(self._add_stat_btn)
        scroll_layout.addWidget(stat_group)

        # 分组组
        group_group = QGroupBox("分组 (GROUP BY)")
        group_layout = QHBoxLayout(group_group)
        self._group_combo = QComboBox()
        self._group_combo.addItem("-- 不分组 --")
        group_layout.addWidget(self._group_combo)
        scroll_layout.addWidget(group_group)

        # 排序组
        sort_group = QGroupBox("排序 (ORDER BY)")
        sort_layout = QHBoxLayout(sort_group)
        self._sort_combo = QComboBox()
        self._sort_combo.addItem("-- 不排序 --")
        sort_layout.addWidget(self._sort_combo)
        sort_layout.addWidget(QLabel("顺序:"))
        self._sort_dir = QComboBox()
        self._sort_dir.addItems(["降序 (DESC)", "升序 (ASC)"])
        sort_layout.addWidget(self._sort_dir)
        scroll_layout.addWidget(sort_group)

        # 限制行数
        limit_group = QGroupBox("行数限制 (LIMIT)")
        limit_layout = QHBoxLayout(limit_group)
        self._limit_check = QCheckBox("限制结果行数:")
        self._limit_check.setChecked(True)
        limit_layout.addWidget(self._limit_check)
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(1, 100000)
        self._limit_spin.setValue(100)
        limit_layout.addWidget(self._limit_spin)
        scroll_layout.addWidget(limit_group)

        # SQL 预览
        preview_group = QGroupBox("生成的 SQL")
        preview_layout = QVBoxLayout(preview_group)
        self._sql_preview = QPlainTextEdit()
        self._sql_preview.setReadOnly(True)
        self._sql_preview.setMaximumHeight(120)
        preview_layout.addWidget(self._sql_preview)
        scroll_layout.addWidget(preview_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

    def set_available_columns(self, columns):
        self._columns = columns

        for row in self._condition_rows:
            current = row._col_combo.currentText()
            row._col_combo.blockSignals(True)
            row._col_combo.clear()
            row._col_combo.addItems(columns)
            if current in columns:
                row._col_combo.setCurrentText(current)
            row._col_combo.blockSignals(False)

        for row in self._stat_rows:
            current = row._col_combo.currentText()
            row._col_combo.blockSignals(True)
            row._col_combo.clear()
            row._col_combo.addItems(columns)
            if current in columns:
                row._col_combo.setCurrentText(current)
            row._col_combo.blockSignals(False)

        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        self._group_combo.addItem("-- 不分组 --")
        self._group_combo.addItems(columns)
        self._group_combo.blockSignals(False)

        self._sort_combo.blockSignals(True)
        self._sort_combo.clear()
        self._sort_combo.addItem("-- 不排序 --")
        self._sort_combo.addItems(columns)
        self._sort_combo.blockSignals(False)

    def execute(self):
        sql = self.build_sql()
        if sql:
            self._sql_preview.setPlainText(sql)
            self.query_requested.emit(sql)

    def build_sql(self):
        if not self._columns:
            return None

        if self._stat_rows:
            selects = [r.to_sql_select() for r in self._stat_rows]
            group_col = self._group_combo.currentText()
            if group_col != "-- 不分组 --":
                selects.insert(0, '"{}"'.format(group_col))
            select_clause = ", ".join(selects)
        else:
            select_clause = "*"

        sql = "SELECT {} FROM data".format(select_clause)

        if self._condition_rows:
            conditions = []
            for i, row in enumerate(self._condition_rows):
                cond = row.to_sql_condition()
                if i == 0:
                    conditions.append(cond)
                else:
                    conditions.append(
                        "{} {}".format(row.get_connector(), cond)
                    )
            sql += " WHERE " + " ".join(conditions)

        group_col = self._group_combo.currentText()
        if group_col != "-- 不分组 --":
            sql += ' GROUP BY "{}"'.format(group_col)

        sort_col = self._sort_combo.currentText()
        if sort_col != "-- 不排序 --":
            direction = "DESC" if self._sort_dir.currentText().startswith("降序") else "ASC"
            sql += ' ORDER BY "{}" {}'.format(sort_col, direction)

        if self._limit_check.isChecked():
            sql += " LIMIT {}".format(self._limit_spin.value())

        return sql

    def clear(self):
        for row in self._condition_rows[:]:
            self._remove_condition(row)
        for row in self._stat_rows[:]:
            self._remove_stat_column(row)
        self._sql_preview.clear()

    def _add_condition(self):
        if not self._columns:
            return
        idx = len(self._condition_rows)
        row = ConditionRow(self._columns, idx)
        row.removed.connect(self._remove_condition)
        self._cond_layout.insertWidget(self._cond_layout.count() - 1, row)
        self._condition_rows.append(row)

    def _remove_condition(self, row):
        self._cond_layout.removeWidget(row)
        row.deleteLater()
        self._condition_rows.remove(row)
        for i, r in enumerate(self._condition_rows):
            r._index = i
            if i == 0 and r._connector:
                r._connector.hide()
            elif i > 0 and r._connector:
                r._connector.show()

    def _add_stat_column(self):
        if not self._columns:
            return
        row = StatColumnRow(self._columns)
        row.removed.connect(self._remove_stat_column)
        self._stat_layout.insertWidget(self._stat_layout.count() - 1, row)
        self._stat_rows.append(row)

    def _remove_stat_column(self, row):
        self._stat_layout.removeWidget(row)
        row.deleteLater()
        self._stat_rows.remove(row)

    def _on_preview_sql(self):
        sql = self.build_sql()
        if sql:
            self._sql_preview.setPlainText(sql)
        else:
            self._sql_preview.setPlainText("-- 请先加载文件并设置查询条件")
