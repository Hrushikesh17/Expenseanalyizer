"""Duplicate expense detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def detect_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, float, str], list[str]] = defaultdict(list)
    for record in records:
        key = (
            str(record.get("employee", "")).lower(),
            str(record.get("vendor", "")).lower(),
            float(record.get("amount", 0.0)),
            str(record.get("date", "")),
        )
        buckets[key].append(record["id"])

    return [
        {"ids": ids, "severity": "high", "reason": "same employee, vendor, amount, and date"}
        for ids in buckets.values()
        if len(ids) > 1
    ]
