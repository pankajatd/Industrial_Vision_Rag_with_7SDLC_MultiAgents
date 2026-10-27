# Task Queue & Low-Level Technical Specifications
## Project: Autonomous Industrial AI Defect Inspection, Optical Self-Healing & RAG Maintenance Platform (`Industrial_Vision_Rag_7SDLC_Agents`)
**Author:** Tech Lead Subagent (Phase 3)  
**Status:** DRAFT FOR HITL GATE 3 REVIEW  
**Input References:** `plans/PRD.md`, `plans/architecture-spec.md`  

---

## 1. Project File Layout & File Ownership Boundaries

To ensure clean, isolated development without file collisions or merge conflicts, the codebase strictly follows the identical 3-file modular layout proven across all previous master projects:

```
Industrial_Vision_Rag_7SDLC Agents/
├── requirements.txt            <-- Package manifest (Task 1: Software Engineer)
├── packages.txt                <-- Linux system libraries for OpenCV/GL (Task 1: Software Engineer)
├── plans/                      <-- Project specifications & architecture
│   ├── PRD.md                  <-- Product Requirements Document (Phase 1: Product Manager)
│   ├── architecture-spec.md    <-- System Architecture Specification (Phase 2: Technical Architect)
│   ├── task-queue.md           <-- Engineering Task Queue (Phase 3: Tech Lead)
│   └── detailed-design.md      <-- Low-Level Design Document (Phase 3: Tech Lead)
├── src/
│   ├── __init__.py
│   ├── utils.py                <-- Media validation, grain cancellation & HUD painter (Task 2: Software Engineer)
│   ├── detector.py             <-- Optical self-healing, 21-D features, ML & RAG engine (Task 3: Software Engineer)
│   ├── app.py                  <-- Streamlit interactive operator cockpit HUD (Task 4: Software Engineer)
│   └── data/
│       └── manuals/            <-- Plant SOP markdown manuals SOP-000 to SOP-004 (Task 2: Software Engineer)
│           ├── SOP-000-GENERAL.md
│           ├── SOP-001-CRACK.md
│           ├── SOP-002-CORROSION.md
│           ├── SOP-003-DIMENSIONAL.md
│           └── SOP-004-SCRATCH.md
├── tests/
│   ├── __init__.py
│   ├── conftest.py             <-- Root path resolution helper (Task 5: QA Engineer)
│   ├── test_utils.py           <-- Unit tests for frame processing & visual overlays (Task 5: QA Engineer)
│   └── test_detector.py        <-- Integration tests for perception, ML & RAG (Task 5: QA Engineer)
├── reports/
│   ├── qa-test-report.md       <-- QA test execution report (Task 5: QA Engineer)
│   └── security-audit.md       <-- Defensive vulnerability & SAST report (Task 6: Security Auditor)
├── Dockerfile                  <-- Production container definition (Task 7: DevOps Engineer)
├── docker-compose.yml          <-- Local container orchestration (Task 7: DevOps Engineer)
└── README.md                   <-- Complete user manual & execution guide (Task 7: DevOps Engineer)
```

---

## 2. Low-Level Function Contracts & Interfaces

The Software Engineer must implement these exact function contracts:

### 2.1 Utility, Image Preprocessing & Painter HUD Engine (`src/utils.py`)
```python
def validate_media_input(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    """Validates that uploaded bytes form a readable, non-corrupt image (.jpg, .png) or video (.mp4)."""

def load_and_validate_image(input_data) -> np.ndarray:
    """Normalizes bytes, PIL images, or numpy arrays into 3-channel RGB uint8 format (512x512)."""

def segment_grain_neutral(frame_bgr: np.ndarray, threshold_offset: int = 0) -> np.ndarray:
    """
    Cancels horizontal brushed metal grain by subtracting row-wise mean intensity:
    grain_neutral = clip(|gray - row_means|, 0, 255).
    Applies binary thresholding (28 + offset) and morphological open (2x2) and close (3x3).
    Returns: binary mask np.ndarray (uint8, 0 or 255).
    """

def draw_defect_overlay(
    raw_frame: np.ndarray,
    mask: np.ndarray,
    defect_type: str,
    severity_score: float
) -> np.ndarray:
    """
    Renders visual HUD overlays onto the frame:
    - Superimposes isolated defect pixels with Crimson Red: RGB(239, 68, 68).
    - Renders status badges: PASS (Emerald Green), SCRATCH (Sky Blue), CORROSION (Amber), CRACK (Red), DIMENSIONAL (Violet).
    """

def format_telemetry_csv(records: list[dict]) -> str:
    """Serializes per-frame telemetry dictionaries into clean RFC 4180 CSV text for 1-click download."""
```

