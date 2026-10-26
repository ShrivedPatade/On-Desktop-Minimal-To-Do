# config.py
import math
import struct
import sys
import tkinter as tk
import zlib
from pathlib import Path

# --- Build-Safe Path Resolution ---
if getattr(sys, "frozen", False):
    # Running as compiled PyInstaller .exe
    APP_DIR = Path(sys.executable).parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    # Running in normal Python development environment
    APP_DIR = Path(__file__).parent
    BUNDLE_DIR = APP_DIR

DB_PATH = APP_DIR / "data" / "tasks.db"
LOGO_PATH = BUNDLE_DIR / "assets" / "Minimal-To-Do-Logo.ico"

# --- Color Palette (Light Minimal Theme) ---
PALETTE = {
    "chroma_key": "#010102",     # Transparent corner mask color
    "bg_main": "#E5E5E5",        # Light Gray - Main window background
    "bg_surface": "#D4D6DC",     # Slightly darker gray - Header & dividers
    "bg_input": "#F2F2F4",       # Lighter than bg_main - Rounded input field
    "border_faint": "#C8CAD0",   # Faint thin 1px border for input pill & '+' ring
    "btn_plus_bg": "#E9EAEF",    # Almost transparent fill for round '+' button
    "btn_plus_hover": "#DCDFE6", # Subtle hover fill for '+' button
    "accent": "#14213D",         # Deep Navy - Active pins, checkmarks, focus border
    "text_primary": "#000000",   # Pure Black - Primary task text
    "text_muted": "#6E7382",     # Muted Slate - Completed tasks & placeholder
    "danger": "#C94A4A",         # Muted Crimson - Delete button hover state
}

# --- Window Metrics ---
WINDOW_WIDTH = 340
WINDOW_HEIGHT = 500
WINDOW_ALPHA = 0.85  # Increased transparency to blend into desktop background
WINDOW_RADIUS = 20
INPUT_RADIUS = 18

# --- Typography ---
FONT_FAMILY = "Segoe UI"
FONT_HEADER = (FONT_FAMILY, 9, "bold")
FONT_INPUT = (FONT_FAMILY, 10)
FONT_TASK = (FONT_FAMILY, 10, "normal")
FONT_TASK_DONE = (FONT_FAMILY, 10, "overstrike")
FONT_ICON = (FONT_FAMILY, 10, "bold")


def draw_rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    corners: tuple = (True, True, True, True),
    **kwargs,
) -> int:
    """Draws a geometric rounded rectangle on a Tkinter Canvas."""
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = []
    steps = 12

    corner_specs = [
        (x1 + r, y1 + r, 180, corners[0], x1, y1),
        (x2 - r, y1 + r, 270, corners[1], x2, y1),
        (x2 - r, y2 - r, 0,   corners[2], x2, y2),
        (x1 + r, y2 - r, 90,  corners[3], x1, y2),
    ]

    for cx, cy, start_deg, is_round, sx, sy in corner_specs:
        if is_round and r > 0:
            for i in range(steps + 1):
                angle = math.radians(start_deg + (90 * i / steps))
                points.extend([cx + r * math.cos(angle), cy + r * math.sin(angle)])
        else:
            points.extend([sx, sy])

    return canvas.create_polygon(points, smooth=False, **kwargs)


def ensure_logo_ico() -> Path:
    """
    Ensures assets/logo.ico exists. If you drop your own custom 'assets/logo.ico'
    in the project, this function leaves it untouched. Otherwise, it generates a
    clean, minimal #14213D navy rounded icon with a #E5E5E5 checkmark.
    """
    target = APP_DIR / "assets" / "Minimal-To-Do-Logo.ico"
    if LOGO_PATH.exists():
        return LOGO_PATH
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    size = 64
    rows = []

    # Define checkmark line segments for a 64x64 grid
    for y in range(size):
        row = bytearray([0])  # PNG filter byte
        for x in range(size):
            # Rounded square mask (radius 14)
            dx = max(0, 14 - x, x - (size - 15))
            dy = max(0, 14 - y, y - (size - 15))
            dist = math.hypot(dx, dy)

            if dist > 14.5:
                row.extend((0, 0, 0, 0))  # Transparent outside corner
            else:
                # Checkmark geometry: short leg (18,33)->(27,42), long leg (27,42)->(46,21)
                on_check = False
                if 18 <= x <= 27 and abs((y - 33) - (x - 18)) <= 3.2:
                    on_check = True
                elif 27 <= x <= 46 and abs((y - 42) + (x - 27) * (21 / 19)) <= 3.2:
                    on_check = True

                if on_check:
                    row.extend((229, 229, 229, 255))  # #E5E5E5 Light Checkmark
                else:
                    row.extend((20, 33, 61, 255))     # #14213D Deep Navy Background
        rows.append(bytes(row))

    raw_data = b"".join(rows)

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw_data, 9))
        + png_chunk(b"IEND", b"")
    )

    # Wrap PNG payload in standard Windows ICO container
    ico_header = struct.pack("<HHH", 0, 1, 1)
    ico_dir_entry = struct.pack(
        "<BBBBHHII", size, size, 0, 0, 1, 32, len(png_bytes), 22
    )
    target.write_bytes(ico_header + ico_dir_entry + png_bytes)
    return target