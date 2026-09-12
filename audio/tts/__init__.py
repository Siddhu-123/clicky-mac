"""TTS Package."""
from audio.tts.base_tts import BaseTTSProvider
from audio.tts.edge_tts_provider import EdgeTTSProvider, clean_text_for_speech
from audio.tts.macos_tts_provider import MacOSTTSProvider

__all__ = ["BaseTTSProvider", "EdgeTTSProvider", "MacOSTTSProvider", "clean_text_for_speech"]
