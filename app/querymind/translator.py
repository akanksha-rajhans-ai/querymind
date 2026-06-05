"""Text-to-SQL generation for the local MVP.

The MVP uses deterministic templates so the project is demoable without an API key.
The interface is deliberately small so an LLM provider can replace or augment the
template layer in the next milestone.
"""

from __future__ import annotations

import os
import re
from typing import List

from app.querymind.guardrails import validate_read_only_sql
from app.querymind.llm_provider import GeminiTextToSQLProvider
from app.querymind.models import SQLCandidate, SchemaContext
from app.querymind.prompt_builder import build_sql_prompt
from app.querymind.schema_index import SchemaIndex, tokenize




class TextToSQLTranslator:
    def __init__(self, schema: SchemaContext):
        self.schema = schema
        self.index = SchemaIndex(schema)
        self.llm_provider = GeminiTextToSQLProvider()


    def generate(self, question: str) -> SQLCandidate:
        retrieved = self.index.retrieve(question)
        fallback_reason = ""

        use_llm = os.getenv("QUERYMIND_USE_LLM", "false").lower() == "true"

        if use_llm and self.llm_provider.is_configured():
            prompt = build_sql_prompt(question, self.schema, retrieved)
            try:
                sql = self.llm_provider.generate_sql(prompt)
                ok, message = validate_read_only_sql(sql)
                if not ok:
                    raise ValueError(message)

                return SQLCandidate(
                    sql=sql,
                    rationale="Generated SQL with Gemini using retrieved schema context.",
                    retrieved_tables=retrieved,
                    confidence=0.78,
                    source="gemini",
                    fallback_reason="",
                )
            except Exception as exc:
                fallback_reason = f"Gemini unavailable, used local fallback. Error: {exc}"
                print(f"Gemini generation failed: {exc}")

        sql, rationale, confidence = self._template_sql(question)
        if not sql:
            sql, rationale, confidence = self._fallback_sql(question, retrieved)

        ok, message = validate_read_only_sql(sql)
        if not ok:
            raise ValueError(message)

        return SQLCandidate(
            sql=sql,
            rationale=rationale,
            retrieved_tables=retrieved,
            confidence=confidence,
            source="local_fallback",
            fallback_reason=fallback_reason,
        )

    def _template_sql(self, question: str) -> tuple[str, str, float]:
        lower = question.lower()
        if self._mentions(lower, "monthly", "month") and self._mentions(lower, "revenue", "sales", "spend"):
            return (
                """
                SELECT
                    strftime('%Y-%m', o.order_date) AS month,
                    ROUND(SUM(oi.quantity * oi.unit_price_cents) / 100.0, 2) AS revenue
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.order_id
                WHERE o.status = 'completed'
                GROUP BY month
                ORDER BY month;
                """,
                "Matched a monthly revenue intent and joined orders to order_items for line-item revenue.",
                0.93,
            )

        if self._mentions(lower, "category", "categories") and self._mentions(lower, "revenue", "sales", "generated"):
            return (
                """
                SELECT
                    p.category AS category,
                    ROUND(SUM(oi.quantity * oi.unit_price_cents) / 100.0, 2) AS revenue
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.order_id
                JOIN products p ON p.product_id = oi.product_id
                WHERE o.status = 'completed'
                GROUP BY p.category
                ORDER BY revenue DESC;
                """,
                "Matched category revenue and used products.category with completed order line items.",
                0.92,
            )

        if self._mentions(lower, "top", "most") and self._mentions(lower, "product", "products") and self._mentions(lower, "revenue", "sales"):
            return (
                """
                SELECT
                    p.product_name AS product,
                    p.category AS category,
                    SUM(oi.quantity) AS units_sold,
                    ROUND(SUM(oi.quantity * oi.unit_price_cents) / 100.0, 2) AS revenue
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.order_id
                JOIN products p ON p.product_id = oi.product_id
                WHERE o.status = 'completed'
                GROUP BY p.product_id, p.product_name, p.category
                ORDER BY revenue DESC
                LIMIT 5;
                """,
                "Matched top product revenue and ranked products by completed order revenue.",
                0.92,
            )

        if self._mentions(lower, "top", "most") and self._mentions(lower, "customer", "customers") and self._mentions(lower, "spend", "spent", "revenue"):
            return (
                """
                SELECT
                    c.full_name AS customer,
                    c.segment AS segment,
                    ROUND(SUM(oi.quantity * oi.unit_price_cents) / 100.0, 2) AS total_spend
                FROM customers c
                JOIN orders o ON o.customer_id = c.customer_id
                JOIN order_items oi ON oi.order_id = o.order_id
                WHERE o.status = 'completed'
                GROUP BY c.customer_id, c.full_name, c.segment
                ORDER BY total_spend DESC
                LIMIT 5;
                """,
                "Matched top customers by spend and aggregated completed order line items per customer.",
                0.91,
            )

        if self._mentions(lower, "orders", "order") and self._mentions(lower, "status", "state"):
            return (
                """
                SELECT
                    status,
                    COUNT(*) AS order_count
                FROM orders
                GROUP BY status
                ORDER BY order_count DESC;
                """,
                "Matched order status breakdown and grouped orders by status.",
                0.89,
            )

        if self._mentions(lower, "average", "avg") and self._mentions(lower, "order") and self._mentions(lower, "value", "revenue"):
            return (
                """
                SELECT
                    ROUND(SUM(order_total_cents) / COUNT(*) / 100.0, 2) AS average_order_value
                FROM (
                    SELECT
                        o.order_id,
                        SUM(oi.quantity * oi.unit_price_cents) AS order_total_cents
                    FROM orders o
                    JOIN order_items oi ON oi.order_id = o.order_id
                    WHERE o.status = 'completed'
                    GROUP BY o.order_id
                ) order_totals;
                """,
                "Matched average order value and averaged completed order totals.",
                0.88,
            )

        if self._mentions(lower, "refund", "refunds") and self._mentions(lower, "rate", "count", "amount"):
            return (
                """
                SELECT
                    COUNT(DISTINCT r.refund_id) AS refund_count,
                    ROUND(SUM(r.amount_cents) / 100.0, 2) AS refund_amount,
                    ROUND(COUNT(DISTINCT r.order_id) * 100.0 / COUNT(DISTINCT o.order_id), 2) AS refunded_order_rate
                FROM orders o
                LEFT JOIN refunds r ON r.order_id = o.order_id
                WHERE o.status = 'completed';
                """,
                "Matched refund metrics and compared refunded completed orders to all completed orders.",
                0.86,
            )

        if self._mentions(lower, "shipment", "shipments", "shipping", "transit", "pending") and self._mentions(lower, "transit", "pending", "still"):
            return (
                """
                SELECT
                    s.order_id,
                    s.carrier,
                    s.status AS shipment_status,
                    s.shipped_at,
                    s.delivered_at
                FROM shipments s
                WHERE s.delivered_at IS NULL
                ORDER BY s.shipped_at;
                """,
                "Matched in-transit or pending shipments and filtered undelivered shipment rows.",
                0.9,
            )

        city = self._extract_city(question)
        if city and self._mentions(lower, "customer", "customers", "clients", "buyers"):
            safe_city = city.replace("'", "''")
            return (
                f"""
                SELECT
                    full_name AS customer,
                    email,
                    city,
                    segment
                FROM customers
                WHERE LOWER(city) = LOWER('{safe_city}')
                ORDER BY full_name;
                """,
                f"Matched customer lookup by city and filtered customers.city = {city}.",
                0.84,
            )


        if self._mentions(lower, "open") and self._mentions(lower, "ticket", "tickets", "support"):
            return (
                """
                SELECT
                    t.ticket_id,
                    c.full_name AS customer,
                    t.issue_type,
                    t.priority,
                    t.created_at
                FROM support_tickets t
                JOIN customers c ON c.customer_id = t.customer_id
                WHERE t.status = 'open'
                ORDER BY
                    CASE t.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    t.created_at;
                """,
                "Matched open support tickets and joined customer context for triage.",
                0.87,
            )

        return "", "", 0.0

    def _fallback_sql(self, question: str, retrieved: List) -> tuple[str, str, float]:
        terms = tokenize(question)
        table = retrieved[0].table if retrieved else self._default_table()
        table_info = self.schema.tables[table]
        if {"count", "many", "number"}.intersection(terms):
            return (
                f"SELECT COUNT(*) AS row_count FROM {table};",
                f"Used schema retrieval fallback and counted rows in the most relevant table: {table}.",
                0.58,
            )
        columns = table_info.column_names()[:5]
        column_sql = ", ".join(columns)
        return (
            f"SELECT {column_sql} FROM {table} LIMIT 20;",
            f"Used schema retrieval fallback and selected representative columns from {table}.",
            0.52,
        )

    def _default_table(self) -> str:
        return "orders" if "orders" in self.schema.tables else sorted(self.schema.tables)[0]

    @staticmethod
    def _mentions(text: str, *terms: str) -> bool:
        return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)

    @staticmethod
    def _extract_city(text: str) -> str:
        match = re.search(
            r"\b(?:in|from|at)\s+([a-zA-Z][a-zA-Z\s'-]{1,40})(?:\?|$|\s+with|\s+by|\s+ordered|\s+sorted)",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return ""

        city = match.group(1).strip()
        return " ".join(word.capitalize() for word in city.split())


