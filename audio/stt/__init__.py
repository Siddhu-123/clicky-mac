"""STT package."""
from audio.stt.base_stt import BaseSTTProvider
from audio.stt.faster_whisper_stt import FasterWhisperSTT

__all__ = ["BaseSTTProvider", "FasterWhisperSTT"]
