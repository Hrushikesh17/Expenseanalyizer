"""Clean and normalize expense records."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return default


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = {str(key).strip().lower().replace(" ", "_"): value for key, value in record.items()}
    cleaned["amount"] = round(_float(cleaned.get("amount")), 2)
    cleaned["employee"] = str(cleaned.get("employee", "unknown")).strip() or "unknown"
    cleaned["vendor"] = str(cleaned.get("vendor", "unknown")).strip() or "unknown"
    cleaned["category"] = str(cleaned.get("category", "uncategorized")).strip() or "uncategorized"
    cleaned["description"] = str(cleaned.get("description", "")).strip()
    cleaned["business_purpose"] = str(
        cleaned.get("business_purpose") or cleaned.get("purpose") or cleaned.get("description", "")
    ).strip()
    cleaned["receipt"] = str(
        cleaned.get("receipt") or cleaned.get("receipt_url") or cleaned.get("receipt_file") or cleaned.get("proof") or ""
    ).strip()
    cleaned["employee_id"] = str(cleaned.get("employee_id", "")).strip()
    cleaned["department"] = str(cleaned.get("department", "")).strip()
    cleaned["source_system"] = str(
        cleaned.get("source_system") or cleaned.get("source") or cleaned.get("accounting_platform") or ""
    ).strip()
    cleaned["historical_outcome"] = str(
        cleaned.get("historical_outcome")
        or cleaned.get("audit_outcome")
        or cleaned.get("previous_audit_outcome")
        or ""
    ).strip()
    cleaned["submitted_currency"] = str(cleaned.get("currency", "")).strip()

    raw_date = str(cleaned.get("date", "")).strip()
    cleaned["date"] = raw_date
    cleaned["parsed_date"] = parse_date(raw_date)
    return cleaned


def clean_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [clean_record(record) for record in records]


def parse_date(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
