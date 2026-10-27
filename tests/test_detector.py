"""
Integration Test Suite for Core Perception, Self-Healing, ML & RAG Engine (src/detector.py)
"""

import time
import pytest
import cv2
import numpy as np

from src.detector import IndustrialDefectDetector, EXPECTED_FEATURES
from src.utils import generate_synthetic_frame


@pytest.fixture(scope="module")
def detector():
    """Initializes and caches the detector for the test suite."""
    return IndustrialDefectDetector()


class TestOpticalQualityAndSelfHealing:
    """Verifies blur, contrast, and exposure assessment and auto-recovery."""

    def test_sharp_frame_optical_quality(self, detector):
        frame, _ = generate_synthetic_frame("normal", seed=1)
        health = detector.assess_optical_quality(frame)
        assert health["is_acceptable"] is True
        assert health["laplacian_variance"] >= 45.0
        assert len(health["detected_issues"]) == 0

    def test_blurry_frame_detection(self, detector):
        frame, _ = generate_synthetic_frame("normal", seed=2)
        blurry = cv2.GaussianBlur(frame, (17, 17), 0)
        health = detector.assess_optical_quality(blurry)
        assert health["is_acceptable"] is False
        assert "blur" in health["detected_issues"]

    def test_self_healing_sharpening(self, detector):
        frame, _ = generate_synthetic_frame("crack", seed=3)
        blurry = cv2.GaussianBlur(frame, (15, 15), 0)
        res = detector.process_frame(blurry)
        assert "Unsharp Mask" in res["self_healing_action"]
        assert res["annotated_frame"].shape == (512, 512, 3)

    def test_self_healing_exposure_glare(self, detector):
        frame, _ = generate_synthetic_frame("corrosion", seed=4)
        glare = cv2.convertScaleAbs(frame, alpha=1.5, beta=80)
        res = detector.process_frame(glare)
        assert "overexposed" in res["optical_health"]["detected_issues"]
        assert "Gamma Correction" in res["self_healing_action"]


class TestFeatureExtraction21D:
    """Verifies all 21 mathematical features are calculated and sanitized."""

    def test_feature_vector_keys(self, detector):
        frame, _ = generate_synthetic_frame("crack", seed=5)
        mask = np.zeros((512, 512), dtype=np.uint8)
        mask[100:200, 100:200] = 255
        feats = detector.extract_features_21d(frame, mask)
        assert len(feats) == 21
        for k in EXPECTED_FEATURES:
            assert k in feats
            assert not np.isnan(feats[k])
            assert not np.isinf(feats[k])

    def test_bayesian_priors_fallback(self, detector):
        frame, _ = generate_synthetic_frame("normal", seed=6)
        empty_mask = np.zeros((512, 512), dtype=np.uint8)
        feats = detector.extract_features_21d(frame, empty_mask)
        assert feats["total_area"] == 0.0
        assert feats["contour_count"] == 0.0


class TestDefectClassificationAndSeverity:
    """Verifies 5-class Random Forest predictions and severity calculations."""

    @pytest.mark.parametrize("defect_label", ["normal", "scratch", "crack", "corrosion", "dimensional"])
    def test_synthetic_presets_detection(self, detector, defect_label):
        frame, _ = generate_synthetic_frame(defect_label, seed=42)
        res = detector.process_frame(frame)
        assert res["defect_type"] in ["normal", "scratch", "crack", "corrosion", "dimensional"]
        assert 0.0 <= res["confidence"] <= 1.0
        assert 0.0 <= res["severity_score"] <= 10.0
        assert res["severity_level"] in ["PASS", "LOW", "MEDIUM", "CRITICAL"]

    def test_normal_severity_is_zero(self, detector):
        frame, _ = generate_synthetic_frame("normal", seed=7)
        res = detector.process_frame(frame)
        if res["defect_type"] == "normal":
            assert res["severity_score"] == 0.0
            assert res["severity_level"] == "PASS"

    def test_bug004_normal_component_strict_zero_severity(self, detector):
        """Regression test for BUG-004: Normal component with minor speckles must strictly score 0.0."""
        # Simulated normal part with ambient contour noise
        features = {col: 0.0 for col in EXPECTED_FEATURES}
        features["contour_count"] = 2.0
        features["total_area"] = 45.0  # Ambient noise speckles
        _, _, score, level, _ = detector.predict_and_score(features)
        # Force check normal branch behavior
        assert score == 0.0, f"Expected 0.0 for normal but got {score}"
        assert level == "PASS", f"Expected PASS for normal but got {level}"

    def test_bug005_severity_score_strictly_clamped_to_10(self, detector):
        """Regression test for BUG-005: Massive flaw (>30% area) must strictly clamp to 10.0 ceiling."""
        massive_features = {col: 100.0 for col in EXPECTED_FEATURES}
        massive_features["contour_count"] = 5.0
        massive_features["total_area"] = 90000.0  # ~34% of 512x512
        # Mock predicted as dimensional or crack
        detector.model.predict = lambda df: np.array(["dimensional"])
        _, _, score, level, _ = detector.predict_and_score(massive_features, frame_shape=(512, 512))
        assert score <= 10.0, f"Expected score <= 10.0 but got {score}"
        assert score == 10.0, f"Expected clamped score 10.0 but got {score}"
        assert level == "CRITICAL"
        # Reset model
        detector._load_or_train_model()


class TestVectorRAGWorkOrders:
    """Verifies TF-IDF SOP manual semantic retrieval and OSHA work order synthesis."""

    def test_work_order_structure(self, detector):
        wo = detector.generate_work_order(101, "crack", 9.0, "CRITICAL")
        assert wo["work_order_id"] == "WO-M0101-CRACK"
        assert wo["technician_signoff_required"] is True
        assert len(wo["safety_directives"]) >= 3
        # Must contain mandatory OSHA Lockout/Tagout (LOTO 29 CFR 1910.147)
        loto_present = any("1910.147" in d for d in wo["safety_directives"])
        assert loto_present, "OSHA Lockout/Tagout 29 CFR 1910.147 must be cited."
        assert "SOP-001-CRACK.md" in wo["source_manuals"]

    def test_work_order_normal_flawless(self, detector):
        wo = detector.generate_work_order(102, "normal", 0.0, "PASS")
        assert wo["technician_signoff_required"] is False


class TestPerformanceAndLatency:
    """Verifies real-time CPU latency satisfies sub-100ms budget."""

    def test_inference_latency_sub_100ms(self, detector):
        frame, _ = generate_synthetic_frame("crack", seed=8)
        # Warmup
        detector.process_frame(frame)
        latencies = []
        for _ in range(5):
            t0 = time.time()
            res = detector.process_frame(frame)
            latencies.append((time.time() - t0) * 1000)

        avg_latency = np.mean(latencies)
        assert avg_latency < 100.0, f"Average latency {avg_latency:.2f}ms exceeds 100ms threshold."


class TestEdgeCaseRobustness:
    """Verifies resilience against extreme edge-case frames."""

    def test_pure_black_frame(self, detector):
        black = np.zeros((512, 512, 3), dtype=np.uint8)
        res = detector.process_frame(black)
        assert res["annotated_frame"].shape == (512, 512, 3)

    def test_pure_white_frame(self, detector):
        white = np.full((512, 512, 3), 255, dtype=np.uint8)
        res = detector.process_frame(white)
        assert res["annotated_frame"].shape == (512, 512, 3)

    def test_random_uniform_noise(self, detector):
        noise = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        res = detector.process_frame(noise)
        assert res["annotated_frame"].shape == (512, 512, 3)
