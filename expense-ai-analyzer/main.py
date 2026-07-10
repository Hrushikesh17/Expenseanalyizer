"""Application entry point for expense-ai-analyzer."""

from __future__ import annotations

import json

from api.analyze import analyze_expenses
from api.dashboard import dashboard_metrics


DEMO_EXPENSES = [
    {
        "employee": "Asha Rao",
        "vendor": "City Hotel",
        "amount": "12500",
        "date": "2026-07-04",
        "category": "Travel",
        "description": "Late manual hotel claim missing receipt",
    },
    {
        "employee": "Asha Rao",
        "vendor": "City Hotel",
        "amount": "12500",
        "date": "2026-07-04",
        "category": "Travel",
        "description": "Duplicate hotel reimbursement request",
    },
    {
        "employee": "Ravi Menon",
        "vendor": "OfficeKart",
        "amount": "899",
        "date": "2026-07-02",
        "category": "Supplies",
        "description": "Keyboard replacement with receipt",
    },
]


def main() -> None:
    """Run a small demo analysis."""
    analysis = analyze_expenses(DEMO_EXPENSES)
    print(json.dumps({"metrics": dashboard_metrics(analysis), "findings": analysis["findings"]}, indent=2))


if __name__ == "__main__":
    main()
