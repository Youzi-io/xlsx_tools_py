"""
统计引擎 — 提供常用的数据统计分析功能。

支持:
- 描述性统计 (count, mean, std, min, 25%, 50%, 75%, max)
- 分组聚合
- 透视表
- 值计数 / 频率分析
- Top-N 排名
- 相关性分析
- 自定义聚合
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
import numpy as np


class StatsEngine:
    """
    统计引擎。

    用法:
        engine = StatsEngine()
        result = engine.group_by(df, by=["部门"], agg={"金额": "sum"})
        freq = engine.value_counts(df, "部门")
    """

    # 支持聚合函数
    AGG_FUNCTIONS = {
        "求和": "sum",
        "平均值": "mean",
        "计数": "count",
        "最大值": "max",
        "最小值": "min",
        "标准差": "std",
        "方差": "var",
        "中位数": "median",
        "去重计数": "nunique",
        "第一项": "first",
        "最后一项": "last",
    }

    def describe(self, df: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        生成描述性统计。

        参数:
            df: 输入 DataFrame
            columns: 要统计的列，None 表示数值列全部统计
        """
        if columns:
            numeric_cols = [c for c in columns if c in df.columns and
                           pd.api.types.is_numeric_dtype(df[c])]
        else:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not numeric_cols:
            return pd.DataFrame({"提示": ["没有可统计的数值列"]})

        return df[numeric_cols].describe()

    def group_by(
        self,
        df: pd.DataFrame,
        by: List[str],
        agg: Dict[str, Union[str, List[str]]],
        sort_by: Optional[str] = None,
        ascending: bool = False,
    ) -> pd.DataFrame:
        """
        分组聚合。

        参数:
            df: 输入 DataFrame
            by: 分组列列表
            agg: 聚合定义，如 {"金额": "sum", "数量": ["mean", "max"]}
            sort_by: 排序列
            ascending: 升序

        示例:
            result = engine.group_by(df, by=["部门"], agg={"金额": "sum"})
        """
        # 验证列存在
        for col in by:
            if col not in df.columns:
                raise ValueError(f"分组列 '{col}' 不存在。")
        for col in agg:
            if col not in df.columns:
                raise ValueError(f"聚合列 '{col}' 不存在。")

        result = df.groupby(by, as_index=False).agg(agg)

        # 扁平化多层列名
        if isinstance(result.columns, pd.MultiIndex):
            result.columns = ["_".join(col).strip("_") for col in result.columns.values]

        if sort_by and sort_by in result.columns:
            result = result.sort_values(sort_by, ascending=ascending)

        return result

    def pivot(
        self,
        df: pd.DataFrame,
        index: str,
        columns: str,
        values: str,
        aggfunc: str = "sum",
    ) -> pd.DataFrame:
        """
        创建透视表。

        参数:
            df: 输入 DataFrame
            index: 行索引列
            columns: 列索引列
            values: 值列
            aggfunc: 聚合函数
        """
        return pd.pivot_table(
            df,
            index=index,
            columns=columns,
            values=values,
            aggfunc=aggfunc,
            fill_value=0,
        )

    def value_counts(
        self,
        df: pd.DataFrame,
        column: str,
        normalize: bool = False,
        top_n: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        频率统计（值计数）。

        参数:
            df: 输入 DataFrame
            column: 统计列
            normalize: 是否返回比例
            top_n: 返回前 N 项
        """
        counts = df[column].value_counts(normalize=normalize).reset_index()
        counts.columns = [column, "频率" if normalize else "计数"]

        if normalize:
            counts["百分比"] = counts["频率"] * 100
            counts["百分比"] = counts["百分比"].round(2)

        if top_n:
            counts = counts.head(top_n)

        return counts

    def correlation(self, df: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        计算列之间的相关系数矩阵。

        参数:
            df: 输入 DataFrame
            columns: 要分析的列，None 表示所有数值列
        """
        if columns:
            numeric_cols = [c for c in columns if c in df.columns and
                           pd.api.types.is_numeric_dtype(df[c])]
        else:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) < 2:
            return pd.DataFrame({"提示": ["需要至少 2 个数值列"]})

        corr_matrix = df[numeric_cols].corr()
        return corr_matrix.round(4)

    def top_n(
        self,
        df: pd.DataFrame,
        column: str,
        n: int = 10,
        ascending: bool = False,
    ) -> pd.DataFrame:
        """
        Top-N 排名。

        参数:
            df: 输入 DataFrame
            column: 排序列
            n: 返回行数
            ascending: True 为升序（最小 Top-N），False 为降序（最大 Top-N）
        """
        return df.nlargest(n, column) if not ascending else df.nsmallest(n, column)

    def custom_aggregate(
        self,
        df: pd.DataFrame,
        group_by_cols: List[str],
        agg_col: str,
        agg_funcs: List[str],
    ) -> pd.DataFrame:
        """
        对指定列应用多种聚合函数。

        参数:
            df: 输入 DataFrame
            group_by_cols: 分组列
            agg_col: 聚合列
            agg_funcs: 聚合函数名列表，如 ["sum", "mean", "count"]
        """
        # 将中文函数名转为 pandas 函数名
        mapped_funcs = [self.AGG_FUNCTIONS.get(f, f) for f in agg_funcs]

        result = df.groupby(group_by_cols, as_index=False)[agg_col].agg(mapped_funcs)

        # 重命名列
        new_cols = [f"{agg_col}_{f}" for f in agg_funcs]
        rename_map = {old: new for old, new in zip(
            [f"{agg_col}_{f}" for f in mapped_funcs], new_cols
        )}
        # 仅在列名不同时重命名
        result.columns = [rename_map.get(c, c) for c in result.columns]

        return result

    def get_summary_stats(self, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """
        获取单列的统计摘要。

        返回: {count, mean, std, min, max, sum, median, mode, null_count, null_pct}
        """
        series = df[column]
        numeric = pd.api.types.is_numeric_dtype(series)

        stats = {
            "列名": column,
            "非空数量": int(series.count()),
            "空值数量": int(series.isna().sum()),
            "空值比例": round(series.isna().sum() / len(series), 4) if len(series) > 0 else 0,
            "去重数量": int(series.nunique()),
        }

        if numeric:
            stats.update({
                "平均值": round(series.mean(), 4),
                "标准差": round(series.std(), 4),
                "最小值": series.min(),
                "25%分位": round(series.quantile(0.25), 4),
                "中位数": round(series.median(), 4),
                "75%分位": round(series.quantile(0.75), 4),
                "最大值": series.max(),
                "总和": series.sum(),
            })
        else:
            # 字符串列
            try:
                stats["众数"] = series.mode().iloc[0] if not series.mode().empty else None
            except Exception:
                stats["众数"] = None

        return stats
