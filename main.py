"""
Clicky for macOS — Main Application Entry Point.
Native cursor companion, tutor guidance, and autonomous Agent Mode.
"""

from __future__ import annotations

import os
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from companion_manager import CompanionManager


def check_macos_permissions():
    """Prints guidance for necessary macOS system permissions."""
    print("=" * 60)
    print("🔵 Clicky for macOS Initializing...")
    print("=" * 60)
    print("Permissions check on macOS:")
    print("1. Accessibility: Required for global Control+Option hotkey.")
    print("   If prompted, enable in System Settings -> Privacy & Security -> Accessibility.")
    print("2. Screen Recording: Required for screen awareness & visual pointing.")
    print("   If prompted, enable in System Settings -> Privacy & Security -> Screen Recording.")
    print("3. Microphone: Required for push-to-talk voice interaction.")
    print("   If prompted, enable in System Settings -> Privacy & Security -> Microphone.")
    print("=" * 60)


def main():
    check_macos_permissions()

    # Create Qt Application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in menu bar

    # Initialize Clicky Companion
    manager = CompanionManager()
    manager.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
