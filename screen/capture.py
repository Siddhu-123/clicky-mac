"""
Multi-monitor screenshot helper for macOS with Retina (HiDPI) awareness.

Coordinates:
  1. PHYSICAL  — What mss.grab() returns. Real display pixels (e.g. 3024x1964 on 14" MacBook Pro).
  2. LOGICAL   — What macOS / Qt cursor uses in point space (e.g. 1512x982 at 2x Retina scale).
  3. DOWNSCALED — Compressed JPEG sent to LLM vision APIs (e.g. 1280 wide).

The overlay and pointing animations operate in LOGICAL space.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import List, Optional

import mss
import mss.tools
from PIL import Image

try:
    import AppKit
except ImportError:
    AppKit = None


@dataclass
class ScreenShot:
    index: int

    # Downscaled image sent to LLM
    width: int            # width of downscaled JPEG
    height: int           # height of downscaled JPEG
    base64_jpeg: str

    # Real (physical) display dimensions from mss
    physical_width: int
    physical_height: int
    physical_left: int
    physical_top: int

    # Retina DPI scale factor (physical / logical, usually 2.0 on Macs)
    dpi_scale: float

    # Logical origin in macOS/Qt desktop coordinate space
    logical_left: int
    logical_top: int
    logical_width: int
    logical_height: int

    # Native PIL image for zero-copy MLX processing
    pil_image: Optional[Image.Image] = None


def get_macos_dpi_scale() -> float:
    """Returns backing scale factor for main screen on macOS (default 2.0 on Retina)."""
    if AppKit is not None:
        try:
            main_screen = AppKit.NSScreen.mainScreen()
            if main_screen:
                return float(main_screen.backingScaleFactor())
        except Exception as e:
            print(f"[Capture] Error getting backing scale factor: {e}")
    return 2.0  # Safe default for modern Apple Silicon Macs


def capture_all_screens(max_width: int = 1280) -> List[ScreenShot]:
    """
    Captures all active monitors.
    Returns a list of ScreenShot objects containing downscaled base64 JPEGs and coordinate mappings.
    """
    dpi = get_macos_dpi_scale()
    results: List[ScreenShot] = []

    mss_cls = getattr(mss, "MSS", getattr(mss, "mss", None))
    with mss_cls() as sct:
        # sct.monitors[0] is the bounding box of all screens; 1+ are individual displays
        monitors = sct.monitors[1:] if len(sct.monitors) > 1 else sct.monitors

        for i, monitor in enumerate(monitors, start=1):
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

            phys_w, phys_h = img.width, img.height
            phys_left = int(monitor.get("left", 0))
            phys_top = int(monitor.get("top", 0))

            log_w = int(phys_w / dpi)
            log_h = int(phys_h / dpi)
            log_left = int(phys_left / dpi)
            log_top = int(phys_top / dpi)

            # Downscale for LLM token efficiency while keeping aspect ratio
            if img.width > max_width:
                ratio = max_width / img.width
                downscaled_img = img.resize(
                    (max_width, int(img.height * ratio)),
                    Image.Resampling.LANCZOS,
                )
            else:
                downscaled_img = img

            buf = io.BytesIO()
            downscaled_img.save(buf, format="JPEG", quality=80, optimize=True)
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")

            results.append(
                ScreenShot(
                    index=i,
                    width=downscaled_img.width,
                    height=downscaled_img.height,
                    base64_jpeg=encoded,
                    physical_width=phys_w,
                    physical_height=phys_h,
                    physical_left=phys_left,
                    physical_top=phys_top,
                    dpi_scale=dpi,
                    logical_left=log_left,
                    logical_top=log_top,
                    logical_width=log_w,
                    logical_height=log_h,
                    pil_image=downscaled_img,
                )
            )

    return results
