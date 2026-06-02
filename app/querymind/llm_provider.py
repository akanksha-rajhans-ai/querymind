"""Gemini provider integration for QueryMind."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


class GeminiTextToSQLProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("QUERYMIND_GEMINI_MODEL", "gemini-2.0-flash")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_sql(self, prompt: str) -> str:
        if not self.is_configured():
            raise RuntimeError("GEMINI_API_KEY is not set.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 600,
            },
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise RuntimeError(f"Gemini API error: {body}") from exc

        return self._clean_sql(self._extract_text(data))

    @staticmethod
    def _extract_text(data: dict) -> str:
        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        return "\n".join(part.get("text", "") for part in parts).strip()

    @staticmethod
    def _clean_sql(text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```sql\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()
