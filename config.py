"""
Clicky for macOS — Configuration Manager.
Streamlined for Apple Silicon MLX and Qwen Vision Models.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

CONFIG_DIR = Path.home() / ".config" / "clicky"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class ClickyConfig:
    # --- Apple Silicon MLX Vision Model ---
    # Default: Qwen2-VL 2B 4-bit (Fastest, ~1.8 GB RAM)
    # Alternative: mlx-community/Qwen2.5-VL-3B-Instruct-4bit (~2.5 GB RAM)
    mlx_model: str = "mlx-community/Qwen2-VL-2B-Instruct-4bit"
    max_tokens: int = 1024
    temperature: float = 0.2

    # --- Global Hotkey (macOS Control + Option) ---
    hotkey: str = "ctrl+alt"
    push_to_talk: bool = True

    # --- Voice & Speech (Local & Free) ---
    tts_provider: str = "edge"  # "edge" or "macos"
    edge_voice: str = "en-US-AvaNeural"
    tts_rate: str = "+0%"
    tts_volume: str = "+0%"

    # Speech-to-Text (Apple Silicon on-device)
    stt_provider: str = "faster_whisper"
    whisper_model_size: str = "base.en"

    # --- Screen Awareness & Pointing Overlay ---
    max_screenshot_width: int = 1280
    cursor_speed: float = 1.0
    dwell_duration_ms: int = 3500
    highlight_color: str = "#3B82F6"
    annotation_fade_seconds: float = 4.0

    # --- HeyClicky Max (Autonomous Agent Mode) ---
    agent_mode_enabled: bool = True
    agent_workspace_dir: str = str(Path.home() / "dev" / "clicky-mac-workspace")
    web_search_enabled: bool = True
    per_app_memory: bool = True


class ConfigManager:
    def __init__(self):
        self.config = ClickyConfig()
        self.load()

    def load(self) -> ClickyConfig:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(self.config, k):
                            setattr(self.config, k, v)
            except Exception as e:
                print(f"[Config] Error reading {CONFIG_FILE}: {e}")

        # Environment variable overrides
        if os.getenv("MLX_MODEL"):
            self.config.mlx_model = os.getenv("MLX_MODEL")
        if os.getenv("HOTKEY"):
            self.config.hotkey = os.getenv("HOTKEY")
        if os.getenv("EDGE_VOICE"):
            self.config.edge_voice = os.getenv("EDGE_VOICE")

        return self.config

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self.config), f, indent=2)
        except Exception as e:
            print(f"[Config] Error saving {CONFIG_FILE}: {e}")

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        self.save()


cfg_manager = ConfigManager()
cfg = cfg_manager.config
