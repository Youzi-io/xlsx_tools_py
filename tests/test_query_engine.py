"""测试 SQL 查询引擎和统计引擎。"""

import unittest

import pandas as pd

from src.core.query_engine import QueryEngine
from src.core.stats_engine import StatsEngine


class TestQueryEngine(unittest.TestCase):
    """查询引擎测试。"""

    @classmethod
    def setUpClass(cls):
        cls.engine = QueryEngine()
        cls.df = pd.DataFrame({
            "姓名": ["张三", "李四", "王五", "赵六", "钱七"],
            "部门": ["技术部", "市场部", "技术部", "市场部", "技术部"],
            "薪资": [15000, 12000, 18000, 10000, 22000],
            "年龄": [28, 32, 25, 40, 29],
        })

    def test_simple_select(self):
        """测试简单 SELECT。"""
        result = self.engine.execute(self.df, "SELECT * FROM df WHERE 薪资 > 15000")
        self.assertEqual(len(result), 2)
        # 薪资 > 15000 的是王五(18000)和钱七(22000)
        self.assertIn("王五", result["姓名"].values)
        self.assertIn("钱七", result["姓名"].values)

    def test_group_by(self):
        """测试 GROUP BY 聚合。"""
        result = self.engine.execute(
            self.df,
            'SELECT 部门, SUM("薪资") as 总薪资 FROM df GROUP BY 部门'
        )
        self.assertEqual(len(result), 2)

    def test_sql_validation(self):
        """测试 SQL 校验。"""
        valid, _ = self.engine.validate(self.df, "SELECT * FROM df")
        self.assertTrue(valid)

        valid, err = self.engine.validate(self.df, "SELECT * FROMM df")
        self.assertFalse(valid)

    def test_build_sql_from_conditions(self):
        """测试条件构建 SQL。"""
        sql = QueryEngine.build_sql_from_conditions(
            table_name="data",
            select_cols=["部门", "薪资"],
            where_conditions=['"薪资" > 12000'],
            group_by_cols=["部门"],
            order_by_cols=[("薪资", "DESC")],
            limit=5,
        )
        self.assertIn("SELECT", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("GROUP BY", sql)
        self.assertIn("ORDER BY", sql)
        self.assertIn("LIMIT 5", sql)

    def test_schema_info(self):
        """测试表结构信息生成。"""
        schema = self.engine.get_schema_info(self.df)
        self.assertIn("CREATE TABLE", schema)
        print(schema)


class TestStatsEngine(unittest.TestCase):
    """统计引擎测试。"""

    @classmethod
    def setUpClass(cls):
        cls.engine = StatsEngine()
        cls.df = pd.DataFrame({
            "姓名": ["张三", "李四", "王五", "赵六", "钱七"],
            "部门": ["技术部", "市场部", "技术部", "市场部", "技术部"],
            "薪资": [15000, 12000, 18000, 10000, 22000],
            "年龄": [28, 32, 25, 40, 29],
        })

    def test_describe(self):
        """测试描述性统计。"""
        result = self.engine.describe(self.df)
        self.assertIn("mean", result.index)
        self.assertGreater(len(result.columns), 0)

    def test_group_by_agg(self):
        """测试分组聚合。"""
        result = self.engine.group_by(
            self.df, by=["部门"], agg={"薪资": "sum"}
        )
        self.assertEqual(len(result), 2)
        # 技术部薪资总和: 15000 + 18000 + 22000 = 55000
        total_tech = result[result["部门"] == "技术部"]["薪资_sum"].values[0] if "薪资_sum" in result.columns else result[result["部门"] == "技术部"]["薪资"].values[0]
        self.assertEqual(total_tech, 55000)

    def test_value_counts(self):
        """测试值计数。"""
        result = self.engine.value_counts(self.df, "部门")
        self.assertEqual(len(result), 2)
        self.assertIn("计数", result.columns)

    def test_top_n(self):
        """测试 Top-N。"""
        result = self.engine.top_n(self.df, "薪资", n=3)
        self.assertEqual(len(result), 3)
        self.assertEqual(result.iloc[0]["姓名"], "钱七")  # 最高薪

    def test_summary_stats(self):
        """测试单列统计摘要。"""
        stats = self.engine.get_summary_stats(self.df, "薪资")
        self.assertEqual(stats["非空数量"], 5)
        self.assertIn("平均值", stats)
        print(stats)

    def test_correlation(self):
        """测试相关性矩阵。"""
        result = self.engine.correlation(self.df)
        self.assertIn("薪资", result.columns)
        self.assertIn("年龄", result.columns)


if __name__ == "__main__":
    unittest.main()