### 2.2 Core Perception, Self-Healing, ML & RAG Engine (`src/detector.py`)
```python
class IndustrialDefectDetector:
    """Encapsulates optical self-healing, 21-D feature extraction, Random Forest classification, and RAG work order synthesis."""

    def __init__(self, manuals_dir: Optional[str] = None):
        """Initializes thresholds, caches Random Forest model, and indexes plant SOP manuals."""

    def assess_optical_quality(self, frame: np.ndarray) -> dict:
        """Computes Laplacian variance (blur), mean brightness (exposure), and contrast std."""

    def recalibrate_frame(self, frame: np.ndarray, detected_issues: list) -> tuple[np.ndarray, str]:
        """Applies targeted optical recovery: unsharp masking for blur, CLAHE for contrast, gamma curves for glare/darkness."""

    def extract_features_21d(self, preprocessed_bgr: np.ndarray, mask: np.ndarray) -> dict[str, float]:
        """
        Extracts 21-dimensional descriptor vector:
        - 8 Contour Geometry: count, total_area, mean_area, max_area, aspect_ratio, extent, solidity, eccentricity.
        - 3 Intensity Stats: mean, std, range.
        - 7 Hu Moments: hu_1 through hu_7.
        - 3 GLCM Texture: contrast, dissimilarity, homogeneity.
        """

    def predict_and_score(self, features: dict[str, float]) -> tuple[str, float, float, str]:
        """
        Executes Random Forest classification and dynamic severity scoring.
        Returns: (defect_type, confidence, severity_score, severity_level).
        """

    def generate_work_order(self, frame_index: int, defect_type: str, severity_score: float, severity_level: str) -> dict:
        """
        Searches plant SOP manuals using TF-IDF cosine similarity (cutoff >= 0.20) and synthesizes OSHA work order:
        - work_order_id: WO-M0107-CRACK
        - mandatory OSHA Lockout/Tagout (LOTO 29 CFR 1910.147) directives
        - required Level 3 PPE
        - step-by-step repair SOP checklist
        - cited source manual
        """

    def process_frame(self, frame: np.ndarray, threshold_offset: int = 0) -> dict:
        """
        Executes end-to-end perception pipeline on a single frame.
        Returns: strongly typed telemetry dictionary matching Phase 2 architecture spec.
        """
```

---

## 3. Atomic Task Queue for Developers (Tasks 1 through 7)

### Task 1: Environment & Dependency Configuration
* **Assigned Role**: Software Engineer (Phase 4)
* **Target Files**: `requirements.txt`, `packages.txt`
* **Deliverable**:
  - Pinned Python packages: `opencv-python-headless>=4.8.0`, `numpy>=1.24.0`, `scikit-image>=0.21.0`, `scikit-learn>=1.3.0`, `joblib>=1.3.0`, `pandas>=2.0.0`, `Pillow>=10.0.0`, `streamlit>=1.28.0`, `pytest>=7.4.0`.
  - Debian packages in `packages.txt` for headless Docker and Streamlit Cloud: `libgl1`, `libglib2.0-0`.
* **Definition of Done**: Clean installation in fresh virtual environment without dependency conflicts.

---

### Task 2: Utility, Preprocessing & Painter HUD Module
* **Assigned Role**: Software Engineer (Phase 4)
* **Target Files**: `src/utils.py`, `src/data/manuals/` (`SOP-000` through `SOP-004`)
* **Deliverable**:
  - Media validation for image formats (`.jpg`, `.png`) and video streams (`.mp4`).
  - Image normalization into standard 512×512 RGB uint8 arrays.
  - Grain-neutral surface segmentation using row-wise mean intensity subtraction.
  - HUD overlay renderer: superimposes crimson defect pixels and color-coded status badges.
  - CSV telemetry serialization function.
  - Plant SOP markdown manuals (`SOP-000-GENERAL.md`, `SOP-001-CRACK.md`, `SOP-002-CORROSION.md`, `SOP-003-DIMENSIONAL.md`, `SOP-004-SCRATCH.md`).
* **Definition of Done**: Module passes syntax validation and successfully isolates flaws on test metal frames.

---

