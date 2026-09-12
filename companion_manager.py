"""
Central Orchestrator for Clicky macOS.
Manages push-to-talk lifecycle, screen capture, STT/TTS pipelines,
pointing animations, and Agent Mode execution.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
import threading
import time
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from agent.runtime import AgentRuntime
from ai.base_provider import BaseAIProvider
from ai.claude_provider import ClaudeProvider
from ai.gemini_provider import GeminiProvider
from ai.ollama_provider import OllamaProvider
from ai.openai_provider import OpenAIProvider
from ai.universal_locator import UniversalLocator
from ai.web_search import WebSearcher
from audio.capture import AudioRecorder
from audio.playback import AudioPlayer
from audio.stt.faster_whisper_stt import FasterWhisperSTT
from audio.tts.edge_tts_provider import EdgeTTSProvider, clean_text_for_speech
from audio.tts.macos_tts_provider import MacOSTTSProvider
from config import cfg, cfg_manager
from hotkey import GlobalHotkeyMonitor
from screen.capture import ScreenShot, capture_all_screens
from tutor import active_window_title, app_key, is_agent, is_locate, is_next, is_repeat, is_stop
from ui.overlay import OverlayWindow
from ui.panel import CompanionPanel
from ui.settings_dialog import SettingsDialog
from ui.tray import ClickyTrayIcon

CLICKY_SYSTEM_PROMPT = """You are Clicky, a friendly, ultra-competent AI tutor buddy living on the user's macOS screen.
You sit right beside their cursor and help them learn, navigate, code, and automate tasks.

Screen Context:
- The user is currently in: {window_title}
- Multi-monitor screenshots are provided in logical macOS coordinate space.

Guidelines:
1. If the user asks where something is, how to find/click/open a UI element:
   - Identify the element's coordinate in the screenshot.
   - Include a tag: [POINT:x,y:label] where x and y are in logical screen coordinates.
   - Keep your verbal answer concise (1-2 sentences), like a tutor pointing right next to them.
2. You can also draw visual aids on screen:
   - [ARROW:x1,y1->x2,y2]
   - [CIRCLE:x,y,radius:label]
   - [LABEL:x,y:text]
