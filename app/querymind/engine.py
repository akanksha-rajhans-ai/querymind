"""QueryMind orchestration: schema loading, generation, guardrails, execution."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

from app.querymind.guardrails import normalize_sql, validate_read_only_sql
from app.querymind.introspection import SQLiteIntrospector
from app.querymind.models import QueryResult, SchemaContext
from app.querymind.translator import TextToSQLTranslator
from app.querymind.prompt_builder import build_repair_prompt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "querymind_demo.sqlite"
DEMO_SQL_PATH = ROOT / "data" / "demo_ecommerce.sql"


def ensure_demo_db(db_path: Path = DEFAULT_DB_PATH) -> Path:
    db_path = Path(db_path)
    if db_path.exists():
        return db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    sql = DEMO_SQL_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(sql)
        conn.commit()
    return db_path


class QueryMindEngine:
    def __init__(self, db_path: Path | str | None = None):
        configured_path = db_path or os.getenv("QUERYMIND_DB_PATH") or DEFAULT_DB_PATH
        self.db_path = ensure_demo_db(Path(configured_path))
        self.schema: SchemaContext = SQLiteIntrospector(self.db_path).load_schema()
        self.translator = TextToSQLTranslator(self.schema)

    def ask(self, question: str, max_rows: int = 50) -> QueryResult:
        started = time.perf_counter()
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("Question is required.")

        candidate = self.translator.generate(cleaned_question)
        sql = normalize_sql(candidate.sql)
        ok, message = validate_read_only_sql(sql)
        if not ok:
            raise ValueError(message)

        repair_attempted = False
        repair_succeeded = False
        original_sql = ""
        repair_error = ""

        try:
            columns, rows = self._execute(sql, max_rows=max_rows)
        except sqlite3.Error as exc:
            if candidate.source != "gemini":
                raise

            repair_attempted = True
            original_sql = sql
            repair_error = str(exc)

            repair_prompt = build_repair_prompt(
                question=cleaned_question,
                failed_sql=sql,
                error_message=repair_error,
                schema=self.schema,
                retrieved_tables=candidate.retrieved_tables,
            )

            repaired_sql = self.translator.llm_provider.repair_sql(repair_prompt)

            ok, message = validate_read_only_sql(repaired_sql)
            if not ok:
                raise ValueError(f"Repaired SQL failed guardrails: {message}")

            sql = normalize_sql(repaired_sql)
            columns, rows = self._execute(sql, max_rows=max_rows)
            repair_succeeded = True

        elapsed = int((time.perf_counter() - started) * 1000)

        return QueryResult(
            question=cleaned_question,
            sql=sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            rationale=candidate.rationale,
            retrieved_tables=candidate.retrieved_tables,
            confidence=candidate.confidence,
            source=candidate.source,
            fallback_reason=candidate.fallback_reason,
            latency_ms=elapsed,
            repair_attempted=repair_attempted,
            repair_succeeded=repair_succeeded,
            original_sql=original_sql,
            repair_error=repair_error,
        )

    def schema_summary(self) -> Dict[str, Any]:
        return {
            "database": str(self.db_path),
            "tables": [
                {
                    "name": table.name,
                    "row_count": table.row_count,
                    "columns": [
                        {
                            "name": column.name,
                            "type": column.data_type,
                            "nullable": column.nullable,
                            "primary_key": column.primary_key,
                        }
                        for column in table.columns
                    ],
                    "foreign_keys": [
                        {
                            "column": key.column,
                            "references": f"{key.referenced_table}.{key.referenced_column}",
                        }
                        for key in table.foreign_keys
                    ],
                }
                for table in self.schema.tables.values()
            ],
        }

    @staticmethod
    def example_questions() -> List[str]:
        return [
            "Show monthly revenue for completed orders",
            "Which product categories generated the most revenue?",
            "Who are the top 5 customers by spend?",
            "How many orders do we have by status?",
            "Which shipments are still in transit?",
            "List customers in Seattle",
            "Show open support tickets by priority",
        ]

    def _execute(self, sql: str, max_rows: int) -> tuple[List[str], List[Dict[str, Any]]]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            columns = [description[0] for description in cursor.description or []]
            fetched = cursor.fetchmany(max_rows)
        return columns, [dict(row) for row in fetched]