### Task 3: Core Perception, Self-Healing, ML & RAG Engine (The Detective)
* **Assigned Role**: Software Engineer (Phase 4)
* **Target File**: `src/detector.py`
* **Deliverable**:
  - `IndustrialDefectDetector` class with model loading and optical quality checks (Laplacian variance, brightness, contrast).
  - Autonomous self-healing recovery: unsharp masking for blur, CLAHE for contrast, gamma curve LUT for glare/darkness.
  - 21-dimensional descriptor extraction (Contour geometry, intensity stats, Hu moments, GLCM texture).
  - Random Forest 5-class classifier and dynamic 0–10 severity rating calculation.
  - TF-IDF vector store search over plant SOP manuals and automated OSHA 29 CFR 1910.147 Lockout/Tagout work order synthesis (`WO-M<frame>-<DEFECT>`).
* **Definition of Done**: Class executes `process_frame()` on test frames in sub-80ms and returns structured diagnostic dictionary.

---

### Task 4: Interactive Web Dashboard & Operator Cockpit HUD
* **Assigned Role**: Software Engineer (Phase 4)
* **Target File**: `src/app.py`
* **Deliverable**:
  - Clean wide-screen UI with custom CSS industrial dark-slate styling.
  - Dual-viewport canvas: Raw Conveyor Camera Feed (Left) vs. High-Contrast Red Flaw Mask (Right).
  - Real-time KPI summary cards: Part Quality Status, Defect Severity Score, AI Confidence, Camera Health.
  - Sidebar source selector: "Preset Factory Demos" vs. "Live Inspection Camera Feed".
  - Interactive parameter sliders: Defect Detection Sensitivity, Surface Contrast Boost, and Camera Sharpness Alarm.
  - Expandable OSHA Maintenance Work Order card showing Lockout/Tagout directives and SOP steps.
  - 1-click RFC 4180 CSV telemetry log export button.
* **Definition of Done**: Running `streamlit run src/app.py` launches a responsive dashboard in browser without runtime errors.

---

### Task 5: Automated QA Test Suite & Test Images
* **Assigned Role**: QA / Test Engineer (Phase 5)
* **Target Files**: `tests/conftest.py`, `tests/test_utils.py`, `tests/test_detector.py`, `reports/qa-test-report.md`
* **Deliverable**:
  - Unit tests in `tests/test_utils.py` (validation, grain-neutral segmentation, overlay rendering, CSV format).
  - Integration tests in `tests/test_detector.py` (optical quality checks, self-healing unsharp masking, 21-D features, Random Forest predictions across all 5 classes, RAG work order generation).
  - Minimum 25+ automated test cases.
  - Issue formal QA test execution report (`reports/qa-test-report.md`).
* **Definition of Done**: Running `pytest -v tests/` in terminal passes 100% of tests with strict code freeze on `src/`.

---

### Task 6: Defensive Security & Vulnerability Audit
* **Assigned Role**: Security Auditor (Phase 6)
* **Target File**: `reports/security-audit.md`
* **Deliverable**:
  - Static code security analysis (SAST) on all `src/*.py` files.
  - Verification of image upload memory bounds and decompression bomb protections (`Image.MAX_IMAGE_PIXELS = 50,000,000`).
  - Formula injection protection on CSV telemetry exports (`=`, `@`, `+`, `-`).
  - Memory leak check on frame processing.
  - Issue formal security audit report with `SAFE TO COMMIT` certification.
* **Definition of Done**: Complete audit published to `reports/security-audit.md` with zero critical vulnerabilities.

---

### Task 7: DevOps Packaging & Deployment
* **Assigned Role**: DevOps Engineer (Phase 7)
* **Target Files**: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.gitignore`, `README.md`
* **Deliverable**:
  - Lightweight CPU-optimized container (`python:3.10-slim`).
  - Docker Compose service definition with automated health checks on port 8501.
  - Complete user manual (`README.md`).
  - Detailed Design Document (`plans/detailed-design.md`, `.docx`, `.pdf`).
  - Customer Handover Guide and Docker Testing Manual (`.docx`, `.pdf`).
* **Definition of Done**: Container builds and launches with `docker compose up --build -d` and passes health check.

---

## 4. Execution Order & Dependencies

```
[ Task 1: requirements.txt & packages.txt ]
                      │
                      ▼
            [ Task 2: src/utils.py & src/data/manuals/ ]
                      │
                      ▼
           [ Task 3: src/detector.py ]
                      │
                      ▼
             [ Task 4: src/app.py ]
                      │
                      ▼
           [ Task 5: tests/ (QA Suite) ]
                      │
                      ▼
     [ Task 6: reports/security-audit.md ]
                      │
                      ▼
   [ Task 7: Dockerfile, compose, README.md ]
```
