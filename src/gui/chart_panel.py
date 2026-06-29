"""
图表面板 — 将 matplotlib 图表嵌入 PyQt6，支持多种图表类型。

功能:
- 自动根据数据选择合适的图表类型
- 支持手动切换图表类型
- 导出为 PNG
"""

import io

import pandas as pd
import matplotlib
matplotlib.use("QtAgg")  # PyQt6 后端

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import font_manager

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QGroupBox, QFileDialog,
)
from PyQt6.QtCore import Qt


# 尝试设置中文字体
def _setup_chinese_font():
    """设置 matplotlib 中文字体。"""
    chinese_fonts = [
        "Microsoft YaHei", "SimHei", "WenQuanYi Zen Hei",
        "Noto Sans CJK SC", "PingFang SC", "Hiragino Sans GB",
        "SimSun", "KaiTi",
    ]
    available = [f.name for f in font_manager.fontManager.ttflist]
    for font_name in chinese_fonts:
        if font_name in available:
            matplotlib.rcParams["font.family"] = font_name
            return

    # 如果没有中文字体，使用 sans-serif
    matplotlib.rcParams["font.family"] = "sans-serif"


_setup_chinese_font()
matplotlib.rcParams["axes.unicode_minus"] = False


class ChartPanelWidget(QWidget):
    """
    图表面板 — 嵌入 matplotlib。

    支持的图表类型:
    - 柱状图 (bar)
    - 分组柱状图 (barh)
    - 折线图 (line)
    - 饼图 (pie)
    - 散点图 (scatter)
    """

    CHART_TYPES = ["自动", "柱状图", "分组柱状图", "折线图", "饼图", "散点图"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_df: pd.DataFrame | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        group = QGroupBox("📊 图表")
        group_layout = QVBoxLayout(group)

        # 控制栏
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("类型:"))

        self._chart_type_combo = QComboBox()
        self._chart_type_combo.addItems(self.CHART_TYPES)
        self._chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)
        ctrl_layout.addWidget(self._chart_type_combo)

        self._save_chart_btn = QPushButton("保存图表")
        self._save_chart_btn.clicked.connect(self._on_save_chart)
        ctrl_layout.addWidget(self._save_chart_btn)

        ctrl_layout.addStretch()
        group_layout.addLayout(ctrl_layout)

        # Matplotlib 画布
        self._fig = Figure(figsize=(6, 5), dpi=100)
        self._canvas = FigureCanvas(self._fig)
        group_layout.addWidget(self._canvas)

        layout.addWidget(group)

    # ── 公共方法 ────────────────────────────────

    def auto_plot(self, df: pd.DataFrame, chart_type: str = "自动"):
        """
        自动根据数据选择合适的图表类型并渲染。

        策略:
        - 1 个数值列 + 1 个分类列 → 柱状图
        - 多个数值列 + 分类列 → 分组柱状图
        - 只有分类列 → 饼图
        - 多个数值列 → 折线图（按行索引）
        """
        self._current_df = df

        if df.empty or len(df.columns) == 0:
            self.clear()
            return

        self._fig.clear()

        if chart_type == "自动":
            chart_type = self._auto_detect_chart(df)

        self._plot(df, chart_type)
        self._canvas.draw()

    def clear(self):
        """清空图表。"""
        self._fig.clear()
        self._canvas.draw()
        self._current_df = None

    # ── 内部方法 ────────────────────────────────

    def _auto_detect_chart(self, df: pd.DataFrame) -> str:
        """自动判断最合适的图表类型。"""
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        cat_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

        n_num = len(numeric_cols)
        n_cat = len(cat_cols)
        n_rows = len(df)

        if n_num == 0 and n_cat > 0:
            return "饼图"
        elif n_num == 1 and n_cat >= 1:
            return "柱状图"
        elif n_num >= 2 and n_cat >= 1:
            return "分组柱状图"
        elif n_num >= 2:
            if n_rows <= 20:
                return "柱状图"
            else:
                return "折线图"
        elif n_num == 1:
            return "柱状图"
        else:
            return "柱状图"

    def _plot(self, df: pd.DataFrame, chart_type: str):
        """执行实际的绘图操作。"""
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        cat_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

        # 确定分类列（用作 X 轴标签）
        if cat_cols:
            label_col = cat_cols[0]
        elif numeric_cols:
            # 使用第一个数值列作为标签
            label_col = numeric_cols[0]
        else:
            label_col = df.columns[0]

        labels = df[label_col].astype(str).tolist()

        if chart_type == "柱状图":
            ax = self._fig.add_subplot(111)
            if numeric_cols:
                val_col = numeric_cols[0] if label_col in numeric_cols else numeric_cols[0]
                ax.bar(labels, df[val_col].values, color="#4472C4", alpha=0.8)
                ax.set_ylabel(val_col)
            else:
                ax.text(0.5, 0.5, "无可用数值列", transform=ax.transAxes, ha="center")
            ax.set_title("柱状图")
            self._rotate_labels(ax, labels)

        elif chart_type == "分组柱状图":
            ax = self._fig.add_subplot(111)
            plot_cols = [c for c in numeric_cols if c != label_col][:6]  # 最多 6 组
            if plot_cols:
                x = range(len(labels))
                bar_width = 0.8 / len(plot_cols)
                colors = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47"]
                for i, col in enumerate(plot_cols):
                    offset = (i - (len(plot_cols) - 1) / 2) * bar_width
                    ax.bar([xi + offset for xi in x], df[col].values,
                           bar_width, label=col, color=colors[i % len(colors)], alpha=0.85)
                ax.set_xticks(x)
                ax.set_xticklabels(labels)
                ax.legend()
            ax.set_title("分组柱状图")
            self._rotate_labels(ax, labels)

        elif chart_type == "折线图":
            ax = self._fig.add_subplot(111)
            if numeric_cols:
                for i, col in enumerate(numeric_cols[:5]):  # 最多 5 条线
                    ax.plot(labels, df[col].values, marker="o", label=col,
                           linewidth=1.5, markersize=4)
                ax.legend()
            ax.set_title("折线图")
            self._rotate_labels(ax, labels)

        elif chart_type == "饼图":
            ax = self._fig.add_subplot(111)
            if numeric_cols:
                val_col = numeric_cols[0] if label_col in numeric_cols else numeric_cols[0]
                ax.pie(df[val_col].values, labels=labels, autopct="%1.1f%%",
                       startangle=90, colors=plt_colors())
                ax.set_title(f"饼图 - {val_col}")
            else:
                # 值计数饼图
                counts = df[label_col].value_counts()
                ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%",
                       startangle=90, colors=plt_colors())
                ax.set_title(f"饼图 - {label_col}")

        elif chart_type == "散点图":
            ax = self._fig.add_subplot(111)
            if len(numeric_cols) >= 2:
                x_col, y_col = numeric_cols[0], numeric_cols[1]
                ax.scatter(df[x_col].values, df[y_col].values,
                          alpha=0.7, c="#4472C4", edgecolors="white")
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                ax.set_title(f"散点图: {x_col} vs {y_col}")
            else:
                ax.text(0.5, 0.5, "散点图需要至少 2 个数值列",
                       transform=ax.transAxes, ha="center")

        self._fig.tight_layout()

    def _rotate_labels(self, ax, labels: list):
        """如果标签太长则旋转。"""
        max_len = max(len(str(l)) for l in labels) if labels else 0
        if max_len > 5 or len(labels) > 8:
            ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)

    def _on_chart_type_changed(self, chart_type: str):
        """图表类型切换。"""
        if self._current_df is not None:
            self.auto_plot(self._current_df, chart_type)

    def _on_save_chart(self):
        """保存图表为 PNG。"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存图表", "chart.png", "PNG 图片 (*.png);;所有文件 (*.*)"
        )
        if filepath:
            self._fig.savefig(filepath, dpi=150, bbox_inches="tight")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "保存成功", f"图表已保存至:\n{filepath}")


def plt_colors() -> list:
    """返回 matplotlib 配色方案。"""
    return ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47",
            "#264478", "#9E4A1A", "#636363", "#997300"]
