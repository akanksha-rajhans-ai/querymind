from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.querymind.engine import QueryMindEngine, ensure_demo_db
from app.querymind.evaluator import run_eval
from app.querymind.guardrails import validate_read_only_sql
from app.querymind.models import SQLCandidate


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

    def test_repairs_failed_gemini_sql(self) -> None:
        def fake_generate(question: str) -> SQLCandidate:
            return SQLCandidate(
                sql="SELECT missing_column FROM customers;",
                rationale="Fake Gemini generated invalid SQL.",
                retrieved_tables=[],
                confidence=0.78,
                source="gemini",
                fallback_reason="",
            )

        class FakeRepairProvider:
            def __init__(self) -> None:
                self.prompt = ""

            def repair_sql(self, prompt: str) -> str:
                self.prompt = prompt
                return """
                SELECT
                    full_name AS customer,
                    email,
                    city
                FROM customers
                ORDER BY full_name
                LIMIT 3;
                """

        fake_provider = FakeRepairProvider()

        self.engine.translator.generate = fake_generate
        self.engine.translator.llm_provider = fake_provider

        result = self.engine.ask("List customers")

        self.assertTrue(result.repair_attempted)
        self.assertTrue(result.repair_succeeded)
        self.assertEqual("SELECT missing_column FROM customers;", result.original_sql)
        self.assertIn("missing_column", result.repair_error)
        self.assertIn("full_name AS customer", result.sql)
        self.assertEqual(3, result.row_count)
        self.assertIn("SELECT missing_column FROM customers;", fake_provider.prompt)


if __name__ == "__main__":
    unittest.main()

