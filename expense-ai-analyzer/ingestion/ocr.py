"""OCR utilities for scanned expense documents."""

from __future__ import annotations

from pathlib import Path


def extract_receipt_text(path: str | Path) -> str:
    """Best-effort OCR for receipt images."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return ""

    try:
        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception:
        return ""
