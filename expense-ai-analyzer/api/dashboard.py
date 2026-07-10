"""Dashboard API routes."""

from __future__ import annotations

from typing import Any


def dashboard_metrics(analysis: dict[str, Any]) -> dict[str, Any]:
    records = analysis.get("records", [])
    findings = analysis.get("findings", {})
    total_amount = sum(record.get("amount", 0.0) for record in records)
    confidence_values = [record.get("confidence", 0.0) for record in records]
    high_risk_count = sum(1 for item in findings.get("anomalies", []) if item.get("severity") == "high")
    rejected_count = len(findings.get("guardrails", {}).get("issues", [])) + len(findings.get("duplicates", []))
    return {
        "record_count": len(records),
        "total_amount": round(total_amount, 2),
        "anomaly_count": len(findings.get("anomalies", [])),
        "high_risk_count": high_risk_count,
        "duplicate_count": len(findings.get("duplicates", [])),
        "average_confidence": round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0.0,
        "estimated_cycle_time_saved_min": max(0, len(records) * 6 - rejected_count * 2),
        "guardrails_passed": findings.get("guardrails", {}).get("passed", False),
        "knowledge_graph": findings.get("knowledge_graph", {}),
    }
