"""Expense anomaly detection."""

from __future__ import annotations

from typing import Any


def detect_anomalies(records: list[dict[str, Any]], zscore_threshold: float = 2.0) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for record in records:
        reasons = []
        severity_points = 0
        if abs(record.get("amount_zscore", 0.0)) >= zscore_threshold:
            reasons.append("amount is statistically unusual")
            severity_points += 3
        if record.get("is_weekend"):
            reasons.append("expense was submitted for a weekend date")
            severity_points += 2
        if record.get("is_round_amount"):
            reasons.append("round amount may need receipt validation")
            severity_points += 1
        if record.get("is_manual"):
            reasons.append("manual claim needs extra verification")
            severity_points += 1
        if record.get("missing_receipt_hint") or (record.get("is_round_amount") and not record.get("has_receipt")):
            reasons.append("receipt or supporting proof is missing")
            severity_points += 2
        if reasons:
            severity = "high" if severity_points >= 5 else "medium" if severity_points >= 2 else "low"
            confidence = min(0.95, 0.45 + (severity_points * 0.1) + (0.1 if record.get("confidence", 0) >= 0.8 else 0))
            findings.append(
                {
                    "id": record["id"],
                    "severity": severity,
                    "confidence": round(confidence, 2),
                    "reasons": reasons,
                }
            )
    return findings
