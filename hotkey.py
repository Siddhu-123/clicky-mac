"""
Global shortcut and push-to-talk monitor for macOS using pynput.
Default combination: Control + Option (HeyClicky standard).
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional, Set

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from config import cfg


class GlobalHotkeyMonitor:
    """
    Listens for system-wide push-to-talk or hotkey combinations on macOS.
    Fires `on_press` when the combo is pressed/held, and `on_release` when released.
    Also handles `Esc` for instant cancellation of speech / agent actions.
    """

    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        on_cancel: Optional[Callable[[], None]] = None,
        hotkey_str: Optional[str] = None,
    ):
        self.on_press = on_press
        self.on_release = on_release
        self.on_cancel = on_cancel
        self.hotkey_str = (hotkey_str or cfg.hotkey).lower()

        self._active_modifiers: Set[str] = set()
        self._target_modifiers: Set[str] = set()
        self._held = False
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

        self._parse_hotkey()

    def _parse_hotkey(self):
        parts = [p.strip() for p in self.hotkey_str.split("+") if p.strip()]
        for p in parts:
            if p in ("ctrl", "control"):
                self._target_modifiers.add("ctrl")
            elif p in ("alt", "opt", "option"):
                self._target_modifiers.add("alt")
            elif p in ("cmd", "command", "win", "meta"):
                self._target_modifiers.add("cmd")
            elif p in ("shift",):
                self._target_modifiers.add("shift")

    def _key_to_token(self, key) -> Optional[str]:
        if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            return "ctrl"
        if key in (Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr):
            return "alt"
        if key in (Key.cmd, Key.cmd_l, Key.cmd_r):
            return "cmd"
        if key in (Key.shift, Key.shift_l, Key.shift_r):
            return "shift"
        return None

    def _on_key_press(self, key):
        # Escape key triggers instant stop / cancel
        if key == Key.esc and self.on_cancel:
            try:
                self.on_cancel()
            except Exception as e:
                print(f"[Hotkey] Error in on_cancel: {e}")
            return

        token = self._key_to_token(key)
        if token:
            with self._lock:
                self._active_modifiers.add(token)
                if not self._held and self._target_modifiers.issubset(self._active_modifiers):
                    self._held = True
                    try:
                        self.on_press()
                    except Exception as e:
                        print(f"[Hotkey] Error in on_press: {e}")

    def _on_key_release(self, key):
        token = self._key_to_token(key)
        if token:
            with self._lock:
                self._active_modifiers.discard(token)
                if self._held and not self._target_modifiers.issubset(self._active_modifiers):
                    self._held = False
                    try:
                        self.on_release()
                    except Exception as e:
                        print(f"[Hotkey] Error in on_release: {e}")

    def start(self):
        """Starts the global keyboard listener in a background thread."""
        if self._listener is None:
            self._listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
            )
            self._listener.daemon = True
            self._listener.start()
            print(f"[Hotkey] Listening for combo: {self.hotkey_str} (Esc to cancel)")

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
