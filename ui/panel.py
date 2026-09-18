"""
Floating HUD Panel for Clicky macOS.
Shows status, user query transcript, live streaming answers, and model badge.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config import cfg


class CompanionPanel(QWidget):
    """Floating HUD companion panel matching macOS dark design."""

    def __init__(self, on_toggle_mode=None, on_open_settings=None, on_submit_text=None):
        super().__init__()
        self.on_toggle_mode = on_toggle_mode
        self.on_open_settings = on_open_settings
        self.on_submit_text = on_submit_text

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(360, 310)

        # Drag state
        self._drag_pos = QPoint()

        self._build_ui()
        self._set_default_position()

    def _set_default_position(self):
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.right() - self.width() - 40
            y = geom.bottom() - self.height() - 40
            self.move(x, y)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Main glass frame
        self.card = QFrame(self)
        self.card.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 24, 36, 230);
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 14px;
            }
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        # ── Header bar ──
        header = QHBoxLayout()
        header.setSpacing(8)

        # App Title & Status pill
        self.title_label = QLabel("Clicky", self.card)
        self.title_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #FFFFFF; border: none;")

        self.status_pill = QLabel("Ready", self.card)
        self.status_pill.setStyleSheet("""
            QLabel {
                background-color: rgba(59, 130, 246, 0.2);
                color: #60A5FA;
                border: 1px solid rgba(59, 130, 246, 0.4);
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }
        """)

        header.addWidget(self.title_label)
        header.addWidget(self.status_pill)
        header.addStretch()

        # Mode Button (Talk / Agent)
        self.mode_btn = QPushButton("Talk", self.card)
        self.mode_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.3);
                border-color: #3B82F6;
            }
        """)
        if self.on_toggle_mode:
            self.mode_btn.clicked.connect(self.on_toggle_mode)
        header.addWidget(self.mode_btn)

        # Settings button
        self.settings_btn = QPushButton("⚙", self.card)
        self.settings_btn.setFixedSize(24, 24)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        if self.on_open_settings:
            self.settings_btn.clicked.connect(self.on_open_settings)
        header.addWidget(self.settings_btn)

        card_layout.addLayout(header)

        # ── User query line ──
        self.query_label = QLabel("Hold Ctrl+Option to talk", self.card)
        self.query_label.setWordWrap(True)
        self.query_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-style: italic; border: none;")
        card_layout.addWidget(self.query_label)

        # ── Scrollable Answer Area ──
        self.scroll = QScrollArea(self.card)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
            }
        """)

        self.answer_label = QLabel("Ask anything about your screen — I'll point and explain step-by-step.", self.scroll)
        self.answer_label.setWordWrap(True)
        self.answer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.answer_label.setStyleSheet("color: #F8FAFC; font-size: 13px; line-height: 1.4; border: none;")

        self.scroll.setWidget(self.answer_label)
        card_layout.addWidget(self.scroll, 1)

        # ── Text Input Line for Typing ──
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self.input_field = QLineEdit(self.card)
        self.input_field.setPlaceholderText("Type a question or agent task (Enter)...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(15, 23, 42, 0.7);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
                background-color: rgba(15, 23, 42, 0.95);
            }
        """)
        self.input_field.returnPressed.connect(self._on_enter_pressed)
        input_layout.addWidget(self.input_field, 1)

        send_btn = QPushButton("↑", self.card)
        send_btn.setFixedSize(28, 28)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: 800;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        send_btn.clicked.connect(self._on_enter_pressed)
        input_layout.addWidget(send_btn)

        card_layout.addLayout(input_layout)

        # ── Footer: Model info ──
        short_name = cfg.mlx_model.split("/")[-1].replace("-Instruct", "").replace("-4bit", " 4-bit")
        self.footer_label = QLabel(f"Apple MLX: {short_name}", self.card)
        self.footer_label.setStyleSheet("color: #64748B; font-size: 10px; border: none;")
        card_layout.addWidget(self.footer_label)

        root_layout.addWidget(self.card)

    def _on_enter_pressed(self):
        text = self.input_field.text().strip()
        if text and hasattr(self, "on_submit_text") and self.on_submit_text:
            self.input_field.clear()
            self.on_submit_text(text)

    def set_status(self, text: str, state: str = "normal"):
        self.status_pill.setText(text)
        color_map = {
            "listening": ("rgba(34, 197, 94, 0.2)", "#4ADE80", "rgba(34, 197, 94, 0.4)"),
            "thinking": ("rgba(59, 130, 246, 0.2)", "#60A5FA", "rgba(59, 130, 246, 0.4)"),
            "speaking": ("rgba(168, 85, 247, 0.2)", "#C084FC", "rgba(168, 85, 247, 0.4)"),
            "agent": ("rgba(245, 158, 11, 0.2)", "#FBBF24", "rgba(245, 158, 11, 0.4)"),
            "normal": ("rgba(100, 116, 139, 0.2)", "#94A3B8", "rgba(100, 116, 139, 0.3)"),
        }
        bg, fg, border = color_map.get(state, color_map["normal"])
        self.status_pill.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)

    def set_user_query(self, query: str):
        self.query_label.setText(f'"{query}"' if query else "")

    def set_answer(self, answer: str):
        self.answer_label.setText(answer)
        # Scroll to bottom on new text
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def update_model_badge(self, provider_name: str, model_name: str):
        self.footer_label.setText(f"Provider: {provider_name.title()} ({model_name})")

    def update_mode_badge(self, is_agent: bool):
        self.mode_btn.setText("Agent" if is_agent else "Talk")
        if is_agent:
            self.mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(245, 158, 11, 0.3);
                    color: #FBBF24;
                    border: 1px solid #F59E0B;
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)
        else:
            self.mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.1);
                    color: #E2E8F0;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)

    # ── Drag Window Support ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
