"""
Central Orchestrator for Clicky macOS (Apple MLX Edition).
Connects push-to-talk, Retina screen capture, Apple Silicon MLX (Qwen-VL),
smooth bezier pointing, and HeyClicky Max Agent Mode.
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
from ai.mlx_engine import MLXEngine
from ai.web_search import WebSearcher
from audio.capture import AudioRecorder
from audio.playback import AudioPlayer
from audio.stt.faster_whisper_stt import FasterWhisperSTT
from audio.tts.edge_tts_provider import EdgeTTSProvider, clean_text_for_speech
from audio.tts.macos_tts_provider import MacOSTTSProvider
from config import cfg, cfg_manager
from hotkey import GlobalHotkeyMonitor
from screen.capture import ScreenShot, capture_all_screens
from tutor import active_window_title, app_key, is_agent, is_locate, is_repeat, is_stop
from ui.overlay import OverlayWindow
from ui.panel import CompanionPanel
from ui.settings_dialog import SettingsDialog
from ui.tray import ClickyTrayIcon

CLICKY_SYSTEM_PROMPT = """You are Clicky, an AI tutor buddy living next to the user's cursor on macOS.
Powered by Apple Silicon MLX and Qwen Vision.

Screen Context:
- Active window: {window_title}
- Screen capture is provided.

Guidelines:
1. When asked where an element, button, or menu is:
   - Identify its coordinates on screen.
   - Include a tag: [POINT:x,y:label] where x and y are in logical screen coordinates.
   - Speak in 1-2 concise, friendly sentences.
2. You can also draw visual whiteboard annotations:
   - [ARROW:x1,y1->x2,y2]
   - [CIRCLE:x,y,radius:label]
   - [LABEL:x,y:text]
