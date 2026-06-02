"""Run QueryMind MVP evaluation cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.querymind.evaluator import run_eval  # noqa: E402


def main() -> None:
    results = run_eval(ROOT / "data" / "eval_questions.json")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
