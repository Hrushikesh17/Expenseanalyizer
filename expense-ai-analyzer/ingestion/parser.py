"""Parse raw expense documents into structured records."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.ocr import extract_receipt_text


AMOUNT_RE = re.compile(r"(?:rs\.?|inr|\$)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b")


def _has_meaningful_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    printable = sum(char.isprintable() or char.isspace() for char in stripped)
    alpha_numeric = sum(char.isalnum() for char in stripped)
    return printable / max(len(stripped), 1) > 0.85 and alpha_numeric > 2


def _records_from_dataframe(frame: pd.DataFrame) -> list[dict[str, Any]]:
    frame = frame.dropna(how="all")
    return frame.fillna("").to_dict(orient="records")


def _metadata_record(file_path: Path, reason: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"file-{file_path.stem or 'upload'}",
            "employee": "unknown",
            "vendor": file_path.name,
            "category": "unparsed file",
            "amount": "0",
            "date": "",
            "receipt": file_path.name,
            "description": f"{reason}. File was received but could not be converted into structured expense rows.",
        }
    ]


def _records_from_text(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines, start=1):
        amount_match = AMOUNT_RE.search(line)
        date_match = DATE_RE.search(line)
        amount = amount_match.group(1).replace(",", "") if amount_match else "0"
        date = date_match.group(1) if date_match else ""
        cleaned_line = line
        if amount_match:
            cleaned_line = cleaned_line.replace(amount_match.group(0), " ")
        if date_match:
            cleaned_line = cleaned_line.replace(date_match.group(0), " ")
        parts = [part.strip(" ,;|") for part in re.split(r"\s{2,}|,|\|", cleaned_line) if part.strip()]

        records.append(
            {
                "id": f"manual-{index}",
                "employee": parts[0] if len(parts) > 0 else "manual input",
                "vendor": parts[1] if len(parts) > 1 else "unknown",
                "category": parts[2] if len(parts) > 2 else "uncategorized",
                "amount": amount,
                "date": date,
                "description": line,
            }
        )
    return records


def parse_expense_text(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("records", [data])
    except json.JSONDecodeError:
        pass
    return _records_from_text(text)


def _read_pdf_text(file_path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise ImportError("Install PyPDF2 to read PDF uploads.") from exc

    reader = PdfReader(str(file_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx_text(file_path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ImportError("Install python-docx to read Word uploads.") from exc

    document = Document(str(file_path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def parse_expense_file(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("records", [])
    if suffix == ".csv":
        with file_path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    if suffix == ".tsv":
        with file_path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))
    if suffix in {".xlsx", ".xls"}:
        return _records_from_dataframe(pd.read_excel(file_path))
    if suffix in {".txt", ".md", ".log"}:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        records = parse_expense_text(text) if _has_meaningful_text(text) else []
        return records or _metadata_record(file_path, "No readable expense text found")
    if suffix == ".pdf":
        records = parse_expense_text(_read_pdf_text(file_path))
        return records or _metadata_record(file_path, "No selectable PDF text found")
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        ocr_text = extract_receipt_text(file_path)
        records = parse_expense_text(ocr_text) if _has_meaningful_text(ocr_text) else []
        if records:
            for record in records:
                record.setdefault("receipt", file_path.name)
                record.setdefault("description", f"OCR receipt text from {file_path.name}")
            return records
        return _metadata_record(file_path, "Receipt image OCR did not produce enough readable claim details")
    if suffix in {".docx", ".doc"}:
        records = parse_expense_text(_read_docx_text(file_path))
        return records or _metadata_record(file_path, "No readable Word text found")

    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        records = parse_expense_text(text) if _has_meaningful_text(text) else []
    except OSError:
        records = []
    return records or _metadata_record(file_path, f"Unsupported or binary format {suffix or '(no extension)'}")
