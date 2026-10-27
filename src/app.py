"""
Interactive Web Application & Industrial Conveyor Telemetry Cockpit
Project: Autonomous Industrial AI Defect Inspection, Optical Self-Healing & RAG Maintenance Platform
Module: src/app.py
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2
import numpy as np
import streamlit as st
from PIL import Image

# Ensure project root and src directory are in sys.path
_file_dir = Path(__file__).resolve().parent
_root_dir = _file_dir.parent
for _p in [str(_root_dir), str(_file_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from src.detector import IndustrialDefectDetector
    from src.utils import (
        validate_media_input,
        load_and_validate_image,
        generate_synthetic_frame,
        format_telemetry_csv
    )
except (ModuleNotFoundError, ImportError):
    from detector import IndustrialDefectDetector
    from utils import (
        validate_media_input,
        load_and_validate_image,
        generate_synthetic_frame,
        format_telemetry_csv
    )

# =============================================================================
# Streamlit Application Configuration & Custom Industrial Cockpit Styling
# =============================================================================
st.set_page_config(
    page_title="Industrial AI Inspector | Vision & RAG Cockpit",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Industrial Dark-Slate CSS Styling (Universal Light & Dark Mode Support)
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 14px 16px !important;
        margin-bottom: 12px !important;
        color: #f8fafc !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15) !important;
    }
    .metric-title {
        color: #94a3b8 !important;
        font-size: 0.80rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 4px !important;
    }
    .metric-value {
        color: #f8fafc !important;
        font-size: 1.45rem !important;
        font-weight: 700 !important;
    }
    .badge-pass {
        background-color: #065f46 !important;
        color: #34d399 !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
    }
    .badge-warn {
        background-color: #854d0e !important;
        color: #fde047 !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
    }
    .badge-crit {
        background-color: #7f1d1d !important;
        color: #fca5a5 !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
    }
    .viewport-header {
        background-color: #1e293b;
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 6px 6px 0 0;
        padding: 8px 14px;
        font-size: 0.92rem;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_detector() -> IndustrialDefectDetector:
    """Initializes and caches the IndustrialDefectDetector instance."""
    return IndustrialDefectDetector()


# Initialize session state for telemetry logging
if "telemetry_records" not in st.session_state:
    st.session_state.telemetry_records = []
if "frame_counter" not in st.session_state:
    st.session_state.frame_counter = 101


def main():
    detector = get_detector()

    # Top Header & SDLC Attribution Badge
    st.markdown("### 🏭 Industrial AI Quality Inspector & Autonomous Maintenance RAG Platform")
    st.caption("🚀 Engineered under the **MASTER_SDLC_AGENTS** 7-Phase Multi-Agent Framework with 100% HITL Quality Gates")

    # =========================================================================
    # Sidebar: Inspection Controls & Plain-English Parameter Sliders
    # =========================================================================
    st.sidebar.header("⚙️ Conveyor Inspection Controls")

    input_mode = st.sidebar.radio(
        "Source Input Mode",
        options=["Preset Factory Conveyor Demos", "Upload Metal Component Photo"],
        index=0
    )

    optical_glitch = "None (Healthy Optics)"
    defect_preset = "Crack"

    if input_mode == "Preset Factory Conveyor Demos":
        defect_preset = st.sidebar.selectbox(
            "Select Defect Scenario",
            options=["Normal (Flawless)", "Scratch (Cosmetic)", "Corrosion (Oxidation)", "Crack (Structural)", "Dimensional (Edge Notch)"],
            index=3
        )
        optical_glitch = st.sidebar.selectbox(
            "Simulate Camera Lens Degradation",
            options=["None (Healthy Optics)", "Blurry Lens (Vibration / Out of Focus)", "Overexposed Glare (Lighting Washout)", "Underexposed Dark (Dim Light)"],
            index=0
        )
        uploaded_file = None
    else:
        uploaded_file = st.sidebar.file_uploader(
            "Upload Metal Part Image",
            type=["jpg", "jpeg", "png", "bmp", "webp"]
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ Algorithm Tuning Controls")

    threshold_offset = st.sidebar.slider(
        "Defect Detection Sensitivity",
        min_value=-10,
        max_value=10,
        value=0,
        help="[Lower = Catch major flaws only | Higher = Catch hairline micro-scratches]"
    )

    clahe_boost = st.sidebar.slider(
        "Surface Contrast Boost",
        min_value=1.0,
        max_value=6.0,
        value=3.0,
        step=0.5,
        help="[Standard: 3.0 | Low Light: 4.5 | High Glare: 1.5]"
    )

    sharpness_alarm = st.sidebar.slider(
        "Camera Sharpness Variance Alarm",
        min_value=30.0,
        max_value=70.0,
        value=45.0,
        step=5.0,
        help="[Laplacian variance threshold: below this triggers autonomous self-healing sharpening]"
    )

    # Ingestion & Frame Processing Logic
    current_frame = None
    raw_label = "normal"

    if input_mode == "Preset Factory Conveyor Demos":
        mapping = {
            "Normal (Flawless)": "normal",
            "Scratch (Cosmetic)": "scratch",
            "Corrosion (Oxidation)": "corrosion",
            "Crack (Structural)": "crack",
            "Dimensional (Edge Notch)": "dimensional"
        }
        target_defect = mapping.get(defect_preset, "crack")
        st.session_state.frame_counter += 1
        current_frame, raw_label = generate_synthetic_frame(target_defect, seed=st.session_state.frame_counter)

        # Apply optical degradation if requested
        if optical_glitch == "Blurry Lens (Vibration / Out of Focus)":
            current_frame = cv2.GaussianBlur(current_frame, (17, 17), 0)
        elif optical_glitch == "Overexposed Glare (Lighting Washout)":
            current_frame = cv2.convertScaleAbs(current_frame, alpha=1.4, beta=70)
        elif optical_glitch == "Underexposed Dark (Dim Light)":
            current_frame = cv2.convertScaleAbs(current_frame, alpha=0.3, beta=0)

    elif uploaded_file is not None:
        file_bytes = uploaded_file.read()
        is_valid, msg = validate_media_input(file_bytes, uploaded_file.name)
        if not is_valid:
            st.error(f"Upload Error: {msg}")
            return
        st.session_state.frame_counter += 1
        current_frame = load_and_validate_image(file_bytes)

    if current_frame is None:
        st.info("👈 Please select a preset scenario or upload a metal component image from the sidebar.")
        return

    # Execute Detective Perception Pipeline
    with st.spinner("Analyzing metal component..."):
        result = detector.process_frame(
            frame_rgb=current_frame,
            frame_index=st.session_state.frame_counter,
            threshold_offset=threshold_offset
        )

    # Record telemetry for CSV export
    telemetry_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "frame_index": result["frame_index"],
        "defect_type": result["defect_type"],
        "severity_score": result["severity_score"],
        "severity_level": result["severity_level"],
        "confidence": round(result["confidence"] * 100, 1),
        "contour_count": result["features_21d"].get("contour_count", 0),
        "total_area": round(result["features_21d"].get("total_area", 0), 1),
        "optical_health": "ACCEPTABLE" if result["optical_health"]["is_acceptable"] else "SELF-HEALED"
    }
    st.session_state.telemetry_records.append(telemetry_entry)

    # =========================================================================
    # Executive KPI Metric Cards (Plain English)
    # =========================================================================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card"><div class="metric-title">Part Quality Status</div>', unsafe_allow_html=True)
        d_type = result["defect_type"].upper()
        if d_type == "NORMAL":
            st.markdown(f'<div class="metric-value"><span class="badge-pass">✅ {d_type} (PASS)</span></div>', unsafe_allow_html=True)
        elif d_type in ("SCRATCH", "CORROSION"):
            st.markdown(f'<div class="metric-value"><span class="badge-warn">⚠️ {d_type} (WARN)</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="metric-value"><span class="badge-crit">🚨 {d_type} (CRIT)</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card"><div class="metric-title">Defect Severity Score</div>', unsafe_allow_html=True)
        score = result["severity_score"]
        color = "#34d399" if score == 0.0 else "#fde047" if score < 7.5 else "#fca5a5"
        st.markdown(f'<div class="metric-value" style="color: {color};">{score:.1f} <span style="font-size: 0.85rem; color: #94a3b8; font-weight: 400;">/ 10.0 ({result["severity_level"]})</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card"><div class="metric-title">AI Detection Certainty</div>', unsafe_allow_html=True)
        conf_pct = round(result["confidence"] * 100, 1)
        st.markdown(f'<div class="metric-value">{conf_pct}% <span style="font-size: 0.85rem; color: #38bdf8; font-weight: 400;">({result["latency_ms"]} ms)</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card"><div class="metric-title">Camera Optical Health</div>', unsafe_allow_html=True)
        is_clean = result["optical_health"]["is_acceptable"]
        if is_clean:
            st.markdown('<div class="metric-value" style="color: #34d399;">HEALTHY <span style="font-size: 0.8rem; color: #94a3b8; font-weight: 400;">(Sharp)</span></div>', unsafe_allow_html=True)
        else:
            issues = ", ".join(result["optical_health"]["detected_issues"]).upper()
            st.markdown(f'<div class="metric-value" style="color: #38bdf8;">RESTORED <span style="font-size: 0.75rem; color: #fde047; font-weight: 400;">({issues})</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if not result["optical_health"]["is_acceptable"]:
        st.info(f"🛠️ **Autonomous Self-Healing Active:** Camera degradation detected. Applied: **{result['self_healing_action']}**.")

    # =========================================================================
    # Dual-Viewport Inspection Screen (Pixel-Perfect Horizontal Alignment)
    # =========================================================================
    view_col1, view_col2 = st.columns(2)

    with view_col1:
        st.markdown('<div class="viewport-header">📷 Raw Sensor Input (Live Conveyor View)</div>', unsafe_allow_html=True)
        st.image(current_frame, caption=f"Conveyor Frame #{result['frame_index']} (512x512 RGB)", use_container_width=True)

    with view_col2:
        st.markdown('<div class="viewport-header">🔬 AI Defect Mask (Flaw Overlay & HUD)</div>', unsafe_allow_html=True)
        st.image(result["annotated_frame"], caption=f"Flaw Mask & Telemetry HUD Overlay (512x512 RGB)", use_container_width=True)

    # =========================================================================
    # Automated OSHA Maintenance Work Order Console (RAG Engine)
    # =========================================================================
    wo = result.get("work_order", {})
    if wo and result["severity_score"] > 0.0:
        with st.expander(f"📋 Automated Maintenance Work Order ({wo.get('work_order_id')})", expanded=True):
            st.markdown(f"**Target Defect:** `{wo.get('defect_type').upper()}` | **Severity Rating:** `{wo.get('severity_level')}` | **Technician Sign-Off Required:** `{wo.get('technician_signoff_required')}`")

            st.markdown("##### ⚠️ Mandatory OSHA Safety Directives")
            for directive in wo.get("safety_directives", []):
                st.markdown(f"- 🔴 **{directive}**")

            st.markdown("##### 🛠️ Step-by-Step Remediation Procedure (SOP)")
            for i, step in enumerate(wo.get("repair_procedure", []), 1):
                st.markdown(f"{i}. {step}")

            st.caption(f"📚 **Authoritative Manuals Cited:** {', '.join(wo.get('source_manuals', []))}")
    else:
        st.success("✅ **Quality Gate Approved:** No structural or cosmetic defects detected. Part cleared for packaging.")

    # =========================================================================
    # 1-Click CSV Telemetry Download & Inspection History
    # =========================================================================
    st.markdown("---")
    hist_col1, hist_col2 = st.columns([3, 1])

    with hist_col1:
        st.markdown(f"**Session Telemetry Log ({len(st.session_state.telemetry_records)} inspected frames recorded)**")

    with hist_col2:
        csv_data = format_telemetry_csv(st.session_state.telemetry_records)
        st.download_button(
            label="📥 Download Telemetry Log (CSV)",
            data=csv_data,
            file_name="industrial_conveyor_telemetry.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
