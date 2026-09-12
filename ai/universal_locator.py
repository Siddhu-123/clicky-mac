"""
Universal Two-Stage Grid Locator for macOS.
Works with ANY vision model (Gemini, Ollama, OpenAI, Claude).

Stage 1: Overlays a 12x8 numbered grid on the screenshot; LLM picks the cell.
Stage 2: Crops into that cell and overlays a 6x6 fine grid for sub-cell precision.
Computes the exact target coordinate in macOS logical screen space.
"""

from __future__ import annotations

import base64
import io
import re
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from screen.capture import ScreenShot


def _draw_grid(
    image: Image.Image,
    cols: int,
    rows: int,
    color: tuple = (255, 50, 50, 180),
    font_size: int = 16,
) -> Image.Image:
    """Draws a numbered grid across the image."""
    img = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = img.size
    col_w = w / cols
    row_h = h / rows

    # Vertical lines
    for c in range(1, cols):
        x = int(c * col_w)
        draw.line([(x, 0), (x, h)], fill=color, width=1)

    # Horizontal lines
    for r in range(1, rows):
        y = int(r * row_h)
        draw.line([(0, y), (w, y)], fill=color, width=1)

    # Cell numbers (1-indexed)
    num = 1
    for r in range(rows):
        for c in range(cols):
            x = int(c * col_w + 4)
            y = int(r * row_h + 4)
            # Background box for readability
            draw.rectangle([(x - 2, y - 2), (x + 22, y + 16)], fill=(0, 0, 0, 160))
            draw.text((x, y), str(num), fill=(255, 255, 255, 240))
            num += 1

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    return combined


def image_to_base64_jpeg(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def base64_to_image(b64_str: str) -> Image.Image:
    data = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(data)).convert("RGB")


class UniversalLocator:
    """Provides pixel-accurate coordinate detection using a 2-stage visual grid."""

    COARSE_COLS = 12
    COARSE_ROWS = 8

    FINE_COLS = 6
    FINE_ROWS = 6

    @classmethod
    def generate_coarse_grid(cls, screenshot: ScreenShot) -> ScreenShot:
        """Draws 12x8 grid over screenshot JPEG."""
        base_img = base64_to_image(screenshot.base64_jpeg)
        grid_img = _draw_grid(base_img, cls.COARSE_COLS, cls.COARSE_ROWS)
        b64 = image_to_base64_jpeg(grid_img)

        return ScreenShot(
            index=screenshot.index,
            width=grid_img.width,
            height=grid_img.height,
            base64_jpeg=b64,
            physical_width=screenshot.physical_width,
            physical_height=screenshot.physical_height,
            physical_left=screenshot.physical_left,
            physical_top=screenshot.physical_top,
            dpi_scale=screenshot.dpi_scale,
            logical_left=screenshot.logical_left,
            logical_top=screenshot.logical_top,
            logical_width=screenshot.logical_width,
            logical_height=screenshot.logical_height,
        )

    @classmethod
    def parse_cell_number(cls, response: str, max_cell: int) -> Optional[int]:
        """Extracts the chosen cell number from LLM response."""
        matches = re.findall(r"\b(\d{1,3})\b", response)
        for m in matches:
            val = int(m)
            if 1 <= val <= max_cell:
                return val
        return None

    @classmethod
    def cell_to_logical_point(
        cls,
        cell: int,
        screenshot: ScreenShot,
        cols: int = 12,
        rows: int = 8,
    ) -> Tuple[int, int]:
        """Calculates center point of a cell in logical screen coordinates."""
        idx = cell - 1
        c = idx % cols
        r = idx // cols

        col_w = screenshot.logical_width / cols
        row_h = screenshot.logical_height / rows

        center_x = screenshot.logical_left + int((c + 0.5) * col_w)
        center_y = screenshot.logical_top + int((r + 0.5) * row_h)

        return center_x, center_y
