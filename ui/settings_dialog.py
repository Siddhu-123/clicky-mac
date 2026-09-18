"""
Settings Dialog for Clicky macOS (Apple MLX Edition).
Configure MLX Qwen model, voice, and push-to-talk hotkey.
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

MLX_PRESETS = [
    ("mlx-community/Qwen2-VL-2B-Instruct-4bit", "Qwen2-VL 2B 4-bit (Fastest, ~1.8 GB RAM) [Default]"),
    ("mlx-community/Qwen2.5-VL-3B-Instruct-4bit", "Qwen2.5-VL 3B 4-bit (Higher detail, ~2.5 GB RAM)"),
    ("mlx-community/Qwen2.5-VL-7B-Instruct-4bit", "Qwen2.5-VL 7B 4-bit (Maximum reasoning, ~5.5 GB RAM)"),
    ("custom", "Custom HuggingFace / Local Path..."),
]


class SettingsDialog(QDialog):
    def __init__(self, parent=None, on_saved=None):
        super().__init__(parent)
        self.on_saved = on_saved
        self.setWindowTitle("Clicky Settings (Apple MLX)")
        self.setFixedSize(450, 420)
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
        layout.setSpacing(14)

        # ── Apple Silicon MLX Model ──
        mlx_group = QGroupBox("Apple Silicon MLX Engine", self)
        mlx_form = QFormLayout(mlx_group)
        mlx_form.setSpacing(8)

        self.model_combo = QComboBox(self)
        for model_id, label in MLX_PRESETS:
            self.model_combo.addItem(label, model_id)
        self.model_combo.currentIndexChanged.connect(self._on_preset_changed)
        mlx_form.addRow("Model Preset:", self.model_combo)

        self.custom_model_input = QLineEdit(self)
        self.custom_model_input.setPlaceholderText("e.g. mlx-community/Qwen2-VL-2B-Instruct-4bit")
        mlx_form.addRow("Model Identifier:", self.custom_model_input)

        info_label = QLabel("Runs directly on Apple Silicon GPU via Metal with zero cloud lag.", self)
        info_label.setStyleSheet("color: #60A5FA; font-size: 11px; font-style: italic;")
        mlx_form.addRow("", info_label)

        layout.addWidget(mlx_group)

        # ── Voice & Audio ──
        voice_group = QGroupBox("Voice & Speech", self)
        voice_form = QFormLayout(voice_group)
        voice_form.setSpacing(8)

        self.voice_combo = QComboBox(self)
        self.voice_combo.addItems([
            "en-US-AvaNeural",
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-US-AriaNeural",
            "en-GB-SoniaNeural",
            "en-AU-NatashaNeural",
        ])
        voice_form.addRow("Edge Neural Voice:", self.voice_combo)

        layout.addWidget(voice_group)

        # ── Shortcut ──
        pref_group = QGroupBox("Shortcut", self)
        pref_form = QFormLayout(pref_group)
        pref_form.setSpacing(8)

        self.hotkey_input = QLineEdit(self)
        self.hotkey_input.setPlaceholderText("ctrl+alt")
        pref_form.addRow("Push-to-Talk:", self.hotkey_input)

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
        # Match current config model to preset
        current_m = cfg.mlx_model
        matched_idx = -1
        for i, (m_id, _) in enumerate(MLX_PRESETS):
            if m_id == current_m:
                matched_idx = i
                break

        if matched_idx >= 0:
            self.model_combo.setCurrentIndex(matched_idx)
            self.custom_model_input.setText(current_m)
            self.custom_model_input.setEnabled(False)
        else:
            self.model_combo.setCurrentIndex(len(MLX_PRESETS) - 1)  # custom
            self.custom_model_input.setText(current_m)
            self.custom_model_input.setEnabled(True)

        self.hotkey_input.setText(cfg.hotkey)

        idx = self.voice_combo.findText(cfg.edge_voice)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)

    def _on_preset_changed(self, index: int):
        m_id = self.model_combo.currentData()
        if m_id == "custom":
            self.custom_model_input.setEnabled(True)
        else:
            self.custom_model_input.setText(m_id)
            self.custom_model_input.setEnabled(False)

    def _save_values(self):
        m_id = self.model_combo.currentData()
        final_model = self.custom_model_input.text().strip() if m_id == "custom" else m_id

        hotkey_str = self.hotkey_input.text().strip() or "ctrl+alt"
        chosen_voice = self.voice_combo.currentText()

        cfg_manager.update(
            mlx_model=final_model,
            hotkey=hotkey_str,
            edge_voice=chosen_voice,
        )

        if self.on_saved:
            self.on_saved()

        self.accept()
