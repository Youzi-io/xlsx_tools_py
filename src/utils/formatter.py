"""数据格式化工具 — 列名清理、类型推断、数据摘要生成。"""

import re
from datetime import datetime, date
from typing import Any


def sanitize_column_name(name: Any) -> str:
    """
    清理列名：去掉换行/首尾空格/多余空格，统一为适合 pandas 和 SQL 的格式。
    """
    if name is None:
        return "Unnamed"
    s = str(name).strip()
    # 替换换行符和制表符为空格
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # 压缩多个空格
    s = re.sub(r"\s+", " ", s)
    # 如果清理后为空，返回默认名
    if not s:
        return "Unnamed"
    return s


def flatten_header(hierarchy_parts: list[str], separator: str = "_") -> str:
    """
    将层级表头扁平化为单个列名。

    例: ["2024年度", "Q1", "收入"] → "2024年度_Q1_收入"
    空字符串或 None 会自动跳过。
    """
    parts = [sanitize_column_name(p) for p in hierarchy_parts if p]
    parts = [p for p in parts if p and p != "Unnamed"]
    if not parts:
        return "Column"
    return separator.join(parts)


def infer_column_type(values: list) -> str:
    """
    推断列的数据类型。返回: 'numeric', 'datetime', 'string', 'boolean', 'mixed'
    """
    non_null = [v for v in values if v is not None]

    if not non_null:
        return "string"

    type_counts = {"numeric": 0, "datetime": 0, "boolean": 0, "string": 0}
    total = len(non_null)

    for v in non_null:
        if isinstance(v, (int, float)):
            type_counts["numeric"] += 1
        elif isinstance(v, (datetime, date)):
            type_counts["datetime"] += 1
        elif isinstance(v, bool):
            type_counts["boolean"] += 1
        else:
            # 尝试解析
            s = str(v).strip()
            if re.match(r"^-?\d+\.?\d*$", s):
                type_counts["numeric"] += 1
            elif re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", s):
                type_counts["datetime"] += 1
            elif s.lower() in ("true", "false", "yes", "no", "是", "否"):
                type_counts["boolean"] += 1
            else:
                type_counts["string"] += 1

    # 如果某类型超过 60%，判定为该类型
    for t in ["numeric", "datetime", "boolean", "string"]:
        if type_counts[t] / total >= 0.6:
            return t

    return "mixed"


def format_bytes(size_bytes: int) -> str:
    """将字节数格式化为人类可读的大小。"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