3. Speak conversationally and naturally. Keep explanations direct and easy to follow.
"""


class CompanionManager(QObject):
    # Qt Signals for thread-safe UI updates
    status_changed = pyqtSignal(str, str)  # text, state
    query_received = pyqtSignal(str)
    answer_received = pyqtSignal(str)
    point_requested = pyqtSignal(float, float, str)
    annotation_requested = pyqtSignal(str, list)

    def __init__(self):
        super().__init__()
        # Mode: False = Talk Mode, True = Agent Mode (HeyClicky Max)
        self.is_agent_mode = False

        # Audio & Screen
        self.recorder = AudioRecorder(sample_rate=16000)
        self.player = AudioPlayer()
        self.stt = FasterWhisperSTT()
        self.tts = EdgeTTSProvider()
        self.macos_tts = MacOSTTSProvider()

        # UI Components
        self.overlay = OverlayWindow()
        self.panel = CompanionPanel(
            on_toggle_mode=self.toggle_mode,
            on_open_settings=self.open_settings,
        )
        self.tray = ClickyTrayIcon(
            on_toggle_panel=self.toggle_panel,
            on_toggle_mode=self.toggle_mode,
            on_open_settings=self.open_settings,
            on_test_point=self.test_pointing_flight,
            on_quit=self.quit_app,
        )

        # Per-app conversation memory
        self.app_histories: Dict[str, List[Dict[str, str]]] = {}
        self.last_answer: str = ""

        # Connect internal signals to UI
        self.status_changed.connect(self.panel.set_status)
        self.query_received.connect(self.panel.set_user_query)
        self.answer_received.connect(self.panel.set_answer)
        self.point_requested.connect(self.overlay.point_at)
        self.annotation_requested.connect(self._handle_annotation)

        # Hotkey monitor
        self.hotkey_monitor = GlobalHotkeyMonitor(
            on_press=self.on_hotkey_down,
            on_release=self.on_hotkey_up,
            on_cancel=self.on_cancel,
        )

        # Temp directory for TTS files
        self._temp_dir = tempfile.mkdtemp(prefix="clicky_tts_")

        # Async background worker thread & event loop
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._loop_thread.start()

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self):
        self.overlay.show()
        self.panel.show()
        self.tray.show()
        self.hotkey_monitor.start()
        self.update_provider_ui()
        print("[CompanionManager] Clicky started successfully on macOS.")

    def update_provider_ui(self):
        provider = self.get_active_provider()
        model_name = getattr(cfg, f"{cfg.active_provider}_model", "default")
        self.panel.update_model_badge(provider.provider_name, model_name)
        self.panel.update_mode_badge(self.is_agent_mode)
        self.tray.update_mode_label(self.is_agent_mode)

    def get_active_provider(self) -> BaseAIProvider:
        p = cfg.active_provider.lower()
        if p == "gemini":
            return GeminiProvider()
        elif p == "ollama":
            return OllamaProvider()
        elif p == "openai":
            return OpenAIProvider()
        elif p == "claude":
            return ClaudeProvider()
        return GeminiProvider()

    # ── Push-to-Talk Lifecycle ──

    def on_hotkey_down(self):
        """User pressed and is holding push-to-talk combo."""
        print("[CompanionManager] Hotkey pressed - listening...")
        self.player.stop()  # Stop any ongoing playback
        self.status_changed.emit("Listening...", "listening")
        self.recorder.start_recording()

    def on_hotkey_up(self):
        """User released push-to-talk combo."""
        print("[CompanionManager] Hotkey released - processing...")
        audio_data = self.recorder.stop_recording()
        if audio_data is None or len(audio_data) < 16000 * 0.3:
            self.status_changed.emit("Ready", "normal")
            return

        self.status_changed.emit("Thinking...", "thinking")
        # Run transcription and response pipeline in background loop
        asyncio.run_coroutine_threadsafe(self._process_turn(audio_data), self._loop)

    def on_cancel(self):
        """Instant interrupt on Esc."""
        print("[CompanionManager] Cancel triggered.")
        self.player.stop()
        self.overlay.clear_annotations()
        self.status_changed.emit("Ready", "normal")

    # ── Pipeline Processing ──

    async def _process_turn(self, audio_data):
        # 1. Transcribe audio
        transcription = self.stt.transcribe(audio_data)
        if not transcription:
            self.status_changed.emit("Didn't catch that", "normal")
            return

        print(f"[CompanionManager] User query: '{transcription}'")
        self.query_received.emit(transcription)

        # 2. Check for quick commands
        if is_stop(transcription):
            self.on_cancel()
            return

        if is_repeat(transcription) and self.last_answer:
            await self._speak_response(self.last_answer)
            return

        # 3. Detect Agent Mode activation
        is_agent_query = self.is_agent_mode or is_agent(transcription)

        if is_agent_query:
            await self._run_agent_pipeline(transcription)
        else:
            await self._run_talk_pipeline(transcription)

    async def _run_talk_pipeline(self, query: str):
        # 1. Capture screen context
        window_title = active_window_title()
        screenshots = capture_all_screens(max_width=cfg.max_screenshot_width)

        # 2. Check per-app history
        k = app_key(window_title)
        history = self.app_histories.setdefault(k, [])[-8:]  # Keep last 8 turns

        # 3. Format system prompt
        sys_prompt = CLICKY_SYSTEM_PROMPT.format(window_title=window_title)

        # Check for web search requirement
        search_context = ""
        if cfg.web_search_enabled and any(w in query.lower() for w in ["latest", "news", "today", "weather", "who won", "price"]):
            search_context = await WebSearcher.format_search_context(query)
            if search_context:
                sys_prompt += f"\n\nAdditional Real-Time Web Context:\n{search_context}"

        # 4. Query AI provider
        provider = self.get_active_provider()
        self.status_changed.emit("Thinking...", "thinking")
        response = await provider.ask(query, sys_prompt, screenshots, history)

        # Record history
        history.append({"role": "user", "content": query})
        history.append({"role": "model", "content": response})
        self.last_answer = response

        # 5. Parse Visual Tags ([POINT], [ARROW], etc.)
        self._parse_and_dispatch_tags(response)

        # 6. Update UI & Speak
        self.answer_received.emit(response)
        await self._speak_response(response)

    async def _run_agent_pipeline(self, objective: str):
        """HeyClicky Max Autonomous Agent execution."""
        self.status_changed.emit("Agent Working...", "agent")
        provider = self.get_active_provider()

        def _progress(msg):
            self.answer_received.emit(msg)

        runtime = AgentRuntime(provider, on_progress=_progress)
        final_answer = await runtime.run(objective)

        self.last_answer = final_answer
        self.answer_received.emit(final_answer)
        await self._speak_response(final_answer)

    def _parse_and_dispatch_tags(self, text: str):
        """Finds and triggers overlay animations for Clicky tags."""
        # [POINT:x,y:label] or [POINT:x,y]
        point_matches = re.finditer(r"\[POINT:(\d+),(\d+)(?::([^\]]*))?\]", text)
        for m in point_matches:
            x = float(m.group(1))
            y = float(m.group(2))
            label = m.group(3) or ""
            self.point_requested.emit(x, y, label)

        # [ARROW:x1,y1->x2,y2]
        arrow_matches = re.finditer(r"\[ARROW:(\d+),(\d+)->(\d+),(\d+)\]", text)
        for m in arrow_matches:
            self.annotation_requested.emit("arrow", [
                float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
            ])

        # [CIRCLE:x,y,r:label]
        circle_matches = re.finditer(r"\[CIRCLE:(\d+),(\d+),(\d+)(?::([^\]]*))?\]", text)
        for m in circle_matches:
            self.annotation_requested.emit("circle", [
                float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4) or ""
            ])

        # [LABEL:x,y:text]
        label_matches = re.finditer(r"\[LABEL:(\d+),(\d+):([^\]]*)\]", text)
        for m in label_matches:
            self.annotation_requested.emit("label", [
                float(m.group(1)), float(m.group(2)), m.group(3)
            ])

    def _handle_annotation(self, kind: str, args: list):
        if kind == "arrow":
            self.overlay.add_arrow(args[0], args[1], args[2], args[3])
        elif kind == "circle":
            self.overlay.add_circle(args[0], args[1], args[2], args[3])
        elif kind == "label":
            self.overlay.add_label(args[0], args[1], args[2])

    async def _speak_response(self, text: str):
        self.status_changed.emit("Speaking...", "speaking")
        clean = clean_text_for_speech(text)
        if not clean:
            self.status_changed.emit("Ready", "normal")
            return

        out_file = os.path.join(self._temp_dir, f"speech_{int(time.time()*1000)}.mp3")

        # Try Edge TTS first (free neural voice)
        success = await self.tts.synthesize(clean, out_file)
        if not success:
            # Fallback to macOS native say
            out_file_aiff = os.path.join(self._temp_dir, f"speech_{int(time.time()*1000)}.aiff")
            success = await self.macos_tts.synthesize(clean, out_file_aiff)
            out_file = out_file_aiff

        if success:
            self.player.play_file(out_file, on_finished=lambda: self.status_changed.emit("Ready", "normal"))
        else:
            self.status_changed.emit("Ready", "normal")

    # ── UI Actions ──

    def toggle_mode(self):
        self.is_agent_mode = not self.is_agent_mode
        self.update_provider_ui()
        mode_str = "Agent Mode (HeyClicky Max)" if self.is_agent_mode else "Talk Mode"
        print(f"[CompanionManager] Switched to {mode_str}")
        self.status_changed.emit(f"Switched to {mode_str}", "normal")

    def toggle_panel(self):
        if self.panel.isVisible():
            self.panel.hide()
        else:
            self.panel.show()

    def open_settings(self):
        dlg = SettingsDialog(on_saved=self.update_provider_ui)
        dlg.exec()

    def test_pointing_flight(self):
        """Triggers a demonstration flight to test smooth bezier animation."""
        print("[CompanionManager] Testing pointer flight to (500, 300)")
        self.overlay.point_at(500, 300, label="Target Point")
        self.overlay.add_arrow(300, 450, 500, 310)

    def quit_app(self):
        self.hotkey_monitor.stop()
        self.recorder.close()
        self.player.stop()
        self._loop.call_soon_threadsafe(self._loop.stop)
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
