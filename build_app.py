#!/usr/bin/env python3
"""
Clicky for macOS — App Bundle Builder.
Compiles and packages Clicky into a native macOS Application bundle (Clicky.app)
with its own TCC identity (com.clicky.mac) and code signature.
"""

import math
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
DIST_DIR = REPO_DIR / "dist"
APP_DIR = DIST_DIR / "Clicky.app"
CONTENTS_DIR = APP_DIR / "Contents"
MACOS_DIR = CONTENTS_DIR / "MacOS"
RESOURCES_DIR = CONTENTS_DIR / "Resources"
ICONSET_DIR = DIST_DIR / "Clicky.iconset"
ICNS_FILE = RESOURCES_DIR / "Clicky.icns"


def generate_icon():
    """Generates a high-resolution macOS application icon (.icns) for Clicky."""
    print("🎨 Generating Clicky application icon...")
    from PIL import Image, ImageDraw

    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. macOS Squircle Background (Continuous curvature rounded rect)
    margin = 80
    corner_radius = 200
    rect = [margin, margin, size - margin, size - margin]

    # Draw gradient background
    # Deep slate navy (#0B0F19) to dark indigo (#1E1B4B)
    for i in range(margin, size - margin):
        ratio = (i - margin) / (size - 2 * margin)
        r = int(11 * (1 - ratio) + 30 * ratio)
        g = int(15 * (1 - ratio) + 27 * ratio)
        b = int(25 * (1 - ratio) + 75 * ratio)
        # Sliced rounded rectangle mask for smooth gradient
        draw.line([(margin, i), (size - margin, i)], fill=(r, g, b, 255))

    # Mask to squircle
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(rect, radius=corner_radius, fill=255)

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base.paste(img, (0, 0), mask)
    draw = ImageDraw.Draw(base)

    # 2. Glowing outer accent border
    draw.rounded_rectangle(rect, radius=corner_radius, outline=(56, 189, 248, 160), width=10)

    # 3. Stylized AI Robot Companion Face & Cursor
    center_x = size // 2
    center_y = size // 2

    # Robot Head Visor Frame
    visor_w = 480
    visor_h = 280
    visor_box = [
        center_x - visor_w // 2,
        center_y - visor_h // 2 - 20,
        center_x + visor_w // 2,
        center_y + visor_h // 2 - 20
    ]
    draw.rounded_rectangle(visor_box, radius=80, fill=(15, 23, 42, 240), outline=(56, 189, 248, 220), width=12)

    # Glowing Cyan Eyes (Companion expression)
    eye_radius_x = 42
    eye_radius_y = 56
    eye_y = center_y - 20
    left_eye_x = center_x - 120
    right_eye_x = center_x + 120

    # Left eye
    draw.ellipse(
        [left_eye_x - eye_radius_x, eye_y - eye_radius_y, left_eye_x + eye_radius_x, eye_y + eye_radius_y],
        fill=(56, 189, 248, 255)
    )
    # Right eye
    draw.ellipse(
        [right_eye_x - eye_radius_x, eye_y - eye_radius_y, right_eye_x + eye_radius_x, eye_y + eye_radius_y],
        fill=(56, 189, 248, 255)
    )

    # Companion Smile Line
    smile_box = [center_x - 70, center_y + 10, center_x + 70, center_y + 60]
    draw.arc(smile_box, start=20, end=160, fill=(56, 189, 248, 240), width=10)

    # Sleek Navigation Cursor Pointer overlapping bottom-right of visor
    cursor_points = [
        (center_x + 80, center_y + 90),
        (center_x + 240, center_y + 250),
        (center_x + 160, center_y + 260),
        (center_x + 190, center_y + 340),
        (center_x + 130, center_y + 360),
        (center_x + 100, center_y + 280),
        (center_x + 40, center_y + 300)
    ]
    draw.polygon(cursor_points, fill=(14, 165, 233, 255), outline=(240, 249, 255, 255))

    # Pulsing Live Vision Indicator (Emerald Green dot top right of visor)
    dot_x = center_x + visor_w // 2 - 40
    dot_y = center_y - visor_h // 2 + 30
    draw.ellipse([dot_x - 18, dot_y - 18, dot_x + 18, dot_y + 18], fill=(52, 211, 153, 255), outline=(255, 255, 255, 200), width=4)

    # Export to .iconset
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)
    icon_specs = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]

    for filename, px in icon_specs:
        resized = base.resize((px, px), Image.Resampling.LANCZOS)
        resized.save(ICONSET_DIR / filename, "PNG")

    # Run iconutil to create .icns
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_FILE)],
        check=True
    )
    shutil.rmtree(ICONSET_DIR, ignore_errors=True)
    print(f"✓ Icon created: {ICNS_FILE}")


