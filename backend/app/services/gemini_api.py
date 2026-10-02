from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    chunks: list[str] = []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            text = part.get("text")
            if text:
                chunks.append(text)
    return " ".join(piece.strip() for piece in chunks if piece).strip()


def _coerce_json(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("Gemini JSON response was not an object")
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", candidate, re.S)
        if match:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
    raise ValueError(f"Gemini response did not contain valid JSON: {text[:500]!r}")


@dataclass(slots=True)
class GeminiAPIClient:
    model: str | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.model = self.model or settings.default_model
        self.api_key = self.api_key or settings.gemini_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _post(self, path: str, payload: dict) -> dict:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        url = f"{_GEMINI_BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
    ) -> dict:
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_output_tokens,
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        response = await self._post(f"/models/{self.model}:generateContent", payload)
        text = _extract_text(response)
        if not text:
            raise RuntimeError("Gemini response contained no text content.")
        return _coerce_json(text)

    async def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
    ) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"maxOutputTokens": max_output_tokens, "temperature": 0.4},
        }
        response = await self._post(f"/models/{self.model}:generateContent", payload)
        text = _extract_text(response)
        if not text:
            raise RuntimeError("Gemini response contained no text content.")
        return text

    async def embed_text(self, text: str, *, model: str | None = None) -> list[float]:
        embedding_model = model or settings.embedding_model
        payload = {
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": settings.embedding_dimension,
        }
        response = await self._post(f"/models/{embedding_model}:embedContent", payload)

        embedding = response.get("embedding") or {}
        values = embedding.get("values") or embedding.get("value")
        if not values:
            raise RuntimeError("Gemini embedding response did not contain values.")
        return [float(value) for value in values]


@dataclass(slots=True)
class GroqAPIClient:
    """OpenAI-compatible Groq client used when Gemini is unavailable."""

    model: str | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.model = self.model or settings.groq_model
        self.api_key = self.api_key or settings.groq_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(self, *, system_prompt: str, user_prompt: str, max_output_tokens: int, json_mode: bool = False) -> str:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": max_output_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{_GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            if response.is_error:
                detail = response.text[:1000]
                raise httpx.HTTPStatusError(
                    f"Groq returned {response.status_code}: {detail}",
                    request=response.request,
                    response=response,
                )
            result = response.json()

        choices = result.get("choices") or []
        content = ((choices[0].get("message") or {}).get("content") if choices else "")
        if not content:
            raise RuntimeError("Groq response contained no text content.")
        return content