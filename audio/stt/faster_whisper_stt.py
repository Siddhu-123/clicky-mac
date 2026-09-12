"""
Local Speech-to-Text provider using faster-whisper.
Runs on Apple Silicon via NEON int8 quantization (fast, offline, 0 cost).
"""

from __future__ import annotations

import io
import threading
from typing import Optional

import numpy as np

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from audio.stt.base_stt import BaseSTTProvider
from config import cfg


class FasterWhisperSTT(BaseSTTProvider):
    def __init__(self, model_size: Optional[str] = None):
        self.model_size = model_size or cfg.whisper_model_size
        self._model: Optional[WhisperModel] = None
        self._lock = threading.Lock()

    def _ensure_model(self):
        if self._model is None and WhisperModel is not None:
            with self._lock:
                if self._model is None:
                    print(f"[STT] Loading faster-whisper model ({self.model_size})...")
                    self._model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                    )
                    print("[STT] faster-whisper model loaded successfully.")

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        if WhisperModel is None:
            print("[STT] faster-whisper is not installed.")
            return ""

        if audio_data is None or len(audio_data) < sample_rate * 0.3:  # Too short (<300ms)
            return ""

        self._ensure_model()
        if self._model is None:
            return ""

        try:
            # faster-whisper expects float32 1D numpy array normalized to [-1, 1]
            segments, info = self._model.transcribe(
                audio_data,
                beam_size=1,
                language="en",
                temperature=0.0,
                vad_filter=True,
            )
            text = " ".join([seg.text.strip() for seg in segments]).strip()
            return text
        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            return ""
