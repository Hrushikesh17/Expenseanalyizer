"""Search API routes."""

from __future__ import annotations

from typing import Any

from ai.tfidf import tokenize


def search_records(records: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_terms = set(tokenize(query))
    ranked = []
    for record in records:
        text = record.get("audit_text", "")
        overlap = len(query_terms.intersection(tokenize(text)))
        if overlap:
            ranked.append((overlap, record))
    return [record for _, record in sorted(ranked, key=lambda item: item[0], reverse=True)]
