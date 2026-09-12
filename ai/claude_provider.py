"""
Anthropic Claude Provider (Claude 3.5 Sonnet).
"""

from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Optional

from anthropic import AsyncAnthropic

from ai.base_provider import BaseAIProvider
from config import cfg
from screen.capture import ScreenShot


class ClaudeProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or cfg.anthropic_api_key
        self.model = model or cfg.claude_model or "claude-3-5-sonnet-20241022"
        self._client: Optional[AsyncAnthropic] = None

    @property
    def provider_name(self) -> str:
        return "claude"

    def _get_client(self) -> Optional[AsyncAnthropic]:
        if not self.api_key:
            return None
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    def _build_messages(
        self,
        prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[dict]:
        messages = []

        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        user_content = []
        if screenshots:
            for s in screenshots:
                user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": s.base64_jpeg,
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
            return "Anthropic API key is missing. Set ANTHROPIC_API_KEY in settings or .env"

        messages = self._build_messages(prompt, screenshots, history)
        try:
            resp = await client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            )
            text_blocks = [b.text for b in resp.content if hasattr(b, "text")]
            return "".join(text_blocks)
        except Exception as e:
            return f"[Claude Error: {e}]"

    async def ask_stream(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        if not client:
            yield "Anthropic API key is missing. Set ANTHROPIC_API_KEY in settings or .env"
            return

        messages = self._build_messages(prompt, screenshots, history)
        try:
            async with client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"[Claude Stream Error: {e}]"
