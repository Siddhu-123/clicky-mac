"""
Google Gemini Provider (Flash 2.5 / 1.5).
Uses direct REST API via httpx for fast multimodal screen analysis and low latency.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator, Dict, List, Optional

import httpx

from ai.base_provider import BaseAIProvider
from config import cfg
from screen.capture import ScreenShot


class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or cfg.gemini_api_key
        self.model = model or cfg.gemini_model or "gemini-2.5-flash"

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _build_contents(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> dict:
        parts = []

        # Attach screenshots if present
        if screenshots:
            for s in screenshots:
                parts.append({
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": s.base64_jpeg,
                    }
                })

        parts.append({"text": prompt})

        contents = []
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        contents.append({"role": "user", "parts": parts})

        body = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            }
        }
        return body

    async def ask(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if not self.api_key:
            return "Gemini API key is not configured. Please set GEMINI_API_KEY in settings or .env"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        body = self._build_contents(prompt, system_prompt, screenshots, history)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=body)
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join(p.get("text", "") for p in parts)
                return "No response received from Gemini."
            except Exception as e:
                print(f"[GeminiProvider] Error: {e}")
                return f"Gemini Error: {e}"

    async def ask_stream(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield "Gemini API key is not configured. Please set GEMINI_API_KEY in settings or .env"
            return

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        body = self._build_contents(prompt, system_prompt, screenshots, history)

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                async with client.stream("POST", url, json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            raw_data = line[6:].strip()
                            if not raw_data:
                                continue
                            try:
                                chunk = json.loads(raw_data)
                                candidates = chunk.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        text = p.get("text", "")
                                        if text:
                                            yield text
                            except Exception:
                                continue
            except Exception as e:
                yield f"[Gemini Stream Error: {e}]"
