"""
macOS Menu Bar Extra (System Tray) for Clicky (Apple MLX Edition).
Provides quick controls, mode toggles, and settings directly from the macOS menu bar.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from config import cfg


def create_tray_icon() -> QIcon:
    """Generates a clean template menu-bar icon (Clicky blue dot with white pointer)."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer blue circle
    painter.setBrush(QColor(37, 99, 235))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)

    # Inner white pointer
    path = QPainterPath()
    path.moveTo(10, 8)
    path.lineTo(22, 16)
    path.lineTo(14, 18)
    path.lineTo(11, 24)
    path.closeSubpath()

    painter.setBrush(QColor(255, 255, 255))
    painter.drawPath(path)
    painter.end()

    return QIcon(pixmap)


class ClickyTrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        on_toggle_panel=None,
        on_toggle_mode=None,
        on_open_settings=None,
        on_test_point=None,
        on_quit=None,
    ):
        super().__init__(create_tray_icon())
        self.setToolTip("Clicky — AI Cursor Companion (Apple MLX)")

        self.on_toggle_panel = on_toggle_panel
        self.on_toggle_mode = on_toggle_mode
        self.on_open_settings = on_open_settings
        self.on_test_point = on_test_point
        self.on_quit = on_quit

        self._build_menu()
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger and self.on_toggle_panel:
            self.on_toggle_panel()

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #2563EB;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 8px;
            }
        """)

        # Status Header
        self.status_action = QAction("Clicky: Ready (Apple MLX)", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        # Mode Toggle (Talk vs Agent)
        self.mode_action = QAction("Mode: Talk (Switch to Agent)", menu)
        if self.on_toggle_mode:
            self.mode_action.triggered.connect(self.on_toggle_mode)
        menu.addAction(self.mode_action)

        # Toggle Panel
        toggle_panel_action = QAction("Toggle HUD Panel", menu)
        if self.on_toggle_panel:
            toggle_panel_action.triggered.connect(self.on_toggle_panel)
        menu.addAction(toggle_panel_action)

        menu.addSeparator()

        # Test Pointing Demo
        if self.on_test_point:
            test_point_action = QAction("🎯 Test Pointing Flight", menu)
            test_point_action.triggered.connect(self.on_test_point)
            menu.addAction(test_point_action)

        # Settings
        settings_action = QAction("Settings...", menu)
        if self.on_open_settings:
            settings_action.triggered.connect(self.on_open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit Clicky", menu)
        if self.on_quit:
            quit_action.triggered.connect(self.on_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def update_mode_label(self, is_agent: bool):
        if is_agent:
            self.mode_action.setText("Mode: Agent Mode (Switch to Talk)")
        else:
            self.mode_action.setText("Mode: Talk Mode (Switch to Agent)")

    def update_status(self, status: str):
        self.status_action.setText(f"Clicky: {status}")
