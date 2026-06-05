"""Shared data models for the QueryMind MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool
    primary_key: bool


@dataclass(frozen=True)
class ForeignKeyInfo:
    column: str
    referenced_table: str
    referenced_column: str


@dataclass(frozen=True)
class TableInfo:
    name: str
    columns: List[ColumnInfo]
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    row_count: int = 0

    def column_names(self) -> List[str]:
        return [column.name for column in self.columns]

    def prompt_fragment(self) -> str:
        columns = ", ".join(
            f"{column.name} {column.data_type}".strip()
            for column in self.columns
        )
        if not self.foreign_keys:
            return f"{self.name}({columns})"
        joins = "; ".join(
            f"{key.column} -> {key.referenced_table}.{key.referenced_column}"
            for key in self.foreign_keys
        )
        return f"{self.name}({columns}); foreign keys: {joins}"


@dataclass(frozen=True)
class SchemaContext:
    tables: Dict[str, TableInfo]

    def as_prompt(self) -> str:
        return "\n".join(table.prompt_fragment() for table in self.tables.values())


@dataclass(frozen=True)
class RetrievedTable:
    table: str
    score: float
    matched_terms: List[str]


@dataclass(frozen=True)
class SQLCandidate:
    sql: str
    rationale: str
    retrieved_tables: List[RetrievedTable]
    confidence: float
    source: str
    fallback_reason: str = ""


@dataclass(frozen=True)
class QueryResult:
    question: str
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    rationale: str
    retrieved_tables: List[RetrievedTable]
    confidence: float
    source: str
    fallback_reason: str
    latency_ms: int
    error: Optional[str] = None


