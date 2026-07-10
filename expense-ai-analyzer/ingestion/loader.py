"""Load uploaded expense files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ingestion.parser import parse_expense_file


def load_expenses(path: str | Path) -> list[dict[str, Any]]:
    return parse_expense_file(path)
