"""
OpenAI Provider for GPT-4o / GPT-4o-mini.
"""

from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI

from ai.base_provider import BaseAIProvider
from config import cfg
from screen.capture import ScreenShot


class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or cfg.openai_api_key
        self.model = model or cfg.openai_model or "gpt-4o"
        self._client: Optional[AsyncOpenAI] = None

    @property
    def provider_name(self) -> str:
        return "openai"

    def _get_client(self) -> Optional[AsyncOpenAI]:
        if not self.api_key:
            return None
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

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

        user_content = []
        if screenshots:
            for s in screenshots:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{s.base64_jpeg}",
                        "detail": "low",
                    },
                })
        user_content.append({"type": "text", "text": prompt})
        messages.append({"role": "user", "content": user_content})
        return messages

    async def ask(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        client = self._get_client()
        if not client:
            return "OpenAI API key is missing. Set OPENAI_API_KEY in settings or .env"

        messages = self._build_messages(prompt, system_prompt, screenshots, history)
        try:
            resp = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=2048,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Error: {e}]"

    async def ask_stream(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        if not client:
            yield "OpenAI API key is missing. Set OPENAI_API_KEY in settings or .env"
            return

        messages = self._build_messages(prompt, system_prompt, screenshots, history)
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=2048,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else ""
                if delta:
                    yield delta
        except Exception as e:
            yield f"[OpenAI Stream Error: {e}]"
