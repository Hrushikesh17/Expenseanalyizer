"""Project configuration and environment loading."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
FAISS_DIR = DATA_DIR / "faiss"
EXPORTS_DIR = DATA_DIR / "exports"
PROMPTS_DIR = BASE_DIR / "prompts"
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

GENAI_API_KEY = os.getenv("GENAI_API_KEY", "")
GENAI_BASE_URL = os.getenv("GENAI_BASE_URL", "https://genailab.tcs.in").rstrip("/")
GENAI_MODEL = os.getenv("GENAI_MODEL", "gpt-4o-mini")

AUDIT_KEYWORDS = (
    "duplicate",
    "fraud",
    "suspicious",
    "anomaly",
    "cash",
    "manual",
    "late",
    "missing receipt",
    "receipt mismatch",
    "ocr",
    "policy",
    "split",
    "round amount",
    "weekend",
    "high amount",
    "out of policy",
)
