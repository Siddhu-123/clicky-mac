"""
macOS Native TTS Provider using `say`.
100% offline, built into macOS.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from audio.tts.base_tts import BaseTTSProvider
from audio.tts.edge_tts_provider import clean_text_for_speech


class MacOSTTSProvider(BaseTTSProvider):
    def __init__(self, voice: Optional[str] = "Samantha"):
        self.voice = voice

    async def synthesize(self, text: str, output_path: str | Path, voice: Optional[str] = None) -> bool:
        spoken_text = clean_text_for_speech(text)
        if not spoken_text:
            return False

        out_path = str(output_path)
        v = voice or self.voice or "Samantha"

        def _run():
            # Generate AIFF first then convert to mp3/wav if needed, or say can write .aiff
            cmd = ["say", "-v", v, "-o", out_path, spoken_text]
            res = subprocess.run(cmd, capture_output=True)
            return res.returncode == 0

        return await asyncio.to_thread(_run)
