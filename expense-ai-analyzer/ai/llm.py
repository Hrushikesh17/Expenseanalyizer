"""LLM integration utilities."""

from __future__ import annotations

from typing import Any

import requests

from config import GENAI_API_KEY, GENAI_BASE_URL, GENAI_MODEL


def generate_audit_summary(audit_payload: dict[str, Any]) -> str:
    """Call an OpenAI-compatible chat endpoint when credentials are configured."""
    if not GENAI_API_KEY:
        return "LLM summary skipped because GENAI_API_KEY is not configured."

    prompt = (
        "Summarize these expense audit findings for a hackathon demo. "
        "Emphasize TF-IDF relevance, knowledge graph relationships, guardrails, "
        "innovation, feasibility, scalability, and AI/ML usage.\n\n"
        f"{audit_payload}"
    )
    response = requests.post(
        f"{GENAI_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {GENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GENAI_MODEL,
            "messages": [
                {"role": "system", "content": "You are a precise expense audit copilot."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
