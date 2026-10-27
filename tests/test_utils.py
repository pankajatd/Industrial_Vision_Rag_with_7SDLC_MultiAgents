"""
Unit Test Suite for Image Processing, Preprocessing & Painter HUD (src/utils.py)
"""

import io
import pytest
import numpy as np
from PIL import Image
from src.utils import (
    validate_media_input,
    load_and_validate_image,
    segment_grain_neutral,
    draw_defect_overlay,
    format_telemetry_csv,
    generate_synthetic_frame
)


class TestMediaValidation:
    """Tests input byte verification, format restrictions, and error handling."""

    def test_validate_empty_bytes(self):
        is_valid, msg = validate_media_input(b"", "test.png")
        assert not is_valid
        assert "empty" in msg.lower()

    def test_validate_unsupported_format(self):
        is_valid, msg = validate_media_input(b"some data", "test.exe")
        assert not is_valid
        assert "unsupported" in msg.lower()

    def test_validate_corrupt_bytes(self):
        is_valid, msg = validate_media_input(b"random-corrupt-data-not-an-image", "test.png")
        assert not is_valid
        assert "corrupted" in msg.lower() or "invalid" in msg.lower()

    def test_validate_valid_png(self):
        img = Image.new("RGB", (64, 64), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        is_valid, msg = validate_media_input(buf.getvalue(), "test.png")
        assert is_valid
        assert "valid" in msg.lower()


class TestImageNormalization:
    """Tests standardizing image inputs to 512x512 RGB arrays."""

    def test_load_and_validate_from_bytes(self):
        img = Image.new("RGB", (256, 256), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        arr = load_and_validate_image(buf.getvalue())
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (512, 512, 3)
        assert arr.dtype == np.uint8

    def test_load_and_validate_from_pil(self):
        img = Image.new("RGB", (128, 128), color="green")
        arr = load_and_validate_image(img)
        assert arr.shape == (512, 512, 3)

    def test_load_and_validate_from_grayscale_array(self):
        gray = np.zeros((100, 100), dtype=np.uint8)
        arr = load_and_validate_image(gray)
        assert arr.shape == (512, 512, 3)


class TestGrainNeutralSegmentation:
    """Tests row-wise mean intensity cancellation on brushed metal."""

    def test_segment_flawless_metal(self):
        frame, _ = generate_synthetic_frame("normal", seed=42)
        mask = segment_grain_neutral(frame)
        assert isinstance(mask, np.ndarray)
        assert mask.shape == (512, 512)
        # Normal part should have minimal or zero flaw pixels
        flaw_ratio = np.sum(mask > 0) / (512 * 512)
        assert flaw_ratio < 0.01

    def test_segment_crack_metal(self):
        frame, _ = generate_synthetic_frame("crack", seed=42)
        mask = segment_grain_neutral(frame)
        assert np.sum(mask > 0) > 100


class TestOverlayAndHud:
    """Tests drawing high-contrast flaw highlights and HUD banners."""

    def test_draw_defect_overlay_output_shape(self):
        frame, _ = generate_synthetic_frame("crack", seed=42)
        mask = segment_grain_neutral(frame)
        hud = draw_defect_overlay(frame, mask, "crack", 8.5)
        assert hud.shape == (512, 512, 3)
        assert hud.dtype == np.uint8

    def test_draw_normal_overlay(self):
        frame, _ = generate_synthetic_frame("normal", seed=42)
        mask = np.zeros((512, 512), dtype=np.uint8)
        hud = draw_defect_overlay(frame, mask, "normal", 0.0)
        assert hud.shape == (512, 512, 3)


class TestTelemetryCSVExport:
    """Tests RFC 4180 CSV serialization and formula injection protection."""

    def test_csv_empty_records(self):
        csv = format_telemetry_csv([])
        assert "timestamp,frame_index,defect_type" in csv

    def test_csv_with_records(self):
        records = [
            {"timestamp": "2026-10-27 12:00:00", "frame_index": 101, "defect_type": "crack", "severity_score": 8.5, "severity_level": "CRITICAL", "confidence": 98.2, "optical_health": "ACCEPTABLE"}
        ]
        csv = format_telemetry_csv(records)
        assert "WO-M" not in csv
        assert "101,crack,8.5,CRITICAL" in csv

    def test_csv_formula_injection_protection(self):
        records = [
            {"timestamp": "2026-10-27", "frame_index": 102, "defect_type": "=cmd|' /C calc'!A0", "severity_score": 1.0}
        ]
        csv = format_telemetry_csv(records)
        # Formula '=' must be prepended with single quote
        assert "'=cmd" in csv
