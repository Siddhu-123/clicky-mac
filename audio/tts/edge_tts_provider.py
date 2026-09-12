"""
Microsoft Edge TTS Provider.
100% Free, 400+ neural voices, zero API key required.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import List, Optional

import edge_tts

from audio.tts.base_tts import BaseTTSProvider
from config import cfg

# Regex to strip Clicky tag annotations from spoken text
TAG_REGEX = re.compile(r"\[(POINT|TYPE|ARROW|CIRCLE|UNDERLINE|LABEL):[^\]]*\]")


def clean_text_for_speech(text: str) -> str:
    """Strips annotation tags, markdown code fences, and URLs from spoken audio."""
    # Remove tags
    cleaned = TAG_REGEX.sub("", text)
    # Remove code blocks
    cleaned = re.sub(r"```[\s\S]*?```", "code block omitted", cleaned)
    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    # Remove raw URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Clean redundant whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class EdgeTTSProvider(BaseTTSProvider):
    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or cfg.edge_voice

    async def synthesize(self, text: str, output_path: str | Path, voice: Optional[str] = None) -> bool:
        spoken_text = clean_text_for_speech(text)
        if not spoken_text:
            return False

        selected_voice = voice or self.voice or cfg.edge_voice
        output_file = str(output_path)

        try:
            communicate = edge_tts.Communicate(
                text=spoken_text,
                voice=selected_voice,
                rate=cfg.tts_rate,
                volume=cfg.tts_volume,
            )
            await communicate.save(output_file)
            return True
        except Exception as e:
            print(f"[EdgeTTS] Error synthesizing speech: {e}")
            return False

    @staticmethod
    async def list_voices() -> List[dict]:
        try:
            return await edge_tts.list_voices()
        except Exception as e:
            print(f"[EdgeTTS] Failed to list voices: {e}")
            return []
