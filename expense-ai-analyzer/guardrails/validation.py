"""Validation and guardrail checks."""

from __future__ import annotations

from typing import Any


def validate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for record in records:
        record_issues = []
        if not record.get("employee") or record.get("employee") == "unknown":
            record_issues.append("missing employee")
        if not record.get("vendor") or record.get("vendor") == "unknown":
            record_issues.append("missing vendor")
        if not record.get("business_purpose"):
            record_issues.append("missing business purpose")
        if record.get("amount", 0.0) <= 0:
            record_issues.append("amount must be positive")
        if record.get("parsed_date") is None:
            record_issues.append("date could not be parsed")
        if record.get("missing_receipt_hint"):
            record_issues.append("receipt evidence is missing")
        if record_issues:
            issues.append({"id": record.get("id", "unknown"), "issues": record_issues})

    return {
        "passed": not issues,
        "issues": issues,
        "policy": "Validate completeness, positive amounts, parseable dates, and explainable AI findings.",
    }
