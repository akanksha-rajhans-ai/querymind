"""Build prompts for LLM-backed text-to-SQL generation."""

from __future__ import annotations

from app.querymind.models import RetrievedTable, SchemaContext


def build_sql_prompt(
    question: str,
    schema: SchemaContext,
    retrieved_tables: list[RetrievedTable],
) -> str:
    selected_table_names = {item.table for item in retrieved_tables}

    if selected_table_names:
        tables = [
            table
            for name, table in schema.tables.items()
            if name in selected_table_names
        ]
    else:
        tables = list(schema.tables.values())

    schema_text = "\n".join(table.prompt_fragment() for table in tables)

    return f"""
You are QueryMind, a text-to-SQL engine.

Generate SQLite SQL for the user question.

Rules:
- Return SQL only.
- Do not wrap the SQL in markdown.
- Only generate one SELECT statement.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, PRAGMA, or VACUUM.
- Use only the tables and columns shown in the schema.
- Prefer explicit JOINs using foreign keys.
- If the user asks for a city, status, category, customer, or other value that may not exist, still preserve that filter.
- Do not broaden a filtered question into a generic LIMIT query.
- Add LIMIT 50 only for broad listing queries that do not aggregate.

Schema:
{schema_text}

User question:
{question}
""".strip()
