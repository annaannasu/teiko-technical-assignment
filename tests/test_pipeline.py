import sqlite3
import unittest
from pathlib import Path

import pandas as pd

from analysis import statistical_tests

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / "cell_counts.db").exists():
            import load_data
            load_data.main()

    def test_five_populations_per_sample_and_percentages_sum_to_100(self):
        with sqlite3.connect(ROOT / "cell_counts.db") as connection:
            result = pd.read_sql_query("""
                SELECT sample, COUNT(*) n, SUM(percentage) pct
                FROM cell_frequency_summary GROUP BY sample
            """, connection)
        self.assertTrue((result.n == 5).all())
        self.assertTrue(((result.pct - 100).abs() < 1e-8).all())

    def test_statistical_output_covers_all_populations(self):
        from analysis import trial_frequencies
        with sqlite3.connect(ROOT / "cell_counts.db") as connection:
            result = statistical_tests(trial_frequencies(connection))
        self.assertEqual(len(result), 5)
        self.assertTrue(result.p_value_bh.between(0, 1).all())
        self.assertIn("welch_t_statistic", result.columns)


if __name__ == "__main__":
    unittest.main()
