"""
Microphone audio capture for push-to-talk using sounddevice.
Captures 16kHz mono float32 audio suitable for Whisper / STT.
"""

from __future__ import annotations

import io
import threading
import wave
from typing import Optional

import numpy as np
import sounddevice as sd


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._frames: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False
        self._lock = threading.Lock()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            pass
        if self._is_recording:
            with self._lock:
                self._frames.append(indata.copy())

    def start_recording(self):
        with self._lock:
            self._frames.clear()
            self._is_recording = True

        if self._stream is None or not self._stream.active:
            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
            except Exception as e:
                print(f"[AudioRecorder] Error opening input stream: {e}")
                self._is_recording = False

    def stop_recording(self) -> Optional[np.ndarray]:
        with self._lock:
            self._is_recording = False
            if not self._frames:
                return None
            data = np.concatenate(self._frames, axis=0)

        # Flatten to 1D
        audio_1d = data.flatten()
        return audio_1d

    def stop_and_get_wav_bytes(self) -> Optional[bytes]:
        audio = self.stop_recording()
        if audio is None or len(audio) == 0:
            return None

        # Convert float32 [-1.0, 1.0] to int16
        int16_data = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(int16_data.tobytes())

        return buf.getvalue()

    def close(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