def write_info_plist():
    """Generates the Info.plist with scoped TCC permissions."""
    print("📝 Writing Info.plist...")
    plist_data = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": "Clicky",
        "CFBundleExecutable": "Clicky",
        "CFBundleIconFile": "Clicky",
        "CFBundleIdentifier": "com.clicky.mac",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "Clicky",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "14.0",
        "LSUIElement": False,
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
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
    }

    plist_path = CONTENTS_DIR / "Info.plist"
    with open(plist_path, "wb") as f:
        plistlib.dump(plist_data, f)
    print(f"✓ Info.plist written to {plist_path}")

    # PkgInfo
    pkginfo_path = CONTENTS_DIR / "PkgInfo"
    with open(pkginfo_path, "wb") as f:
        f.write(b"APPL????")


def compile_launcher():
    """Compiles launcher.c into Clicky.app/Contents/MacOS/Clicky."""
    print("🔨 Compiling native Mach-O launcher with clang...")
    python3_bin = REPO_DIR / ".venv" / "bin" / "python3"
    if not python3_bin.exists():
        python3_bin = Path(sys.executable)

    # Obtain python3-config flags
    config_bin = "/opt/homebrew/opt/python@3.14/bin/python3.14-config"
    if not os.path.exists(config_bin):
        config_bin = "python3-config"

    cflags = subprocess.check_output([config_bin, "--cflags"]).decode().strip().split()
    ldflags = subprocess.check_output([config_bin, "--ldflags", "--embed"]).decode().strip().split()

    target_bin = MACOS_DIR / "Clicky"
    MACOS_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "clang",
        "-Wall",
        "-Wextra",
        "-O2",
        str(REPO_DIR / "launcher.c"),
        "-o", str(target_bin)
    ] + cflags + ldflags

    subprocess.run(cmd, check=True)
    os.chmod(target_bin, 0o755)
    print(f"✓ Native launcher compiled: {target_bin}")


def write_project_metadata():
    """Records the project path for the launcher."""
    path_txt = RESOURCES_DIR / "project_path.txt"
    with open(path_txt, "w") as f:
        f.write(str(REPO_DIR) + "\n")


def sign_bundle():
    """Ad-hoc signs the application bundle with identifier com.clicky.mac."""
    print("🔏 Code-signing Clicky.app...")
    subprocess.run(
        [
            "codesign",
            "--force",
            "--deep",
            "--sign", "-",
            "--identifier", "com.clicky.mac",
            str(APP_DIR)
        ],
        check=True
    )
    print("✓ Successfully signed with identifier 'com.clicky.mac'")


def main():
    print("=" * 60)
    print("🚀 Building Clicky for macOS (.app bundle)")
    print("=" * 60)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    MACOS_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

    write_info_plist()
    generate_icon()
    compile_launcher()
    write_project_metadata()
    sign_bundle()

    print("=" * 60)
    print(f"🎉 Build Complete: {APP_DIR}")
    print("=" * 60)
    print("To launch as Clicky.app with isolated permissions:")
    print(f"  open {APP_DIR}")
    print("Or to stream logs in your terminal:")
    print(f"  {MACOS_DIR}/Clicky")
    print("=" * 60)


if __name__ == "__main__":
    main()
