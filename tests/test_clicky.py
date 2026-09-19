"""
Automated unit tests for Clicky macOS (Apple MLX Edition).
"""

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from config import ConfigManager
from screen.capture import capture_all_screens, get_macos_dpi_scale
from tutor import is_agent, is_locate, is_multistep, is_next, is_repeat, is_stop, app_key
from ai.universal_locator import UniversalLocator
from ai.web_search import WebSearcher
from audio.tts.edge_tts_provider import EdgeTTSProvider, clean_text_for_speech
from agent.tools import AgentTools
from agent.runtime import AgentRuntime
from ai.mlx_engine import MLXEngine


class TestClickyMacOS(unittest.TestCase):
    def test_config_manager(self):
        cm = ConfigManager()
        self.assertIsNotNone(cm.config)
        self.assertIn("Qwen", cm.config.mlx_model)

    def test_tutor_classifiers(self):
        self.assertTrue(is_locate("where is the save button?"))
        self.assertTrue(is_locate("how do i click settings?"))
        self.assertTrue(is_multistep("how do i export this video?"))
        self.assertTrue(is_next("next"))
        self.assertTrue(is_stop("stop"))
        self.assertTrue(is_repeat("say that again"))
        self.assertTrue(is_agent("heyclicky agent organize my downloads"))
        self.assertTrue(is_agent("can you automate this workflow"))
        self.assertEqual(app_key("Safari — Google Search"), "Safari")

    def test_clean_text_for_speech(self):
        raw = "Click on the Apple icon [POINT:20,15:Apple menu] to open preferences."
        cleaned = clean_text_for_speech(raw)
        self.assertEqual(cleaned, "Click on the Apple icon to open preferences.")

    def test_screen_capture(self):
        dpi = get_macos_dpi_scale()
        self.assertGreaterEqual(dpi, 1.0)
        screens = capture_all_screens(max_width=800)
        self.assertGreater(len(screens), 0)
        sc = screens[0]
        self.assertGreater(sc.width, 0)
        self.assertGreater(sc.height, 0)
        self.assertIsNotNone(sc.base64_jpeg)
        self.assertIsNotNone(sc.pil_image)

    def test_universal_locator(self):
        screens = capture_all_screens(max_width=800)
        sc = screens[0]
        coarse_sc = UniversalLocator.generate_coarse_grid(sc)
        self.assertEqual(coarse_sc.width, sc.width)
        x, y = UniversalLocator.cell_to_logical_point(1, sc, cols=12, rows=8)
        self.assertGreaterEqual(x, sc.logical_left)
        self.assertGreaterEqual(y, sc.logical_top)

    def test_edge_tts_synthesis(self):
        async def _run():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                tmp_path = tf.name
            try:
                tts = EdgeTTSProvider()
                success = await tts.synthesize("Hello Clicky test", tmp_path)
                self.assertTrue(success)
                self.assertTrue(os.path.exists(tmp_path))
                self.assertGreater(os.path.getsize(tmp_path), 500)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        asyncio.run(_run())

    def test_agent_tools(self):
        # 1. Bash execution
        res = AgentTools.bash_run("echo 'hello clicky'")
        self.assertIn("hello clicky", res)

        # 2. File write and read
        with tempfile.TemporaryDirectory() as td:
            test_file = os.path.join(td, "test.txt")
            write_res = AgentTools.file_write(test_file, "Clicky agent mode verified")
            self.assertIn("Successfully wrote", write_res)
            content = AgentTools.file_read(test_file)
            self.assertEqual(content, "Clicky agent mode verified")

        # 3. Applescript
        apple_res = AgentTools.run_applescript('return "AppleScript OK"')
        self.assertEqual(apple_res, "AppleScript OK")

    def test_mlx_engine_instantiation(self):
        engine = MLXEngine()
        self.assertEqual(engine.provider_name, "mlx")
        self.assertIn("Qwen", engine.model_id)

    def test_parse_action_robust(self):
        """Action parsing must respect quotes and nested parens inside values."""
        rt = AgentRuntime(provider=None)

        # Normal keyword args
        tool, kwargs = rt._parse_action(
            'Thought: run it.\nAction: bash_run(command="echo hello clicky")'
        )
        self.assertEqual(tool, "bash_run")
        self.assertEqual(kwargs["command"], "echo hello clicky")

        # Parens and quote inside a quoted value must not truncate parsing
        tool, kwargs = rt._parse_action(
            'Action: file_write(file_path="a b.txt", content="hello, world!)")'
        )
        self.assertEqual(tool, "file_write")
        self.assertEqual(kwargs["file_path"], "a b.txt")
        self.assertEqual(kwargs["content"], "hello, world!)")

    def test_agent_runtime_uses_assistant_role_history(self):
        """MLX Qwen chat template renders <|im_start|>assistant, not 'model'."""
        rt = AgentRuntime(provider=None)

        recorded = []
        calls = {"n": 0}

        async def _fake_ask(self, prompt, system_prompt, screenshots=None, history=None):
            recorded.extend(history or [])
            calls["n"] += 1
            if calls["n"] == 1:
                return 'Thought: list the files.\nAction: bash_run(command="ls")'
            return "Thought: done.\nFinal Answer: all set"

        rt.provider = type("P", (), {"ask": _fake_ask})()
        result = asyncio.run(rt.run("list files"))
        self.assertTrue(recorded)
        roles = {m["role"] for m in recorded}
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)
        self.assertNotIn("model", roles)
        self.assertIn("all set", result)

    def test_parse_and_dispatch_tags_scales_coordinates(self):
        """Tags must be dispatched with model coords scaled into logical points."""
        from PyQt6.QtWidgets import QApplication
        from PIL import Image
        from companion_manager import CompanionManager
        from screen.capture import ScreenShot

        app = QApplication.instance() or QApplication(sys.argv)
        # NOTE: create the manager inline; creating it via a helper method lets
        # PyQt destroy the parentless QObject before its signals can be used.
        mgr = CompanionManager()
        self.addCleanup(mgr.quit_app)
        # Image the model sees is 1280px wide, display is 2560 logical points
        # (simulates a 2x physical->logical mapping after downscale).
        mgr._last_view_screenshot = ScreenShot(
            index=1,
            width=1280,
            height=720,
            base64_jpeg="",
            physical_width=5120,
            physical_height=2880,
            physical_left=0,
            physical_top=0,
            dpi_scale=2.0,
            logical_left=0,
            logical_top=0,
            logical_width=2560,
            logical_height=1440,
            pil_image=Image.new("RGB", (1280, 720), "white"),
        )

        points, annotations = [], []
        mgr.point_requested.connect(lambda x, y, l: points.append((x, y, l)))
        mgr.annotation_requested.connect(lambda k, a: annotations.append((k, a)))

        clean = mgr._parse_and_dispatch_tags(
            "[POINT:640,360:Save] [ARROW:0,0->100,100] "
            "[CIRCLE:320,180,40:ring] [LABEL:100,200:Note]"
        )

        # POINT scaled 640,360 -> 1280,720
        self.assertEqual(points, [(1280.0, 720.0, "Save")])
        kinds = {a[0]: a[1] for a in annotations}
        self.assertEqual(kinds["arrow"], [0.0, 0.0, 200.0, 200.0])
        self.assertEqual(kinds["circle"], [640.0, 360.0, 80.0, "ring"])
        self.assertEqual(kinds["label"], [200.0, 400.0, "Note"])
        # Non-tag text is preserved, tag-only text falls back to a label
        self.assertIn("Save", clean)

    def test_parse_and_dispatch_tags_label_is_reached(self):
        """LABEL annotations were previously dead code after an early return."""
        from PyQt6.QtWidgets import QApplication
        from companion_manager import CompanionManager

        app = QApplication.instance() or QApplication(sys.argv)
        mgr = CompanionManager()
        self.addCleanup(mgr.quit_app)
        annotations = []
        mgr.annotation_requested.connect(lambda k, a: annotations.append(k))
        mgr._parse_and_dispatch_tags("[LABEL:10,20:Hello Label]")
        self.assertIn("label", annotations)


if __name__ == "__main__":
    unittest.main()
