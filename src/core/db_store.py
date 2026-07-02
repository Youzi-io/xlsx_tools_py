"""
数据库存储层 — 基于 duckdb 持久化存储导入的数据集。

每个数据集存为独立表，元数据记录在 _datasets 表中。
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import duckdb
import pandas as pd


class DatabaseStore:
    """
    本地数据库存储。

    用法:
        store = DatabaseStore("xlsx_tools_data.db")
        store.save_dataset("公司人员", df, "公司人员表.xlsx", "Sheet1")
        df = store.load_dataset("公司人员")
        store.delete_dataset("公司人员")
        datasets = store.list_datasets()
    """

    META_TABLE = "_datasets"
    TABLE_PREFIX = ""

    def __init__(self, db_path: str = None):
        if db_path is None:
            import sys
            if getattr(sys, 'frozen', False):
                # onefile 模式：数据库放在 exe 同目录
                exe_dir = os.path.dirname(os.path.abspath(sys.executable))
                db_path = os.path.join(exe_dir, "xlsx_tools_data.db")
            else:
                db_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "..",
                    "xlsx_tools_data.db"
                )
        self.db_path = os.path.abspath(db_path)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._init_db()

    # ── 初始化 ──────────────────────────────────

    def _init_db(self):
        """初始化数据库，创建元数据表。"""
        self._ensure_conn()
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS {} (
                name VARCHAR PRIMARY KEY,
                table_name VARCHAR NOT NULL,
                source_file VARCHAR,
                sheet_name VARCHAR,
                rows INTEGER,
                cols INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """.format(self.META_TABLE))

    def _ensure_conn(self):
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── 名称规范化 ──────────────────────────────

    @staticmethod
    def _sanitize_table_name(name: str) -> str:
        """将数据集名转为合法的 SQL 表名。"""
        # 保留中文、字母、数字、下划线
        s = re.sub(r'[^\w一-鿿]', '_', name)
        s = re.sub(r'_+', '_', s).strip('_')
        if not s:
            s = "unnamed"
        return DatabaseStore.TABLE_PREFIX + s

    # ── CRUD 操作 ───────────────────────────────

    def save_dataset(self, name: str, df: pd.DataFrame,
                     source_file: str = "", sheet_name: str = "") -> None:
        """
        保存数据集到数据库。

        参数:
            name: 数据集名称（用户自定义）
            df: 要保存的 DataFrame
            source_file: 来源文件名
            sheet_name: 来源 Sheet 名
        """
        self._ensure_conn()
        table_name = self._sanitize_table_name(name)

        # 如果已存在同名，先删除
        if self.exists(name):
            self.delete_dataset(name)

        # 注册并创建表
        self._conn.register("__temp_df", df)
        self._conn.execute(
            'CREATE TABLE "{}" AS SELECT * FROM __temp_df'.format(table_name)
        )
        self._conn.unregister("__temp_df")

        # 记录元数据
        self._conn.execute(
            "INSERT INTO {} (name, table_name, source_file, sheet_name, rows, cols) "
            "VALUES (?, ?, ?, ?, ?, ?)".format(self.META_TABLE),
            [name, table_name, source_file, sheet_name, len(df), len(df.columns)]
        )

    def load_dataset(self, name: str) -> pd.DataFrame:
        """
        从数据库加载数据集。

        返回: pandas DataFrame
        """
        self._ensure_conn()

        meta = self._get_meta(name)
        if not meta:
            raise ValueError("数据集 '{}' 不存在。".format(name))

        return self._conn.execute(
            'SELECT * FROM "{}"'.format(meta["table_name"])
        ).fetchdf()

    def delete_dataset(self, name: str) -> None:
        """删除数据集。"""
        self._ensure_conn()

        meta = self._get_meta(name)
        if not meta:
            return

        # 删除数据表
        self._conn.execute(
            'DROP TABLE IF EXISTS "{}"'.format(meta["table_name"])
        )
        # 删除元数据
        self._conn.execute(
            "DELETE FROM {} WHERE name = ?".format(self.META_TABLE),
            [name]
        )

    def list_datasets(self) -> List[dict]:
        """
        列出所有已保存的数据集。

        返回: [{name, table_name, source_file, sheet_name, rows, cols, created_at}, ...]
        """
        self._ensure_conn()
        rows = self._conn.execute(
            "SELECT name, table_name, source_file, sheet_name, rows, cols, created_at "
            "FROM {} ORDER BY created_at DESC".format(self.META_TABLE)
        ).fetchall()

        return [
            {
                "name": r[0],
                "table_name": r[1],
                "source_file": r[2],
                "sheet_name": r[3],
                "rows": r[4],
                "cols": r[5],
                "created_at": r[6],
            }
            for r in rows
        ]

    def exists(self, name: str) -> bool:
        """检查数据集是否已存在。"""
        return self._get_meta(name) is not None

    def rename_dataset(self, old_name: str, new_name: str) -> None:
        """重命名数据集。"""
        self._ensure_conn()
        meta = self._get_meta(old_name)
        if not meta:
            raise ValueError("数据集 '{}' 不存在。".format(old_name))

        # 更新元数据
        self._conn.execute(
            "UPDATE {} SET name = ? WHERE name = ?".format(self.META_TABLE),
            [new_name, old_name]
        )

    # ── 内部方法 ────────────────────────────────

    def _get_meta(self, name: str) -> Optional[dict]:
        """获取数据集元数据。"""
        self._ensure_conn()
        rows = self._conn.execute(
            "SELECT name, table_name, source_file, sheet_name, rows, cols, created_at "
            "FROM {} WHERE name = ?".format(self.META_TABLE),
            [name]
        ).fetchall()

        if not rows:
            return None
        r = rows[0]
        return {
            "name": r[0],
            "table_name": r[1],
            "source_file": r[2],
            "sheet_name": r[3],
            "rows": r[4],
            "cols": r[5],
            "created_at": r[6],
        }
