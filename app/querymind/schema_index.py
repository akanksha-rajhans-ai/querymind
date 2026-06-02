"""Lightweight schema retrieval for grounding text-to-SQL generation."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Iterable, List, Set

from app.querymind.models import RetrievedTable, SchemaContext, TableInfo


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "from",
    "have",
    "in",
    "is",
    "me",
    "most",
    "of",
    "on",
    "show",
    "the",
    "to",
    "we",
    "what",
    "which",
    "who",
}

TABLE_ALIASES: Dict[str, Set[str]] = {
    "customers": {"customer", "customers", "buyer", "buyers", "client", "clients", "city", "cities", "segment"},
    "orders": {"order", "orders", "purchase", "purchases", "status", "channel", "month"},
    "order_items": {"item", "items", "line", "lines", "quantity", "revenue", "sales", "spend"},
    "products": {"product", "products", "sku", "category", "categories", "price", "revenue"},
    "payments": {"payment", "payments", "paid", "method", "amount"},
    "refunds": {"refund", "refunds", "returned", "chargeback"},
    "shipments": {"shipment", "shipments", "shipping", "shipped", "delivered", "transit", "carrier"},
    "support_tickets": {"support", "ticket", "tickets", "issue", "priority", "open"},
}

COLUMN_ALIASES: Dict[str, Set[str]] = {
    "full_name": {"name", "customer"},
    "product_name": {"name", "product"},
    "unit_price_cents": {"price", "revenue", "spend"},
    "amount_cents": {"amount", "paid", "payment"},
    "order_date": {"date", "month", "monthly"},
    "delivered_at": {"delivered", "transit", "pending"},
    "status": {"status", "state"},
}


def tokenize(text: str) -> Set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if token and token not in STOPWORDS
    }
    expanded = set(tokens)
    for token in tokens:
        if token.endswith("s"):
            expanded.add(token[:-1])
        else:
            expanded.add(f"{token}s")
    return expanded


class SchemaIndex:
    def __init__(self, schema: SchemaContext):
        self.schema = schema
        self._table_terms = {
            name: self._terms_for_table(table)
            for name, table in schema.tables.items()
        }

    def retrieve(self, question: str, top_k: int = 4) -> List[RetrievedTable]:
        query_terms = tokenize(question)
        ranked: List[RetrievedTable] = []
        for table_name, terms in self._table_terms.items():
            matched = sorted(query_terms.intersection(terms))
            score = self._score(query_terms, terms, table_name)
            if score > 0:
                ranked.append(
                    RetrievedTable(
                        table=table_name,
                        score=round(score, 3),
                        matched_terms=matched[:8],
                    )
                )
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    def _terms_for_table(self, table: TableInfo) -> Set[str]:
        terms = set(tokenize(table.name.replace("_", " ")))
        terms.update(TABLE_ALIASES.get(table.name, set()))
        for column in table.columns:
            terms.update(tokenize(column.name.replace("_", " ")))
            terms.update(COLUMN_ALIASES.get(column.name, set()))
        for key in table.foreign_keys:
            terms.update(tokenize(key.referenced_table.replace("_", " ")))
            terms.update(tokenize(key.referenced_column.replace("_", " ")))
        return terms

    @staticmethod
    def _score(query_terms: Set[str], table_terms: Set[str], table_name: str) -> float:
        matches = query_terms.intersection(table_terms)
        if not matches:
            return 0.0
        score = float(len(matches))
        if table_name in {"orders", "order_items"} and {"revenue", "sales", "spend"}.intersection(query_terms):
            score += 1.5
        if table_name == "customers" and {"customer", "customers", "buyer", "buyers"}.intersection(query_terms):
            score += 1.0
        return score / max(len(query_terms), 1)

    def explain(self, retrieved: Iterable[RetrievedTable]) -> Dict[str, List[str]]:
        return defaultdict(list, {item.table: item.matched_terms for item in retrieved})

