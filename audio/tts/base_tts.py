"""TTS provider interface."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseTTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, output_path: str | Path, voice: Optional[str] = None) -> bool:
        """Synthesizes text into an audio file at output_path."""
        pass
