"""
Audio playback manager for Clicky macOS.
Uses macOS native `afplay` for low-latency background playback with instant cancellation.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Optional


class AudioPlayer:
    def __init__(self):
        self._current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._is_playing = False

    def play_file(self, file_path: str | Path, on_finished: Optional[callable] = None) -> bool:
        """Plays an audio file (MP3, WAV, AAC) via macOS afplay in a background thread."""
        path_str = str(file_path)
        if not os.path.exists(path_str):
            print(f"[AudioPlayer] File does not exist: {path_str}")
            return False

        self.stop()

        def _runner():
            with self._lock:
                self._is_playing = True
                try:
                    proc = subprocess.Popen(
                        ["afplay", path_str],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self._current_process = proc
                except Exception as e:
                    print(f"[AudioPlayer] Failed to launch afplay: {e}")
                    self._is_playing = False
                    return

            proc.wait()

            with self._lock:
                if self._current_process is proc:
                    self._is_playing = False
                    self._current_process = None

            if on_finished:
                try:
                    on_finished()
                except Exception:
                    pass

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        return True

    def stop(self):
        """Immediately halts any currently playing audio."""
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                try:
                    self._current_process.terminate()
                    self._current_process.wait(timeout=0.2)
                except Exception:
                    try:
                        self._current_process.kill()
                    except Exception:
                        pass
                self._current_process = None
            self._is_playing = False

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._is_playing