3. Explain directly and clearly without fluff.
"""


class CompanionManager(QObject):
    status_changed = pyqtSignal(str, str)  # text, state
    query_received = pyqtSignal(str)
    answer_received = pyqtSignal(str)
    point_requested = pyqtSignal(float, float, str)
    annotation_requested = pyqtSignal(str, list)

    def __init__(self):
        super().__init__()
        self.is_agent_mode = False

        # Audio & Screen
        self.recorder = AudioRecorder(sample_rate=16000)
        self.player = AudioPlayer()
        self.stt = FasterWhisperSTT()
        self.tts = EdgeTTSProvider()
        self.macos_tts = MacOSTTSProvider()

        # Pure Apple MLX Engine
        self.mlx_engine = MLXEngine()

        # UI Components
        self.overlay = OverlayWindow()
        self.panel = CompanionPanel(
            on_toggle_mode=self.toggle_mode,
            on_open_settings=self.open_settings,
            on_submit_text=self.on_text_query,
        )
        self.tray = ClickyTrayIcon(
            on_toggle_panel=self.toggle_panel,
            on_toggle_mode=self.toggle_mode,
            on_open_settings=self.open_settings,
            on_test_point=self.test_pointing_flight,
            on_quit=self.quit_app,
        )

        # Per-app memory & state
        self.app_histories: Dict[str, List[Dict[str, str]]] = {}
        self.last_answer: str = ""

        # Connect signals
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

        self._temp_dir = tempfile.mkdtemp(prefix="clicky_tts_")

        # Background async worker
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._loop_thread.start()

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self):
        self.overlay.show()
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()
        self.tray.show()
        self.hotkey_monitor.start()
        self.update_provider_ui()
        print("[CompanionManager] Clicky (MLX Apple Silicon) started.")

        # Warm up MLX model in background so first query has zero lag
        def _warmup():
            self.status_changed.emit("Loading MLX Model...", "thinking")
            self.mlx_engine.ensure_model_loaded()
            self.status_changed.emit("Ready", "normal")

        threading.Thread(target=_warmup, daemon=True).start()

    def update_provider_ui(self):
        # Format model name (e.g. "Qwen2-VL 2B 4-bit")
        short_name = cfg.mlx_model.split("/")[-1].replace("-Instruct", "").replace("-4bit", " 4-bit")
        self.panel.update_model_badge("Apple MLX", short_name)
        self.panel.update_mode_badge(self.is_agent_mode)
        self.tray.update_mode_label(self.is_agent_mode)

    # ── Push-to-Talk Lifecycle ──

    def on_hotkey_down(self):
        self.player.stop()
        self.status_changed.emit("Listening...", "listening")
        self.recorder.start_recording()

    def on_hotkey_up(self):
        audio_data = self.recorder.stop_recording()
        if audio_data is None or len(audio_data) < 16000 * 0.3:
            self.status_changed.emit("Ready", "normal")
            return

        self.status_changed.emit("Thinking...", "thinking")
        asyncio.run_coroutine_threadsafe(self._process_turn(audio_data), self._loop)

    def on_text_query(self, text: str):
        query = text.strip()
        if not query:
            return
        self.player.stop()
        self.query_received.emit(query)
        self.status_changed.emit("Thinking...", "thinking")
        asyncio.run_coroutine_threadsafe(self._process_query_turn(query), self._loop)

    def on_cancel(self):
        self.player.stop()
        self.overlay.clear_annotations()
        self.status_changed.emit("Ready", "normal")

    # ── Turn Processing ──

    async def _process_turn(self, audio_data):
        transcription = self.stt.transcribe(audio_data)
        if not transcription:
            self.status_changed.emit("Didn't catch that", "normal")
            return

        self.query_received.emit(transcription)
        await self._process_query_turn(transcription)

    async def _process_query_turn(self, query: str):
        if is_stop(query):
            self.on_cancel()
            return

        if is_repeat(query) and self.last_answer:
            await self._speak_response(self.last_answer)
            return

        is_agent_query = self.is_agent_mode or is_agent(query)
        if is_agent_query:
            await self._run_agent_pipeline(query)
        else:
            await self._run_talk_pipeline(query)

    async def _run_talk_pipeline(self, query: str):
        window_title = active_window_title()
        screenshots = capture_all_screens(max_width=cfg.max_screenshot_width)

        k = app_key(window_title)
        history = self.app_histories.setdefault(k, [])[-6:]

        sys_prompt = CLICKY_SYSTEM_PROMPT.format(window_title=window_title)

        # Real-time web search if needed
        if cfg.web_search_enabled and any(w in query.lower() for w in ["latest", "news", "today", "weather", "price"]):
            search_context = await WebSearcher.format_search_context(query)
            if search_context:
                sys_prompt += f"\n\nWeb Information:\n{search_context}"

        self.status_changed.emit("MLX Inferencing...", "thinking")
        response = await self.mlx_engine.ask(query, sys_prompt, screenshots, history)

        # Update history
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": response})
        self.last_answer = response

        # Parse and show visual tags
        self._parse_and_dispatch_tags(response)

        # Update HUD & Speak
        self.answer_received.emit(response)
        await self._speak_response(response)

    async def _run_agent_pipeline(self, objective: str):
        self.status_changed.emit("Agent Working...", "agent")

        def _progress(msg):
            self.answer_received.emit(msg)

        runtime = AgentRuntime(self.mlx_engine, on_progress=_progress)
        final_answer = await runtime.run(objective)

        self.last_answer = final_answer
        self.answer_received.emit(final_answer)
        await self._speak_response(final_answer)

    def _parse_and_dispatch_tags(self, text: str):
        # [POINT:x,y:label]
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
        success = await self.tts.synthesize(clean, out_file)
        if not success:
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
        self.status_changed.emit(f"Switched to {mode_str}", "normal")

    def toggle_panel(self):
        if self.panel.isVisible():
            self.panel.hide()
        else:
            self.panel.show()

    def open_settings(self):
        dlg = SettingsDialog(on_saved=self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self):
        self.update_provider_ui()
        # Reload model if changed
        if self.mlx_engine.model_id != cfg.mlx_model:
            threading.Thread(target=self.mlx_engine.ensure_model_loaded, daemon=True).start()

    def test_pointing_flight(self):
        self.overlay.point_at(500, 300, label="Target Point")
        self.overlay.add_arrow(300, 450, 500, 310)

    def quit_app(self):
        self.hotkey_monitor.stop()
        self.recorder.close()
        self.player.stop()
        self._loop.call_soon_threadsafe(self._loop.stop)
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
