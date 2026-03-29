from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class LLMRouter:
    def __init__(self) -> None:
        self.timeout = 12.0

    def ask(self, prompt: str) -> tuple[str, str | None]:
        mode = settings.ai_route_mode
        if mode == "off":
            return "AI mode is off.", None
        if mode == "local":
            text = self._ask_ollama(prompt)
            return text, "ollama"
        if mode == "cloud":
            text = self._ask_openai(prompt)
            return text, "openai"

        # Hybrid mode: local first, cloud fallback.
        try:
            text = self._ask_ollama(prompt)
            return text, "ollama"
        except Exception:
            if not settings.openai_api_key:
                return "Local model unavailable and no cloud key configured.", None
            try:
                text = self._ask_openai(prompt)
                return text, "openai"
            except Exception:
                return "Both local and cloud models are unavailable right now.", None

    def is_enabled(self) -> bool:
        return settings.ai_route_mode != "off"

    def _ask_ollama(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("response", "")).strip() or "No response from local model."

    def _ask_openai(self, prompt: str) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")

        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "You are a concise desktop assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{settings.openai_base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return str(data["choices"][0]["message"]["content"]).strip()
