"""
Utility, Image Processing & Painter HUD Module for Industrial Quality Inspection.
Handles image validation, synthetic metal generation, grain-neutral segmentation,
HUD overlays, and RFC 4180 CSV telemetry export.
"""

from __future__ import annotations
import io
import os
import random
from typing import Tuple, List, Dict, Any, Optional

import cv2
import numpy as np
from PIL import Image

# Prevent decompression bomb DoS attacks (Security Guardrail)
Image.MAX_IMAGE_PIXELS = 50_000_000

# Color Constants (BGR format for OpenCV)
COLOR_EMERALD_GREEN = (94, 197, 34)   # PASS
COLOR_SKY_BLUE = (233, 165, 14)       # SCRATCH
COLOR_AMBER_ORANGE = (11, 158, 245)   # CORROSION
COLOR_CRIMSON_RED = (68, 68, 239)     # CRACK
COLOR_VIOLET = (247, 85, 168)         # DIMENSIONAL
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)

DEFECT_COLORS = {
    "normal": COLOR_EMERALD_GREEN,
    "scratch": COLOR_SKY_BLUE,
    "corrosion": COLOR_AMBER_ORANGE,
    "crack": COLOR_CRIMSON_RED,
    "dimensional": COLOR_VIOLET,
}


def validate_media_input(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validates uploaded file bytes against allowed extensions, byte lengths, and header integrity.
    """
    if not file_bytes or len(file_bytes) == 0:
        return False, "Uploaded file is empty (0 bytes)."

    if len(file_bytes) > 50 * 1024 * 1024:
        return False, "File exceeds maximum allowable size (50 MB)."

    ext = os.path.splitext(filename.lower())[1]
    valid_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
    if ext not in valid_extensions:
        return False, f"Unsupported file format '{ext}'. Allowed: {', '.join(valid_extensions)}"

    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img.verify()
        return True, "Valid image file."
    except Exception as e:
        return False, f"Corrupted or invalid image data: {str(e)}"


def load_and_validate_image(input_data: Any, target_size: Tuple[int, int] = (512, 512)) -> np.ndarray:
    """
    Normalizes bytes, PIL Images, or numpy arrays into a standardized 3-channel RGB uint8 array.
    """
    if isinstance(input_data, bytes):
        np_arr = np.frombuffer(input_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Failed to decode image from bytes.")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    elif isinstance(input_data, Image.Image):
        frame = np.array(input_data.convert("RGB"))
    elif isinstance(input_data, np.ndarray):
        frame = input_data.copy()
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
    else:
        raise TypeError(f"Unsupported image input type: {type(input_data)}")

    if frame.shape[:2] != target_size:
        frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)

    return frame.astype(np.uint8)


def segment_grain_neutral(frame_rgb: np.ndarray, threshold_offset: int = 0) -> np.ndarray:
    """
    Cancels brushed metal horizontal texture using row-wise mean intensity subtraction.
    Isolates authentic surface flaws (cracks, scratches, pits, corner chips).
    """
    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

    # 1. Row-wise mean intensity subtraction (cancels horizontal metal grain lines)
    row_means = np.mean(gray, axis=1, keepdims=True)
    grain_neutral = np.clip(np.abs(gray.astype(np.float32) - row_means), 0, 255).astype(np.uint8)

    # 2. Dynamic thresholding
    thresh_val = max(15, 28 + threshold_offset)
    _, binary = cv2.threshold(grain_neutral, thresh_val, 255, cv2.THRESH_BINARY)

    # 3. Morphological open (removes speckles) and close (bridges fissures)
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_close)
    return cleaned


def draw_defect_overlay(
    raw_frame_rgb: np.ndarray,
    mask: np.ndarray,
    defect_type: str = "normal",
    severity_score: float = 0.0
) -> np.ndarray:
    """
    Renders high-contrast visual HUD overlays onto the frame:
    - Overlays isolated defect pixels with bright Crimson Red.
    - Draws colored bounding contours around anomalies.
    - Composites a HUD status banner with color-coded badges.
    """
    canvas = raw_frame_rgb.copy()
    defect_key = defect_type.lower()
    color_bgr = DEFECT_COLORS.get(defect_key, COLOR_EMERALD_GREEN)
    color_rgb = (color_bgr[2], color_bgr[1], color_bgr[0])

    if defect_key != "normal" and mask is not None and np.any(mask > 0):
        # 1. Crimson semi-transparent red overlay on flaw pixels
        flaw_layer = canvas.copy()
        flaw_layer[mask > 0] = [239, 68, 68]
        cv2.addWeighted(flaw_layer, 0.65, canvas, 0.35, 0, canvas)

        # 2. Contour outlines
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 10]
        for c in valid_contours:
            cv2.drawContours(canvas, [c], -1, color_rgb, 2, cv2.LINE_AA)
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(canvas, (x, y), (x + w, y + h), (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Top HUD Banner
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 42), (20, 24, 33), -1)
    status_label = f"[{defect_key.upper()}]  Severity: {severity_score:.1f}/10"
    if defect_key == "normal":
        status_label = "[FLAWLESS PASS]  Ready for Assembly"

    cv2.circle(canvas, (20, 21), 8, color_rgb, -1)
    cv2.putText(canvas, status_label, (36, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

    return canvas


def format_telemetry_csv(records: List[Dict[str, Any]]) -> str:
    """
    Serializes per-frame telemetry dictionaries into RFC 4180 compliant CSV text.
    Implements formula injection protection by prepending a single quote to dangerous characters.
    """
    if not records:
        return "timestamp,frame_index,defect_type,severity_score,severity_level,confidence\n"

    headers = [
        "timestamp", "frame_index", "defect_type", "severity_score",
        "severity_level", "confidence", "contour_count", "total_area", "optical_health"
    ]
    lines = [",".join(headers)]

    for r in records:
        row = []
        for h in headers:
            val = str(r.get(h, ""))
            # Prevent CSV formula injection (=, +, -, @)
            if val and val[0] in ("=", "+", "-", "@"):
                val = f"'{val}"
            # Escape commas and quotes
            if "," in val or '"' in val:
                val = f'"{val.replace(chr(34), chr(34) + chr(34))}"'
            row.append(val)
        lines.append(",".join(row))

    return "\n".join(lines)


# =========================================================================
# Synthetic Industrial Metal Surface & Defect Generator (Zero-Dependency)
# =========================================================================

def generate_base_metal(width: int = 512, height: int = 512, seed: Optional[int] = None) -> np.ndarray:
    """Generates realistic brushed steel surface texture with horizontal grain lines and Gaussian noise."""
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    base_intensity = np.random.randint(165, 195)
    img = np.full((height, width), base_intensity, dtype=np.uint8)

    # Horizontal brushed grain lines
    for _ in range(height * 2):
        y = np.random.randint(0, height)
        thickness = np.random.randint(1, 2)
        shade = np.random.randint(-22, 22)
        line_val = np.clip(base_intensity + shade, 0, 255)
        cv2.line(img, (0, y), (width, y), int(line_val), thickness)

    # Gaussian noise
    noise = np.random.normal(0, 6, (height, width)).astype(np.float32)
    metal = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return cv2.cvtColor(metal, cv2.COLOR_GRAY2RGB)


def inject_scratch(img: np.ndarray) -> np.ndarray:
    """Injects linear or curvilinear surface scratch."""
    out = img.copy()
    h, w = out.shape[:2]
    pt1 = (random.randint(50, w - 50), random.randint(50, h - 50))
    angle = random.uniform(0, 2 * np.pi)
    length = random.randint(80, 220)
    pt2 = (
        int(np.clip(pt1[0] + length * np.cos(angle), 15, w - 15)),
        int(np.clip(pt1[1] + length * np.sin(angle), 15, h - 15))
    )
    thickness = random.randint(1, 3)
    color = (random.randint(50, 90), random.randint(50, 90), random.randint(50, 90))
    cv2.line(out, pt1, pt2, color, thickness, cv2.LINE_AA)
    return out


def inject_crack(img: np.ndarray) -> np.ndarray:
    """Injects branching jagged crack fissure."""
    out = img.copy()
    h, w = out.shape[:2]
    curr_pt = (random.randint(100, w - 100), random.randint(100, h - 100))
    segments = random.randint(7, 14)
    for _ in range(segments):
        next_pt = (
            int(np.clip(curr_pt[0] + random.randint(-28, 28), 15, w - 15)),
            int(np.clip(curr_pt[1] + random.randint(15, 45), 15, h - 15))
        )
        cv2.line(out, curr_pt, next_pt, (25, 25, 25), random.randint(2, 4), cv2.LINE_AA)
        if random.random() < 0.4:
            branch_pt = (
                int(np.clip(curr_pt[0] + random.randint(-35, 35), 15, w - 15)),
                int(np.clip(curr_pt[1] + random.randint(10, 30), 15, h - 15))
            )
            cv2.line(out, curr_pt, branch_pt, (35, 35, 35), 1, cv2.LINE_AA)
        curr_pt = next_pt
    return out


def inject_corrosion(img: np.ndarray) -> np.ndarray:
    """Injects surface oxidation pitting clusters with brownish-orange rust tones."""
    out = img.copy()
    h, w = out.shape[:2]
    cx = random.randint(120, w - 120)
    cy = random.randint(120, h - 120)
    num_spots = random.randint(30, 65)
    for _ in range(num_spots):
        rx = int(np.clip(cx + np.random.normal(0, 32), 15, w - 15))
        ry = int(np.clip(cy + np.random.normal(0, 32), 15, h - 15))
        radius = random.randint(3, 9)
        rust_color = (random.randint(130, 185), random.randint(65, 110), random.randint(20, 50))
        cv2.circle(out, (rx, ry), radius, rust_color, -1)
    return out


def inject_dimensional(img: np.ndarray) -> np.ndarray:
    """Injects corner notch or edge chip flaw."""
    out = img.copy()
    h, w = out.shape[:2]
    flaw_size = random.randint(55, 90)
    corner = random.choice(["top_left", "top_right", "bottom_left", "bottom_right"])

    if corner == "top_left":
        pts = np.array([[0, 0], [flaw_size, 0], [0, flaw_size]], np.int32)
    elif corner == "top_right":
        pts = np.array([[w, 0], [w - flaw_size, 0], [w, flaw_size]], np.int32)
    elif corner == "bottom_left":
        pts = np.array([[0, h], [flaw_size, h], [0, h - flaw_size]], np.int32)
    else:
        pts = np.array([[w, h], [w - flaw_size, h], [w, h - flaw_size]], np.int32)

    cv2.fillPoly(out, [pts], (18, 18, 18))
    return out


def generate_synthetic_frame(defect_type: str = "normal", seed: Optional[int] = None) -> Tuple[np.ndarray, str]:
    """
    Generates a synthetic industrial frame for any of the 5 target classes:
    'normal', 'scratch', 'crack', 'corrosion', 'dimensional'.
    """
    base = generate_base_metal(512, 512, seed=seed)
    defect = defect_type.lower().strip()

    if defect == "scratch":
        frame = inject_scratch(base)
    elif defect == "crack":
        frame = inject_crack(base)
    elif defect == "corrosion":
        frame = inject_corrosion(base)
    elif defect == "dimensional":
        frame = inject_dimensional(base)
    else:
        frame = base
        defect = "normal"

    return frame, defect
