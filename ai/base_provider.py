"""
Base AI Provider Interface for Clicky macOS.
Handles text queries, multimodal screen context, and streaming responses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional

from screen.capture import ScreenShot


class BaseAIProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'gemini', 'ollama', 'openai', 'claude')."""
        pass

    @abstractmethod
    async def ask(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Returns complete string response from LLM."""
        pass

    @abstractmethod
    async def ask_stream(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Yields streaming response tokens."""
        pass
