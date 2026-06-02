"""SQLite schema introspection used for grounding and retrieval."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Iterable

from app.querymind.models import ColumnInfo, ForeignKeyInfo, SchemaContext, TableInfo


class SQLiteIntrospector:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def load_schema(self) -> SchemaContext:
        with sqlite3.connect(str(self.db_path)) as conn:
            table_names = list(self._table_names(conn))
            tables: Dict[str, TableInfo] = {}
            for name in table_names:
                tables[name] = TableInfo(
                    name=name,
                    columns=self._columns(conn, name),
                    foreign_keys=self._foreign_keys(conn, name),
                    row_count=self._row_count(conn, name),
                )
        return SchemaContext(tables=tables)

    @staticmethod
    def _table_names(conn: sqlite3.Connection) -> Iterable[str]:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        return [row[0] for row in rows]

    @staticmethod
    def _columns(conn: sqlite3.Connection, table_name: str) -> list[ColumnInfo]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [
            ColumnInfo(
                name=row[1],
                data_type=row[2] or "TEXT",
                nullable=not bool(row[3]),
                primary_key=bool(row[5]),
            )
            for row in rows
        ]

    @staticmethod
    def _foreign_keys(conn: sqlite3.Connection, table_name: str) -> list[ForeignKeyInfo]:
        rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
        return [
            ForeignKeyInfo(
                column=row[3],
                referenced_table=row[2],
                referenced_column=row[4],
            )
            for row in rows
        ]

    @staticmethod
    def _row_count(conn: sqlite3.Connection, table_name: str) -> int:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])

