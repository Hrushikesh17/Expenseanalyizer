"""Confidence scoring helpers."""

from __future__ import annotations

from typing import Any


def score_confidence(record: dict[str, Any]) -> float:
    required_fields = ("employee", "vendor", "amount", "date", "category", "business_purpose")
    present = sum(bool(record.get(field)) for field in required_fields)
    confidence = present / len(required_fields)
    if record.get("parsed_date") is None:
        confidence -= 0.15
    if record.get("amount", 0.0) <= 0:
        confidence -= 0.2
    if record.get("missing_receipt_hint"):
        confidence -= 0.1
    return round(max(min(confidence, 1.0), 0.0), 2)


def attach_confidence(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**record, "confidence": score_confidence(record)} for record in records]
