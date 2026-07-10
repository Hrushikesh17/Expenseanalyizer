"""TF-IDF based text analysis."""

from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]*")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def top_terms(documents: list[str], limit: int = 8) -> list[list[tuple[str, float]]]:
    tokenized = [tokenize(document) for document in documents]
    document_count = max(len(tokenized), 1)
    doc_freq = Counter(token for doc in tokenized for token in set(doc))

    scored_documents: list[list[tuple[str, float]]] = []
    for tokens in tokenized:
        term_freq = Counter(tokens)
        total = max(sum(term_freq.values()), 1)
        scores = {
            term: (count / total) * math.log((1 + document_count) / (1 + doc_freq[term])) + 1
            for term, count in term_freq.items()
        }
        scored_documents.append(sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit])
    return scored_documents


def relevance_scores(documents: list[str], problem_statement: str) -> list[float]:
    query_terms = set(tokenize(problem_statement))
    if not query_terms:
        return [0.0 for _ in documents]

    scores = []
    for terms in top_terms(documents, limit=20):
        weighted_overlap = sum(score for term, score in terms if term in query_terms)
        scores.append(round(min(weighted_overlap / len(query_terms), 1.0), 3))
    return scores
