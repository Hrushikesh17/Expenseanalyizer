"""Build analysis features from cleaned expense records."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


def build_features(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    amounts = [record.get("amount", 0.0) for record in records]
    avg = mean(amounts) if amounts else 0.0
    deviation = pstdev(amounts) if len(amounts) > 1 else 0.0

    featured: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        amount = record.get("amount", 0.0)
        parsed_date = record.get("parsed_date")
        text = " ".join(
            str(record.get(field, ""))
            for field in ("employee", "vendor", "category", "description", "business_purpose", "receipt")
        )
        description = str(record.get("description", "")).lower()
        receipt = str(record.get("receipt", "")).lower()
        enriched = dict(record)
        enriched["id"] = str(record.get("id") or f"expense-{index + 1}")
        enriched["audit_text"] = text.lower()
        enriched["amount_zscore"] = 0.0 if deviation == 0 else round((amount - avg) / deviation, 3)
        enriched["is_weekend"] = bool(parsed_date and parsed_date.weekday() >= 5)
        enriched["is_round_amount"] = bool(amount and amount % 100 == 0)
        enriched["is_manual"] = "manual" in description
        enriched["has_receipt"] = bool(receipt) or "with receipt" in description or "receipt attached" in description
        enriched["missing_receipt_hint"] = any(
            phrase in description for phrase in ("missing receipt", "no receipt", "without receipt", "lost receipt")
        )
        featured.append(enriched)
    return featured
