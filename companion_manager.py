"""
Central Orchestrator for Clicky macOS (Apple MLX Edition).
Connects push-to-talk, Retina screen capture, Apple Silicon MLX (Qwen-VL),
smooth bezier pointing, and HeyClicky Max Agent Mode.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import re
import tempfile
import threading
import time
import traceback
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
import subprocess
from tutor import active_window_title, app_key, is_agent, is_locate, is_repeat, is_sensitive_window, is_stop, parse_open_app
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
   - Identify its coordinates as seen in the provided screenshot image.
   - Include a tag: [POINT:x,y:label] where x and y are coordinates in the screenshot image.
   - Speak in 1-2 concise, friendly sentences.
2. You can also draw visual whiteboard annotations:
   - [ARROW:x1,y1->x2,y2]
   - [CIRCLE:x,y,radius:label]
   - [LABEL:x,y:text]
3. Explain directly and clearly without fluff.
"""

# Model-compatible annotation tag patterns.
# The vision model reports coordinates in the (downscaled) screenshot image space;
# CompanionManager scales them into macOS logical points before dispatching to the overlay.
_NUM = r"\d+(?:\.\d+)?"
_POINT_RE = re.compile(
    rf"\[POINT:\s*({_NUM})\s*,\s*({_NUM})\s*(?:[:,]\s*[\"']?([^\"'\]]*)[\"']?)?\s*\]"
)
_ARROW_RE = re.compile(
    rf"\[ARROW:\s*({_NUM})\s*,\s*({_NUM})\s*->\s*({_NUM})\s*,\s*({_NUM})\s*\]"
)
_CIRCLE_RE = re.compile(
    rf"\[CIRCLE:\s*({_NUM})\s*,\s*({_NUM})\s*,\s*({_NUM})\s*(?:[:,]\s*[\"']?([^\"'\]]*)[\"']?)?\s*\]"
)
_LABEL_RE = re.compile(
    rf"\[LABEL:\s*({_NUM})\s*,\s*({_NUM})\s*(?:[:,]\s*[\"']?([^\"'\]]*)[\"']?)?\s*\]"
)
_TAG_RE = re.compile(r"\[(?:POINT|ARROW|CIRCLE|LABEL|TYPE|UNDERLINE):[^\]]*\]")


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

        self._is_recording = False
        self.overlay = OverlayWindow()
        self.panel = CompanionPanel(
            on_toggle_mode=self.toggle_mode,
            on_open_settings=self.open_settings,
            on_submit_text=self.on_text_query,
            on_toggle_voice=self.toggle_voice_recording,
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
        self.status_changed.connect(lambda text, state: self.tray.update_status(text))
        self.query_received.connect(self.panel.set_user_query)
        self.answer_received.connect(self.panel.set_answer)
        self.point_requested.connect(self.overlay.point_at)
        self.annotation_requested.connect(self._handle_annotation)

        # Last screenshot the model saw (used to map model coords -> logical points)
        self._last_view_screenshot: Optional[ScreenShot] = None

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
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()
        self.tray.show()
        self.hotkey_monitor.start()
        self.update_provider_ui()
        print("[CompanionManager] Clicky (MLX Apple Silicon) started.")

        # Warm up MLX model in background so first query has zero lag
        def _warmup():
            try:
                self.status_changed.emit("Loading MLX Model...", "thinking")
                self.mlx_engine.ensure_model_loaded()
                self.status_changed.emit("Ready", "normal")
            except Exception as e:
                message = str(e).strip() or type(e).__name__
                self.status_changed.emit(f"Error: {message}", "normal")

        threading.Thread(target=_warmup, daemon=True).start()

    def update_provider_ui(self):
        # Format model name (e.g. "Qwen2-VL 2B 4-bit")
        short_name = cfg.mlx_model.split("/")[-1].replace("-Instruct", "").replace("-4bit", " 4-bit")
        self.panel.update_model_badge("Apple MLX", short_name)
        self.panel.update_mode_badge(self.is_agent_mode)
        self.tray.update_mode_label(self.is_agent_mode)

    # ── Push-to-Talk Lifecycle ──

    def toggle_voice_recording(self):
        if not self._is_recording:
            self._is_recording = True
            self.on_hotkey_down()
        else:
            self._is_recording = False
            self.on_hotkey_up()

    def on_hotkey_down(self):
        self._is_recording = True
        self.player.stop()
        self.status_changed.emit("Listening...", "listening")
        self.recorder.start_recording()

    def on_hotkey_up(self):
        self._is_recording = False
        audio_data = self.recorder.stop_recording()
        if audio_data is None or len(audio_data) < 16000 * 0.3:
            self.status_changed.emit("Ready", "normal")
            return

        self.status_changed.emit("Thinking...", "thinking")
        future = asyncio.run_coroutine_threadsafe(self._process_turn(audio_data), self._loop)
        future.add_done_callback(self._handle_turn_future)

    def on_text_query(self, text: str):
        query = text.strip()
        if not query:
            return
        self.player.stop()
        self.query_received.emit(query)
        self.status_changed.emit("Thinking...", "thinking")
        future = asyncio.run_coroutine_threadsafe(self._process_query_turn(query), self._loop)
        future.add_done_callback(self._handle_turn_future)

    def _handle_turn_future(self, future: concurrent.futures.Future):
        if future.cancelled():
            return
        error = future.exception()
        if error is None:
            return
        traceback.print_exception(type(error), error, error.__traceback__)
        message = str(error).strip() or type(error).__name__
        self.status_changed.emit(f"Error: {message}", "normal")

    def on_cancel(self):
        self._is_recording = False
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

        # Check for direct app launch command (e.g. "Open Google Chrome")
        app_target = parse_open_app(query)
        if app_target:
            self.status_changed.emit(f"Opening {app_target}...", "agent")
            try:
                res = subprocess.run(["open", "-a", app_target], capture_output=True, text=True)
                if res.returncode == 0:
                    reply = f"Opening {app_target} for you."
                else:
                    reply = f"Opening {app_target}..."
                    subprocess.run(["open", "-g", f"/Applications/{app_target}.app"])
            except Exception as e:
                reply = f"Could not launch {app_target}: {e}"

            self.last_answer = reply
            self.answer_received.emit(reply)
            self.status_changed.emit("Ready", "normal")
            await self._speak_response(reply)
            return

        is_agent_query = self.is_agent_mode or is_agent(query)
        if is_agent_query:
            await self._run_agent_pipeline(query)
        else:
            await self._run_talk_pipeline(query)

    async def _run_talk_pipeline(self, query: str):
        window_title = active_window_title()
        if is_sensitive_window(window_title):
            screenshots = []
            self._last_view_screenshot = None
        else:
            screenshots = capture_all_screens(max_width=cfg.max_screenshot_width)
            self._last_view_screenshot = screenshots[0] if screenshots else None

        k = app_key(window_title)
        history = self.app_histories.setdefault(k, [])

        sys_prompt = CLICKY_SYSTEM_PROMPT.format(window_title=window_title)

        # Real-time web search if needed
        if cfg.web_search_enabled and any(w in query.lower() for w in ["latest", "news", "today", "weather", "price"]):
            search_context = await WebSearcher.format_search_context(query)
            if search_context:
                sys_prompt += f"\n\nWeb Information:\n{search_context}"

        self.status_changed.emit("MLX Inferencing...", "thinking")
        response = await self.mlx_engine.ask(query, sys_prompt, screenshots, history[-6:])

        # Update history
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": response})

        # Parse and show visual tags, and get human-readable clean text for HUD
        display_text = self._parse_and_dispatch_tags(response)
        self.last_answer = display_text

        # Update HUD & Speak
        self.status_changed.emit("Ready", "normal")
        self.answer_received.emit(display_text)
        await self._speak_response(display_text)

    async def _run_agent_pipeline(self, objective: str):
        self.status_changed.emit("Agent Working...", "agent")

        def _progress(msg):
            self.answer_received.emit(msg)

        runtime = AgentRuntime(self.mlx_engine, on_progress=_progress)
        final_answer = await runtime.run(objective)

        self.last_answer = final_answer
        self.status_changed.emit("Ready", "normal")
        self.answer_received.emit(final_answer)
        await self._speak_response(final_answer)

    def _map_model_coords(self, x: float, y: float):
        """Scales model-reported (screenshot image) coordinates into macOS logical points."""
        sc = self._last_view_screenshot
        if sc is None or sc.width <= 0 or sc.height <= 0:
            return float(x), float(y)
        sx = sc.logical_left + x * (sc.logical_width / sc.width)
        sy = sc.logical_top + y * (sc.logical_height / sc.height)
        return float(sx), float(sy)

    def _map_model_scale(self, value: float) -> float:
        """Scales a length (e.g. circle radius) from image space to logical points."""
        sc = self._last_view_screenshot
        if sc is None or sc.width <= 0 or sc.height <= 0:
            return float(value)
        sx = sc.logical_width / sc.width
        sy = sc.logical_height / sc.height
        return float(value * (sx + sy) / 2.0)

    def _parse_and_dispatch_tags(self, text: str) -> str:
        first_label = ""

        # [POINT:x,y:label] or [POINT:x, y, "label"]
        for m in _POINT_RE.finditer(text):
            x, y = self._map_model_coords(float(m.group(1)), float(m.group(2)))
            label = (m.group(3) or "").strip().strip("\"'")
            if not first_label and label:
                first_label = label
            self.point_requested.emit(x, y, label)

        # [ARROW:x1,y1->x2,y2]
        for m in _ARROW_RE.finditer(text):
            x1, y1 = self._map_model_coords(float(m.group(1)), float(m.group(2)))
            x2, y2 = self._map_model_coords(float(m.group(3)), float(m.group(4)))
            self.annotation_requested.emit("arrow", [x1, y1, x2, y2])

        # [CIRCLE:x,y,r:label]
        for m in _CIRCLE_RE.finditer(text):
            x, y = self._map_model_coords(float(m.group(1)), float(m.group(2)))
            radius = self._map_model_scale(float(m.group(3)))
            self.annotation_requested.emit(
                "circle", [x, y, radius, (m.group(4) or "").strip().strip("\"'")]
            )

        # [LABEL:x,y:text]
        for m in _LABEL_RE.finditer(text):
            x, y = self._map_model_coords(float(m.group(1)), float(m.group(2)))
            label = (m.group(3) or "").strip().strip("\"'")
            if label:
                self.annotation_requested.emit("label", [x, y, label])

        # Clean tags from text for human display in HUD
        clean_text = _TAG_RE.sub("", text).strip()
        if not clean_text and first_label:
            clean_text = f"Pointing to {first_label} on your screen."
        elif not clean_text:
            clean_text = "Here it is on your screen."
        return clean_text

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
            self.panel._set_default_position()
            self.panel.show()
            self.panel.raise_()
            self.panel.activateWindow()

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
