"""Excel export helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from config import EXPORTS_DIR


def export_excel(records: list[dict[str, Any]], filename: str = "expense_audit.xlsx") -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    target = EXPORTS_DIR / filename
    pd.DataFrame(records).to_excel(target, index=False)
    return target
