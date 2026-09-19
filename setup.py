"""
setup.py for Clicky macOS Application Bundle.
Alternative packaging setup using py2app.
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Clicky",
        "CFBundleDisplayName": "Clicky",
        "CFBundleIdentifier": "com.clicky.mac",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "14.0",
        "LSUIElement": False,
        "NSHighResolutionCapable": True,
        "NSAccessibilityUsageDescription": (
            "Clicky requires Accessibility access to guide your cursor, "
            "inspect active application windows, and automate workflows."
        ),
        "NSScreenCaptureUsageDescription": (
            "Clicky requires Screen Recording access to analyze UI elements "
            "and provide contextual visual assistance."
        ),
        "NSMicrophoneUsageDescription": (
            "Clicky requires Microphone access for push-to-talk voice commands."
        ),
    },
    "packages": [
        "PyQt6",
        "mlx",
        "mlx_vlm",
        "pynput",
        "sounddevice",
        "agent",
        "ai",
        "audio",
        "screen",
        "ui",
    ],
}

setup(
    name="Clicky",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
