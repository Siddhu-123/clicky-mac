"""
Mock / Demo AI Provider for Clicky macOS.
Allows testing screen awareness, pointer flight, annotations, and TTS
immediately out-of-the-box without requiring any API keys or servers.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, List, Optional

from ai.base_provider import BaseAIProvider
from screen.capture import ScreenShot


class MockDemoProvider(BaseAIProvider):
    @property
    def provider_name(self) -> str:
        return "demo"

    async def ask(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        q = (prompt or "").lower()

        # Check if user asked to point or locate something
        if any(w in q for w in ["where", "point", "locate", "show me", "find", "button", "apple"]):
            return (
                "I see your screen! Let me point to the menu bar right here. "
                "[POINT:35,14:Apple Menu] [ARROW:120,80->40,18] [CIRCLE:35,14,24:Menu Area] "
                "You can configure your real AI model in Settings anytime."
            )
        elif any(w in q for w in ["agent", "task", "automate"]):
            return (
                "HeyClicky Agent Mode is active! In full mode, I can run shell commands, "
                "edit files, and automate Mac apps. Configure Gemini or Ollama in Settings to start autonomous tasks."
            )
        else:
            return (
                f"Hello! I heard: '{prompt}'. Clicky is running in Demo Mode. "
                "I can see your screen, fly beside your cursor, and speak answers. "
                "To unlock live AI reasoning, open Settings (⚙) and add a free Gemini API key or connect Ollama."
            )

    async def ask_stream(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        full_text = await self.ask(prompt, system_prompt, screenshots, history)
        for word in full_text.split(" "):
            yield word + " "
            await asyncio.sleep(0.04)
