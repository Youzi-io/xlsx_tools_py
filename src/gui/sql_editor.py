"""SQL 编辑器面板 — SQL 输入、语法提示、Schema 参考。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QSplitter, QLabel, QGroupBox, QPlainTextEdit,
    QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor


class SqlHighlighter(QSyntaxHighlighter):
    """SQL 语法高亮器。"""

    KEYWORDS = [
        "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "LIKE",
        "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "OFFSET",
        "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "OUTER JOIN",
        "ON", "AS", "DISTINCT", "COUNT", "SUM", "AVG", "MAX", "MIN",
        "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER",
        "BETWEEN", "IS", "NULL", "ASC", "DESC", "UNION", "ALL",
        "CASE", "WHEN", "THEN", "ELSE", "END",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor("#0033B3"))
        keyword_fmt.setFontWeight(QFont.Bold)

        for kw in self.KEYWORDS:
            self._rules.append((r"\b{}\b".format(kw), keyword_fmt))

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#067D17"))
        self._rules.append((r"'[^']*'", string_fmt))

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor("#1750EB"))
        self._rules.append((r"\b\d+\.?\d*\b", number_fmt))

        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#8C8C8C"))
        comment_fmt.setFontItalic(True)
        self._rules.append((r"--[^\n]*", comment_fmt))

    def highlightBlock(self, text):
        import re
        for pattern, fmt in self._rules:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class SqlEditorWidget(QWidget):
    """SQL 编辑器面板。"""

    query_executed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        btn_layout = QHBoxLayout()

        self._run_btn = QPushButton("执行 (F5)")
        self._run_btn.setStyleSheet(
            "QPushButton { background-color: #0078D4; color: white; "
            "padding: 6px 16px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #106EBE; }"
        )
        self._run_btn.clicked.connect(
            lambda: self.query_executed.emit(self.get_sql())
        )
        btn_layout.addWidget(self._run_btn)

        self._clear_btn = QPushButton("清空")
        self._clear_btn.clicked.connect(self.clear)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addStretch()

        self._validate_btn = QPushButton("验证 SQL")
        self._validate_btn.clicked.connect(self._on_validate)
        btn_layout.addWidget(self._validate_btn)

        layout.addLayout(btn_layout)

        splitter = QSplitter(Qt.Vertical)

        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText(
            "在此输入 SQL 查询...\n"
            "示例: SELECT * FROM data WHERE 薪资 > 10000\n"
            "表名使用 'data'\n"
            "列名带特殊字符时请用双引号: \"列名\""
        )
        self._editor.setFont(QFont("Consolas", 11))
        self._editor.setTabStopDistance(20)
        self._highlighter = SqlHighlighter(self._editor.document())
        splitter.addWidget(self._editor)

        schema_group = QGroupBox("表结构参考")
        schema_layout = QVBoxLayout(schema_group)
        self._schema_view = QTextEdit()
        self._schema_view.setReadOnly(True)
        self._schema_view.setFont(QFont("Consolas", 10))
        self._schema_view.setMaximumHeight(200)
        self._schema_view.setPlaceholderText("加载文件后将显示表结构...")
        schema_layout.addWidget(self._schema_view)
        splitter.addWidget(schema_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def get_sql(self):
        return self._editor.toPlainText()

    def set_sql(self, sql):
        self._editor.setPlainText(sql)

    def set_schema_hint(self, schema):
        self._schema_view.setPlainText(schema)

    def clear(self):
        self._editor.clear()

    def _on_validate(self):
        sql = self.get_sql()
        if not sql.strip():
            QMessageBox.information(self, "提示", "请输入 SQL。")
            return
        QMessageBox.information(
            self, "提示",
            "SQL 验证需要加载文件。请先打开 xlsx 文件后使用 F5 执行查询。"
        )
