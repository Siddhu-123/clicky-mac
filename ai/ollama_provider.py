"""
Local Ollama Provider for offline vision and reasoning.
Connects to Ollama server at localhost:11434.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator, Dict, List, Optional

import httpx

from ai.base_provider import BaseAIProvider
from config import cfg
from screen.capture import ScreenShot


class OllamaProvider(BaseAIProvider):
    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = (host or cfg.ollama_host or "http://localhost:11434").rstrip("/")
        self.model = model or cfg.ollama_model or "llama3.2-vision"

    @property
    def provider_name(self) -> str:
        return "ollama"

    def _build_messages(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[dict]:
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        user_msg: dict = {"role": "user", "content": prompt}
        if screenshots:
            # Ollama takes list of base64 strings in "images" field
            user_msg["images"] = [s.base64_jpeg for s in screenshots]

        messages.append(user_msg)
        return messages

    async def ask(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        url = f"{self.host}/api/chat"
        messages = self._build_messages(prompt, system_prompt, screenshots, history)
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=body)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
            except Exception as e:
                return f"[Ollama Error: Is Ollama running on {self.host}? Details: {e}]"

    async def ask_stream(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.host}/api/chat"
        messages = self._build_messages(prompt, system_prompt, screenshots, history)
        body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.2},
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                async with client.stream("POST", url, json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                delta = chunk.get("message", {}).get("content", "")
                                if delta:
                                    yield delta
                            except Exception:
                                continue
            except Exception as e:
                yield f"[Ollama Stream Error: {e}]"
