"""
Clicky macOS Configuration Manager.
Stores settings in ~/.config/clicky/config.json and reads environment variables.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load .env if present in workspace
load_dotenv()

CONFIG_DIR = Path.home() / ".config" / "clicky"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class ClickyConfig:
    # --- AI Provider & Model Choice ---
    # Providers: "gemini", "ollama", "openai", "claude"
    active_provider: str = "gemini"
    
    # Model IDs
    gemini_model: str = "gemini-2.5-flash"
    ollama_model: str = "llama3.2-vision"
    openai_model: str = "gpt-4o"
    claude_model: str = "claude-3-5-sonnet-20241022"
    
    # Endpoints
    ollama_host: str = "http://localhost:11434"
    
    # API Keys (can also be supplied via ENV)
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    
    # --- Voice & Speech ---
    # TTS Provider: "edge", "macos", "openai", "elevenlabs"
    tts_provider: str = "edge"
    edge_voice: str = "en-US-AvaNeural"
    tts_rate: str = "+0%"
    tts_volume: str = "+0%"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    
    # STT Provider: "faster_whisper", "deepgram", "openai"
    stt_provider: str = "faster_whisper"
    whisper_model_size: str = "base.en"  # "tiny.en", "base.en", "small.en"
    deepgram_api_key: str = ""
    
    # --- Hotkey & Activation ---
    # "ctrl+alt" corresponds to Control + Option on macOS
    hotkey: str = "ctrl+alt"
    push_to_talk: bool = True
    
    # --- Screen & Overlay ---
    max_screenshot_width: int = 1280
    cursor_speed: float = 1.0  # 1.0 normal, 0.6 slower tutor pace
    dwell_duration_ms: int = 3500
    highlight_color: str = "#3B82F6"  # Clicky blue
    annotation_fade_seconds: float = 4.0
    
    # --- Agent Mode (HeyClicky Max) ---
    agent_mode_enabled: bool = True
    agent_auto_confirm_safe: bool = True
    agent_workspace_dir: str = str(Path.home() / "dev" / "clicky-mac-workspace")
    
    # --- Tutor Features ---
    per_app_memory: bool = True
    code_mode_auto: bool = True
    web_search_enabled: bool = True


class ConfigManager:
    """Manages loading, saving, and updating Clicky configuration."""

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
        if os.getenv("GEMINI_API_KEY"):
            self.config.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        if os.getenv("GOOGLE_API_KEY") and not self.config.gemini_api_key:
            self.config.gemini_api_key = os.getenv("GOOGLE_API_KEY", "")
        if os.getenv("OPENAI_API_KEY"):
            self.config.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if os.getenv("ANTHROPIC_API_KEY"):
            self.config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if os.getenv("ELEVENLABS_API_KEY"):
            self.config.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if os.getenv("DEEPGRAM_API_KEY"):
            self.config.deepgram_api_key = os.getenv("DEEPGRAM_API_KEY", "")
        if os.getenv("OLLAMA_HOST"):
            self.config.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

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
