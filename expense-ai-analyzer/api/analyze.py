"""Analysis API routes."""

from __future__ import annotations

from typing import Any

from ai.anomaly_detector import detect_anomalies
from ai.confidence import attach_confidence
from ai.duplicate_detector import detect_duplicates
from ai.knowledge_graph import ExpenseKnowledgeGraph
from ai.tfidf import relevance_scores, top_terms
from config import AUDIT_KEYWORDS
from guardrails.validation import validate_records
from preprocessing.cleaner import clean_records
from preprocessing.feature_builder import build_features


PROBLEM_STATEMENT = (
    "AI expense analyzer for fraud, duplicate claims, audit risk, policy violations, "
    "explainable guardrails, scalable finance operations, and GenAI decision support."
)


def analyze_expenses(records: list[dict[str, Any]]) -> dict[str, Any]:
    cleaned = clean_records(records)
    featured = attach_confidence(build_features(cleaned))
    documents = [record["audit_text"] for record in featured]
    graph = ExpenseKnowledgeGraph().build(featured)
    terms = top_terms(documents)
    relevance = relevance_scores(documents, PROBLEM_STATEMENT + " " + " ".join(AUDIT_KEYWORDS))

    for record, record_terms, score in zip(featured, terms, relevance):
        record["tfidf_terms"] = record_terms
        record["problem_relevance"] = score

    anomalies = detect_anomalies(featured)
    duplicates = detect_duplicates(featured)
    guardrails = validate_records(featured)

    return {
        "records": featured,
        "findings": {
            "anomalies": anomalies,
            "duplicates": duplicates,
            "guardrails": guardrails,
            "knowledge_graph": graph.summary(),
        },
        "hackathon_alignment": {
            "relevance": "Targets expense audit pain points: duplicate claims, anomaly detection, policy checks, and searchable evidence.",
            "innovation": "Combines TF-IDF explainability, graph relationships, deterministic guardrails, and optional GenAI summaries.",
            "feasibility": "Uses lightweight local analytics first, then augments with LLM calls when available.",
            "scalability": "Separates ingestion, preprocessing, AI, vector DB, guardrails, APIs, exports, and frontend modules.",
            "ai_ml_usage": "TF-IDF, anomaly scoring, duplicate detection, confidence scoring, knowledge graph reasoning, and GenAI audit narration.",
        },
    }
