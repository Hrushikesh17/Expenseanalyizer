"""Upload API helpers."""

from __future__ import annotations

from pathlib import Path

from config import UPLOADS_DIR


def save_upload(filename: str, content: bytes) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    target = UPLOADS_DIR / safe_name
    target.write_bytes(content)
    return target


def save_uploads(files: list[tuple[str, bytes]]) -> list[Path]:
    """Save multiple uploaded files and return their local paths."""
    return [save_upload(filename, content) for filename, content in files]
