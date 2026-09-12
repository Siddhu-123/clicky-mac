"""
Settings Dialog for Clicky macOS.
Allows user to easily switch AI providers, choose models, configure API keys and TTS voices.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from config import cfg, cfg_manager


class SettingsDialog(QDialog):
    def __init__(self, parent=None, on_saved=None):
        super().__init__(parent)
        self.on_saved = on_saved
        self.setWindowTitle("Clicky Settings")
        self.setFixedSize(460, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #1E293B;
                color: #F8FAFC;
            }
            QLabel {
                color: #E2E8F0;
                font-size: 12px;
            }
            QLineEdit, QComboBox {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                color: #F8FAFC;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3B82F6;
            }
            QGroupBox {
                font-weight: 700;
                font-size: 12px;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton#cancel {
                background-color: #334155;
            }
            QPushButton#cancel:hover {
                background-color: #475569;
            }
        """)

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── AI Provider & Models ──
        ai_group = QGroupBox("AI Provider & Model", self)
        ai_form = QFormLayout(ai_group)
        ai_form.setSpacing(8)

        self.provider_combo = QComboBox(self)
        self.provider_combo.addItems([
            "Gemini (Free Cloud)",
            "Ollama (Local Offline)",
            "OpenAI",
            "Claude",
            "Demo (Test Pointing & TTS)",
        ])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        ai_form.addRow("Active Provider:", self.provider_combo)

        self.model_input = QLineEdit(self)
        ai_form.addRow("Model ID:", self.model_input)

        self.api_key_input = QLineEdit(self)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_label = QLabel("API Key:")
        ai_form.addRow(self.api_key_label, self.api_key_input)

        self.ollama_host_input = QLineEdit(self)
        self.ollama_host_input.setPlaceholderText("http://localhost:11434")
        self.ollama_label = QLabel("Ollama URL:")
        ai_form.addRow(self.ollama_label, self.ollama_host_input)

        layout.addWidget(ai_group)

        # ── Voice & Speech ──
        voice_group = QGroupBox("Voice & Audio", self)
        voice_form = QFormLayout(voice_group)
        voice_form.setSpacing(8)

        self.tts_combo = QComboBox(self)
        self.tts_combo.addItems(["Edge TTS (Free 400+ Voices)", "macOS Native Voice (say)"])
        voice_form.addRow("TTS Engine:", self.tts_combo)

        self.voice_combo = QComboBox(self)
        self.voice_combo.addItems([
            "en-US-AvaNeural",
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-US-AriaNeural",
            "en-GB-SoniaNeural",
            "en-AU-NatashaNeural",
        ])
        voice_form.addRow("Edge Voice:", self.voice_combo)

        self.stt_combo = QComboBox(self)
        self.stt_combo.addItems(["faster-whisper (Local base.en)", "faster-whisper (Local tiny.en)"])
        voice_form.addRow("Speech-to-Text:", self.stt_combo)

        layout.addWidget(voice_group)

        # ── Shortcuts & Mode ──
        pref_group = QGroupBox("Preferences & Hotkey", self)
        pref_form = QFormLayout(pref_group)
        pref_form.setSpacing(8)

        self.hotkey_input = QLineEdit(self)
        self.hotkey_input.setPlaceholderText("ctrl+alt")
        pref_form.addRow("Push-to-Talk Hotkey:", self.hotkey_input)

        layout.addWidget(pref_group)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Settings", self)
        save_btn.clicked.connect(self._save_values)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_values(self):
        # Set provider
        p = cfg.active_provider.lower()
        if p == "gemini":
            self.provider_combo.setCurrentIndex(0)
            self.model_input.setText(cfg.gemini_model)
            self.api_key_input.setText(cfg.gemini_api_key)
        elif p == "ollama":
            self.provider_combo.setCurrentIndex(1)
            self.model_input.setText(cfg.ollama_model)
        elif p == "openai":
            self.provider_combo.setCurrentIndex(2)
            self.model_input.setText(cfg.openai_model)
            self.api_key_input.setText(cfg.openai_api_key)
        elif p == "claude":
            self.provider_combo.setCurrentIndex(3)
            self.model_input.setText(cfg.claude_model)
            self.api_key_input.setText(cfg.anthropic_api_key)
        elif p == "demo":
            self.provider_combo.setCurrentIndex(4)
            self.model_input.setText("demo-mode")

        self.ollama_host_input.setText(cfg.ollama_host)
        self.hotkey_input.setText(cfg.hotkey)

        # Voice
        idx = self.voice_combo.findText(cfg.edge_voice)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)

        self._on_provider_changed(self.provider_combo.currentIndex())

    def _on_provider_changed(self, index: int):
        is_ollama = (index == 1)
        is_demo = (index == 4)
        self.ollama_label.setVisible(is_ollama)
        self.ollama_host_input.setVisible(is_ollama)
        self.api_key_label.setVisible(not is_ollama and not is_demo)
        self.api_key_input.setVisible(not is_ollama and not is_demo)

        # Update placeholder / default model
        if index == 0:
            self.model_input.setText(cfg.gemini_model or "gemini-2.5-flash")
            self.api_key_input.setText(cfg.gemini_api_key)
        elif index == 1:
            self.model_input.setText(cfg.ollama_model or "llama3.2-vision")
        elif index == 2:
            self.model_input.setText(cfg.openai_model or "gpt-4o")
            self.api_key_input.setText(cfg.openai_api_key)
        elif index == 3:
            self.model_input.setText(cfg.claude_model or "claude-3-5-sonnet-20241022")
            self.api_key_input.setText(cfg.anthropic_api_key)
        elif index == 4:
            self.model_input.setText("demo-mode")

    def _save_values(self):
        idx = self.provider_combo.currentIndex()
        providers = ["gemini", "ollama", "openai", "claude", "demo"]
        chosen_provider = providers[idx]

        model_id = self.model_input.text().strip()
        api_key = self.api_key_input.text().strip()
        ollama_host = self.ollama_host_input.text().strip() or "http://localhost:11434"
        hotkey_str = self.hotkey_input.text().strip() or "ctrl+alt"
        chosen_voice = self.voice_combo.currentText()

        updates = {
            "active_provider": chosen_provider,
            "ollama_host": ollama_host,
            "hotkey": hotkey_str,
            "edge_voice": chosen_voice,
        }

        if chosen_provider == "gemini":
            updates["gemini_model"] = model_id
            updates["gemini_api_key"] = api_key
        elif chosen_provider == "ollama":
            updates["ollama_model"] = model_id
        elif chosen_provider == "openai":
            updates["openai_model"] = model_id
            updates["openai_api_key"] = api_key
        elif chosen_provider == "claude":
            updates["claude_model"] = model_id
            updates["anthropic_api_key"] = api_key

        cfg_manager.update(**updates)

        if self.on_saved:
            self.on_saved()

        self.accept()
