"""SQL safety checks for the local execution path."""

from __future__ import annotations

import re
from typing import Tuple


BLOCKED_KEYWORDS = {
    "alter",
    "attach",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "pragma",
    "replace",
    "truncate",
    "update",
    "vacuum",
}


def strip_sql_comments(sql: str) -> str:
    without_line_comments = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    return re.sub(r"/\*.*?\*/", "", without_line_comments, flags=re.DOTALL)


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", strip_sql_comments(sql)).strip()


def validate_read_only_sql(sql: str) -> Tuple[bool, str]:
    clean = normalize_sql(sql)
    if not clean:
        return False, "SQL is empty."
    statement_count = len([part for part in clean.split(";") if part.strip()])
    if statement_count > 1:
        return False, "Only one SQL statement is allowed."
    no_trailing_semicolon = clean[:-1] if clean.endswith(";") else clean
    first_word = no_trailing_semicolon.split(" ", 1)[0].lower()
    if first_word not in {"select", "with"}:
        return False, "Only SELECT queries are allowed."
    tokens = set(re.findall(r"\b[a-z_]+\b", no_trailing_semicolon.lower()))
    blocked = sorted(tokens.intersection(BLOCKED_KEYWORDS))
    if blocked:
        return False, f"Blocked keyword found: {blocked[0]}"
    return True, "ok"

