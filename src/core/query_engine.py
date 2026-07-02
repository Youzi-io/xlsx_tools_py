"""
SQL 查询引擎 — 基于 duckdb 直接对 pandas DataFrame 执行 SQL 查询。

优势:
- 零配置，无需启动数据库服务
- 支持标准 SQL: SELECT, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, JOIN
- 支持窗口函数、子查询
- 列名自动处理特殊字符（用双引号包裹）
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd


class QueryEngine:
    """
    SQL 查询引擎。

    用法:
        engine = QueryEngine()
        result = engine.execute(df, "SELECT 部门, SUM(金额) FROM df GROUP BY 部门")
        # 或使用 SQL 中的占位符表名 'data'
        result = engine.execute(df, "SELECT * FROM data WHERE 金额 > 1000")
    """

    # 默认的 DataFrame 注册名
    DEFAULT_TABLE = "data"

    def __init__(self):
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._last_result: Optional[pd.DataFrame] = None
        self._last_sql: str = ""

    def execute(self, df: pd.DataFrame, sql: str,
                db_store=None) -> pd.DataFrame:
        """
        执行 SQL 查询。

        参数:
            df: 源 DataFrame
            sql: SQL 查询语句。表名使用 'data' 或数据库中的表名。
            db_store: 可选 DatabaseStore，传入后可查询持久化表。
        """
        sql = self._preprocess_sql(sql, df, db_store)

        try:
            if db_store is not None:
                con = duckdb.connect(db_store.db_path)
            else:
                con = duckdb.connect()

            # 仅当 DataFrame 有列时才注册 data 表
            if len(df.columns) > 0:
                con.register(self.DEFAULT_TABLE, df)

            result = con.execute(sql).fetchdf()
            con.close()
        except Exception as e:
            raise ValueError("SQL 执行失败:\n{}\n\n错误: {}".format(sql, e)) from e

        self._last_result = result
        self._last_sql = sql
        return result

    def validate(self, df: pd.DataFrame, sql: str,
                 db_store=None) -> Tuple[bool, str]:
        """验证 SQL 语句是否合法。"""
        try:
            sql = self._preprocess_sql(sql, df, db_store)
            if db_store is not None:
                con = duckdb.connect(db_store.db_path)
            else:
                con = duckdb.connect()
            if len(df.columns) > 0:
                con.register(self.DEFAULT_TABLE, df)
            con.execute("EXPLAIN {}".format(sql))
            con.close()
            return True, ""
        except Exception as e:
            return False, str(e)

    def get_schema_info(self, df: pd.DataFrame) -> str:
        """
        生成表结构信息（用于展示给用户参考）。

        返回类似:
            CREATE TABLE data (
                "姓名" VARCHAR,
                "部门" VARCHAR,
                "Q1收入" DOUBLE,
                ...
            );
        """
        lines = [f"-- 表名: {self.DEFAULT_TABLE}"]
        lines.append(f"-- 行数: {len(df)}")
        lines.append(f"CREATE TABLE {self.DEFAULT_TABLE} (")

        type_map = {
            "object": "VARCHAR",
            "int64": "BIGINT",
            "float64": "DOUBLE",
            "bool": "BOOLEAN",
            "datetime64[ns]": "TIMESTAMP",
        }

        for col in df.columns:
            dtype = str(df[col].dtype)
            sql_type = type_map.get(dtype, "VARCHAR")
            # 列名用双引号包裹以处理中文和特殊字符
            lines.append(f'    "{col}" {sql_type},')

        # 去掉最后一个逗号
        lines[-1] = lines[-1].rstrip(",")
        lines.append(");")

        # 添加示例查询
        lines.append("")
        lines.append("-- 示例查询:")
        sample_col = df.columns[0] if len(df.columns) > 0 else "*"
        lines.append(f'SELECT "{sample_col}", COUNT(*) FROM {self.DEFAULT_TABLE} GROUP BY "{sample_col}";')

        return "\n".join(lines)

    def get_schema_info_with_db(self, df: pd.DataFrame, db_store=None) -> str:
        """
        生成包含持久化表的完整 Schema 信息。
        """
        lines = []

        # 当前内存表
        lines.append("-- ========================")
        lines.append("-- 当前表: data ({} 行)".format(len(df)))
        lines.append("-- ========================")
        type_map = {
            "object": "VARCHAR", "int64": "BIGINT", "float64": "DOUBLE",
            "bool": "BOOLEAN", "datetime64[ns]": "TIMESTAMP",
        }
        for col in df.columns:
            dtype = str(df[col].dtype)
            sql_type = type_map.get(dtype, "VARCHAR")
            lines.append('--   "{}"  {}'.format(col, sql_type))

        # 持久化表
        if db_store is not None:
            datasets = db_store.list_datasets()
            if datasets:
                lines.append("--")
                lines.append("-- ========================")
                lines.append("-- 持久化表 (可直接查询):")
                lines.append("-- ========================")
                for ds in datasets:
                    lines.append('--   {}  ({} 行 x {} 列)'.format(
                        ds["name"], ds["rows"], ds["cols"]
                    ))
                lines.append("--")
                lines.append("-- 示例: SELECT * FROM {} WHERE ...".format(
                    datasets[0]["name"] if datasets else "table_name"
                ))
                lines.append("-- JOIN 示例: SELECT * FROM data JOIN {} ON ...".format(
                    datasets[0]["name"] if datasets else "table_name"
                ))

        return "\n".join(lines)

    def get_last_result(self) -> Optional[pd.DataFrame]:
        """获取上次查询结果。"""
        return self._last_result

    def get_last_sql(self) -> str:
        """获取上次执行的 SQL。"""
        return self._last_sql

    # ── 内部方法 ────────────────────────────────

    def _preprocess_sql(self, sql: str, df: pd.DataFrame,
                        db_store=None) -> str:
        """
        预处理 SQL，修复常见的用户书写错误:
        1. 双引号字符串值 → 单引号（"广州分公司" → '广州分公司'）
           双引号在 SQL 中表示标识符(列名)，字符串值必须用单引号
        """
        # 收集所有已知列名：当前DataFrame + 数据库中的表
        column_names = set(df.columns)
        table_names = set()

        if db_store is not None:
            for ds in db_store.list_datasets():
                table_names.add(ds["name"])
                table_names.add(ds["table_name"])

        def replace_double_quoted_string(match):
            content = match.group(1)
            # 列名或表名 → 保留双引号
            if content in column_names or content in table_names:
                return '"{}"'.format(content)
            # 否则是字符串字面量 → 单引号
            return "'{}'".format(content)

        sql = re.sub(r'"([^"]*)"', replace_double_quoted_string, sql)

        return sql

    @staticmethod
    def build_sql_from_conditions(
        table_name: str,
        select_cols: List[str],
        where_conditions: List[str],
        group_by_cols: Optional[List[str]] = None,
        having_conditions: Optional[List[str]] = None,
        order_by_cols: Optional[List[Tuple[str, str]]] = None,
        limit: Optional[int] = None,
    ) -> str:
        """
        从结构化条件构建 SQL 语句。

        参数:
            table_name: 表名
            select_cols: SELECT 列列表
            where_conditions: WHERE 条件列表
            group_by_cols: GROUP BY 列列表
            having_conditions: HAVING 条件列表
            order_by_cols: ORDER BY [(列名, "ASC"|"DESC")]
            limit: LIMIT 数量
        """
        # SELECT
        select = ", ".join(f'"{c}"' for c in select_cols) if select_cols else "*"
        sql = f"SELECT {select} FROM {table_name}"

        # WHERE
        if where_conditions:
            sql += " WHERE " + " AND ".join(where_conditions)

        # GROUP BY
        if group_by_cols:
            sql += " GROUP BY " + ", ".join(f'"{c}"' for c in group_by_cols)

        # HAVING
        if having_conditions:
            sql += " HAVING " + " AND ".join(having_conditions)

        # ORDER BY
        if order_by_cols:
            parts = [f'"{c}" {direction}' for c, direction in order_by_cols]
            sql += " ORDER BY " + ", ".join(parts)

        # LIMIT
        if limit is not None:
            sql += f" LIMIT {limit}"

        return sql
