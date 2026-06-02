from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.querymind.engine import QueryMindEngine, ensure_demo_db
from app.querymind.evaluator import run_eval
from app.querymind.guardrails import validate_read_only_sql


ROOT = Path(__file__).resolve().parents[1]


class QueryMindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "demo.sqlite"
        ensure_demo_db(self.db_path)
        self.engine = QueryMindEngine(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_engine_generates_monthly_revenue(self) -> None:
        result = self.engine.ask("Show monthly revenue for completed orders")
        self.assertIn("strftime", result.sql)
        self.assertEqual(["month", "revenue"], result.columns)
        self.assertGreater(result.row_count, 0)

    def test_engine_handles_city_lookup(self) -> None:
        result = self.engine.ask("List customers in Seattle")
        self.assertIn("customers", result.sql)
        self.assertEqual("Seattle", result.rows[0]["city"])

    def test_guardrails_reject_write_queries(self) -> None:
        ok, message = validate_read_only_sql("DROP TABLE customers;")
        self.assertFalse(ok)
        self.assertIn("SELECT", message)

    def test_eval_cases_pass(self) -> None:
        results = run_eval(ROOT / "data" / "eval_questions.json", engine=self.engine)
        self.assertEqual(1.0, results["accuracy"])


if __name__ == "__main__":
    unittest.main()

