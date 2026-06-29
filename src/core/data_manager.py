"""
数据管理器 — 管理 pandas DataFrame 的完整生命周期。

负责:
- 将 xlsx 数据加载为 pandas DataFrame
- 使用 HeaderDetector 识别的列名作为 DataFrame columns
- 提供数据摘要、列类型、预览等功能
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.core.xlsx_reader import XlsxReader, FileInfo
from src.core.header_detector import HeaderDetector, HeaderInfo, ColumnDef
from src.utils.merger import expand_merged_value


class DataManager:
    """
    数据管理器。

    用法:
        dm = DataManager()
        dm.load("data.xlsx", "Sheet1")
        df = dm.get_dataframe()
        info = dm.get_header_info()
    """

    def __init__(self):
        self._reader: Optional[XlsxReader] = None
        self._header_info: Optional[HeaderInfo] = None
        self._dataframe: Optional[pd.DataFrame] = None
        self._current_filepath: Optional[str] = None
        self._current_sheet: Optional[str] = None

    # ── 加载 ────────────────────────────────────

    def load(self, filepath: str, sheet_name: str = None) -> pd.DataFrame:
        """
        加载 xlsx 文件并解析为 DataFrame。

        参数:
            filepath: xlsx 文件路径
            sheet_name: Sheet 名称，为 None 时使用第一个 Sheet
        """
        self._reader = XlsxReader(filepath)
        self._reader.open()
        self._current_filepath = filepath

        # 选择 Sheet
        available = self._reader.get_sheet_names()
        if sheet_name is None:
            sheet_name = available[0]
        if sheet_name not in available:
            raise ValueError(f"Sheet '{sheet_name}' 不存在。可用: {available}")

        self._current_sheet = sheet_name
        ws = self._reader.select_sheet(sheet_name)

        # 检测表头
        detector = HeaderDetector(ws)
        self._header_info = detector.detect()

        # 读取数据行
        data_start = self._header_info.data_start_row + 1  # data_start_row 是 0-based
        raw_data = self._reader.read_data_rows(data_start)

        # 构建 DataFrame
        if not raw_data:
            # 空数据
            self._dataframe = pd.DataFrame(columns=[c.flat_name for c in self._header_info.columns])
        else:
            self._dataframe = pd.DataFrame(raw_data)
            # 设置列名
            col_names = [c.flat_name for c in self._header_info.columns]
            # 处理列数不匹配
            if len(col_names) < len(self._dataframe.columns):
                col_names += [f"Column_{i}" for i in range(len(col_names), len(self._dataframe.columns))]
            elif len(col_names) > len(self._dataframe.columns):
                col_names = col_names[:len(self._dataframe.columns)]

            self._dataframe.columns = col_names

            # 类型转换：尝试将数值列转为 numeric
            self._auto_convert_types()

        return self._dataframe

    def reload_with_header_rows(self, header_row_count: int) -> pd.DataFrame:
        """
        使用指定的表头行数重新加载数据（允许用户手动调整）。
        """
        if self._reader is None:
            raise RuntimeError("请先调用 load() 加载文件。")

        ws = self._reader.get_active_sheet()
        detector = HeaderDetector(ws)
        # 手动设置表头行为前 N 行
        # 这里简单重建 header_info
        header_info = detector.detect()

        # 重写 header_rows 为指定的数量
        if header_row_count > 0:
            header_info = HeaderInfo(
                header_rows=list(range(header_row_count)),
                data_start_row=header_row_count,
                columns=header_info.columns,
                total_rows=header_info.total_rows,
                total_cols=header_info.total_cols,
                sheet_name=header_info.sheet_name,
                confidence=1.0  # 手动指定，置信度为 1
            )
            # 重新构建列
            columns = detector._build_column_defs(
                list(range(1, header_row_count + 1))
            )
            header_info.columns = columns

        self._header_info = header_info

        # 重新读取数据
        data_start = header_info.data_start_row + 1
        raw_data = self._reader.read_data_rows(data_start)
        col_names = [c.flat_name for c in header_info.columns]

        if not raw_data:
            self._dataframe = pd.DataFrame(columns=col_names)
        else:
            self._dataframe = pd.DataFrame(raw_data)
            if len(col_names) < len(self._dataframe.columns):
                col_names += [f"Column_{i}" for i in range(len(col_names), len(self._dataframe.columns))]
            else:
                col_names = col_names[:len(self._dataframe.columns)]
            self._dataframe.columns = col_names
            self._auto_convert_types()

        return self._dataframe

    # ── 查询 ────────────────────────────────────

    def get_dataframe(self) -> pd.DataFrame:
        """获取当前 DataFrame。"""
        if self._dataframe is None:
            raise RuntimeError("未加载数据。请先调用 load()。")
        return self._dataframe

    def get_header_info(self) -> HeaderInfo:
        """获取表头信息。"""
        if self._header_info is None:
            raise RuntimeError("未加载数据。请先调用 load()。")
        return self._header_info

    def get_columns(self) -> List[str]:
        """获取所有列名。"""
        return list(self.get_dataframe().columns)

    def get_dtypes(self) -> Dict[str, str]:
        """获取每列的数据类型。"""
        df = self.get_dataframe()
        return {col: str(dtype) for col, dtype in df.dtypes.items()}

    def get_summary(self) -> Dict[str, Any]:
        """获取数据摘要。"""
        df = self.get_dataframe()
        header = self.get_header_info()

        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        completeness = 1 - (missing_cells / total_cells) if total_cells > 0 else 1

        return {
            "rows": len(df),
            "cols": len(df.columns),
            "total_cells": total_cells,
            "missing_cells": int(missing_cells),
            "completeness": round(completeness, 4),
            "header_rows": len(header.header_rows),
            "header_confidence": round(header.confidence, 4),
            "column_types": self._summarize_types(),
            "memory_usage": df.memory_usage(deep=True).sum(),
        }

    def get_preview(self, n_rows: int = 50) -> pd.DataFrame:
        """获取数据预览（前 N 行）。"""
        return self.get_dataframe().head(n_rows)

    def get_sheet_names(self) -> List[str]:
        """获取 xlsx 文件中所有 Sheet 名称。"""
        if self._reader is None:
            raise RuntimeError("未加载文件。")
        return self._reader.get_sheet_names()

    def get_file_info(self) -> FileInfo:
        """获取文件信息。"""
        if self._reader is None:
            raise RuntimeError("未加载文件。")
        return self._reader.get_file_info()

    def close(self):
        """关闭并释放资源。"""
        if self._reader:
            self._reader.close()

    # ── 内部方法 ────────────────────────────────

    def _auto_convert_types(self):
        """自动将合适的列转换为数值类型。"""
        for col in self._dataframe.columns:
            try:
                self._dataframe[col] = pd.to_numeric(self._dataframe[col], errors="ignore")
            except Exception:
                pass

    def _summarize_types(self) -> Dict[str, int]:
        """统计列类型分布。"""
        df = self._dataframe
        type_map = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            type_map[dtype] = type_map.get(dtype, 0) + 1
        return type_map
