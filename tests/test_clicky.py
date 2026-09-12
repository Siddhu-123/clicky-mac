"""
Automated unit tests for Clicky macOS modules.
"""

import asyncio
import os
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


class TestClickyMacOS(unittest.TestCase):
    def test_config_manager(self):
        cm = ConfigManager()
        self.assertIsNotNone(cm.config)
        self.assertIn(cm.config.active_provider, ["gemini", "ollama", "openai", "claude"])

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

    def test_mock_demo_provider(self):
        from ai.mock_provider import MockDemoProvider
        provider = MockDemoProvider()
        self.assertEqual(provider.provider_name, "demo")

        async def _test():
            resp = await provider.ask("Where is the save button?", "")
            self.assertIn("[POINT:", resp)
            self.assertIn("[ARROW:", resp)
        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
