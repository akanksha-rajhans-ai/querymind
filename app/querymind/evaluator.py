"""Simple deterministic evaluation for MVP text-to-SQL quality."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from app.querymind.engine import QueryMindEngine


@dataclass(frozen=True)
class EvalCaseResult:
    case_id: str
    question: str
    passed: bool
    sql_score: float
    column_score: float
    generated_sql: str
    expected_sql_contains: List[str]
    expected_columns: List[str]
    row_count: int
    error: str = ""


def run_eval(cases_path: Path, engine: QueryMindEngine | None = None) -> Dict[str, Any]:
    engine = engine or QueryMindEngine()
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    results: List[EvalCaseResult] = []

    for case in cases:
        try:
            result = engine.ask(case["question"])
            generated_sql = result.sql
            sql_score = _contains_score(generated_sql, case["expected_sql_contains"])
            column_score = _contains_score(" ".join(result.columns), case["expected_columns"])
            passed = sql_score == 1.0 and column_score == 1.0 and result.row_count > 0
            results.append(
                EvalCaseResult(
                    case_id=case["id"],
                    question=case["question"],
                    passed=passed,
                    sql_score=sql_score,
                    column_score=column_score,
                    generated_sql=generated_sql,
                    expected_sql_contains=case["expected_sql_contains"],
                    expected_columns=case["expected_columns"],
                    row_count=result.row_count,
                )
            )
        except Exception as exc:  # noqa: BLE001 - eval should report all failures
            results.append(
                EvalCaseResult(
                    case_id=case["id"],
                    question=case["question"],
                    passed=False,
                    sql_score=0.0,
                    column_score=0.0,
                    generated_sql="",
                    expected_sql_contains=case["expected_sql_contains"],
                    expected_columns=case["expected_columns"],
                    row_count=0,
                    error=str(exc),
                )
            )

    passed = sum(1 for result in results if result.passed)
    total = len(results)
    return {
        "accuracy": round(passed / total, 3) if total else 0.0,
        "passed": passed,
        "total": total,
        "results": [asdict(result) for result in results],
    }


def _contains_score(actual: str, expected_fragments: List[str]) -> float:
    if not expected_fragments:
        return 1.0
    normalized_actual = actual.lower()
    hits = sum(1 for fragment in expected_fragments if fragment.lower() in normalized_actual)
    return round(hits / len(expected_fragments), 3)

