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
    """Checks and reports live macOS permissions for Accessibility, Screen Recording, and Mic."""
    print("=" * 60)
    print("🔵 Clicky for macOS (Apple MLX Edition)")
    try:
        from Foundation import NSBundle
        bundle = NSBundle.mainBundle()
        bid = bundle.bundleIdentifier() or "Raw Python binary"
        bundle_path = bundle.bundlePath()
        if bundle_path.endswith(".app"):
            print(f"📦 App Bundle:        {bundle_path}")
            print(f"🆔 TCC Identity:      {bid} (Scoped to Clicky)")
        else:
            print(f"🆔 TCC Identity:      {bid}")
    except Exception:
        pass
    print("-" * 60)

    # 1. Accessibility (quiet check without forcing Terminal prompt)
    try:
        import ApplicationServices
        trusted = ApplicationServices.AXIsProcessTrustedWithOptions({
            ApplicationServices.kAXTrustedCheckOptionPrompt: False
        })
        status_acc = "✓ GRANTED" if trusted else "⚠️ Optional (for global hotkey Ctrl+Option): Enable Clicky in System Settings -> Accessibility"
    except Exception as e:
        status_acc = f"Unknown ({e})"
    print(f"1. Accessibility:     {status_acc}")

    # 2. Screen Recording
    try:
        import Quartz
        screen_ok = Quartz.CGPreflightScreenCaptureAccess()
        status_scr = "✓ GRANTED" if screen_ok else "⚠️ ACTION REQUIRED: Enable Clicky in System Settings -> Privacy -> Screen Recording"
    except Exception as e:
        status_scr = f"Unknown ({e})"
    print(f"2. Screen Recording:  {status_scr}")

    # 3. Microphone
    try:
        import sounddevice as sd
        dev = sd.query_devices(kind="input")
        status_mic = f"✓ READY ({dev.get('name', 'Default Mic')})"
    except Exception as e:
        status_mic = f"⚠️ Check audio input ({e})"
    print(f"3. Microphone:        {status_mic}")
    print("=" * 60)


def main():
    check_macos_permissions()

    if "--check-permissions" in sys.argv or "--test-startup" in sys.argv:
        print("✓ Clicky startup check completed.")
        return

    # Configure macOS AppKit activation policy
    try:
        from AppKit import NSApp, NSApplicationActivationPolicyRegular
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        NSApp.activateIgnoringOtherApps_(True)
    except Exception:
        pass

    # Create Qt Application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Initialize Clicky Companion
    manager = CompanionManager()
    manager.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
