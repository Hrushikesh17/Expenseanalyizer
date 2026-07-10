"""Vector search helpers.

This module keeps a tiny in-memory fallback so the prototype works without a
native FAISS install. It can be replaced by faiss.IndexFlatIP later.
"""

from __future__ import annotations

from typing import Any

from ai.embeddings import hashed_embedding


class SimpleVectorIndex:
    def __init__(self) -> None:
        self.items: list[tuple[str, list[float], dict[str, Any]]] = []

    def add(self, item_id: str, text: str, metadata: dict[str, Any]) -> None:
        self.items.append((item_id, hashed_embedding(text), metadata))

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_vector = hashed_embedding(query)
        scored = []
        for item_id, vector, metadata in self.items:
            score = sum(left * right for left, right in zip(query_vector, vector))
            scored.append({"id": item_id, "score": round(score, 4), "metadata": metadata})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]
