"""Retrieval augmented generation utilities."""

from __future__ import annotations

from typing import Any

from ai.tfidf import tokenize


def retrieve_context(records: list[dict[str, Any]], question: str, limit: int = 5) -> list[dict[str, Any]]:
    question_terms = set(tokenize(question))
    ranked = []
    for record in records:
        record_terms = set(tokenize(record.get("audit_text", "")))
        score = len(question_terms.intersection(record_terms))
        if score:
            ranked.append((score, record))
    return [record for _, record in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit]]
