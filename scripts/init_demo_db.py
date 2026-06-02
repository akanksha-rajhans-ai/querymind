"""Create the local QueryMind demo SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "demo_ecommerce.sql"
DEFAULT_DB_PATH = ROOT / "data" / "querymind_demo.sqlite"


def create_demo_db(db_path: Path = DEFAULT_DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(sql)
        conn.commit()
    return db_path


def main() -> None:
    db_path = create_demo_db()
    print(f"Created demo database at {db_path}")


if __name__ == "__main__":
    main()

