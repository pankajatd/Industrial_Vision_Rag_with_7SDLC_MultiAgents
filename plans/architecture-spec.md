# Technical Architecture Specification
## Project: Autonomous Industrial AI Defect Inspection, Optical Self-Healing & RAG Maintenance Platform (`Industrial_Vision_Rag_7SDLC_Agents`)

**Author:** Technical Architect Subagent  
**Status:** DRAFT FOR HITL GATE 2 REVIEW  
**Scope:** High-Level System Design & Technology Stack Selection  
**Project Path:** `C:\Pankaja\AUTOMATED_SDLC_AGENT_PROJECTS\Industrial_Vision_Rag_7SDLC Agents`  

---

## 1. System Overview & Architectural Approach

To satisfy the business and functional requirements defined in `plans/PRD.md`, the platform is architected as a **modular, multi-tier industrial vision, machine learning, and knowledge retrieval application** divided into two primary high-level tiers:

```
+--------------------------------------------------------------------------+
|                       PRESENTATION LAYER (Web UI)                        |
|   - Real-time conveyor stream and single-frame step inspection           |
|   - Interactive defect preset simulator (Normal, Scratch, Crack, etc.)   |
|   - Sensitivity, surface contrast, and camera sharpness tuning sliders   |
|   - Real-time cockpit KPI metric cards (Status, Severity, Confidence)    |
|   - Expandable OSHA Lockout/Tagout (LOTO) maintenance work order box     |
|   - Side-by-side inspection canvas (Raw Surface vs. Red Flaw Mask)       |
|   - 1-click RFC 4180 CSV telemetry log export                            |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|            AI VISION, SELF-HEALING & RAG INFERENCE ENGINE                |
|   - Stage 1: Optical Quality Assessment & Blur/Lighting Check            |
|   - Stage 2: Autonomous Optical Self-Healing (Unsharp Mask, CLAHE, Gamma)|
|   - Stage 3: Grain-Neutral Surface Segmentation (Row-wise Cancellation)  |
|   - Stage 4: 21-D Feature Extraction (Geometry, Moments, GLCM Texture)   |
|   - Stage 5: 5-Class Defect Classification & Dynamic Severity Scoring    |
|   - Stage 6: Semantic Vector RAG Retrieval over Plant SOP Manuals        |
|   - Stage 7: OSHA 29 CFR 1910.147 Maintenance Work Order Synthesis      |
|   - Stage 8: Annotation & Visual Mask Compositing Engine                 |
+--------------------------------------------------------------------------+
```

---

## 2. Technology Stack Selection & Rationale

| System Layer | Selected Technology | Architectural Rationale |
| :--- | :--- | :--- |
| **Core Runtime** | **Python 3.10+ / 3.11** | Industry standard for machine learning, computer vision, and multi-agent systems. |
| **Computer Vision Engine** | **OpenCV (Headless)** | Ultra-fast, CPU-optimized image decoding, color conversion, geometric matrix operations, and morphological filtering without requiring GPU hardware. |
| **Feature & Texture Engine** | **Scikit-Image (`skimage`)** | Robust Gray-Level Co-occurrence Matrix (GLCM) texture descriptors (contrast, dissimilarity, homogeneity) and ellipse fitting for defect analysis. |
| **Machine Learning Classifier** | **Scikit-Learn (Random Forest)** | Lightweight, highly accurate 100-tree ensemble classifier providing sub-10ms CPU inference across 21-D feature vectors with calibrated probability outputs. |
| **Knowledge Retrieval & Vector Search** | **TF-IDF Vector Store & Cosine Similarity** | Ultra-lightweight, zero-latency semantic search over plant SOP markdown manuals without external API costs or cloud dependencies. |
| **Multi-Agent Orchestration** | **LangGraph / StateGraph** | Manages deterministic state transitions across vision, diagnostics, self-healing, and maintenance RAG pipelines. |
| **Web UI Framework** | **Streamlit** | Enables clean, reactive dashboard interfaces with built-in camera viewports, parameter sliders, telemetry KPI cards, and file download handlers. |
| **Automated Test Runner** | **Pytest** | Standard enterprise test runner for verifying optical self-healing, feature extraction, ML classification, and RAG work order generation. |
| **Containerization** | **Docker & Docker Compose** | Ensures turnkey, 1-command deployment across factory edge workstations and cloud environments with automated healthchecks. |

---

## 3. High-Level System Components & Boundaries

### Component A: Web Presentation Layer
* **Responsibility**: Manages all operator interactions, telemetry displays, parameter sliders, and report downloads.
* **Boundaries**: Strictly handles media viewing, preset selection, slider parameter adjustments, status badge rendering, and CSV exports. **Contains no AI detection algorithms, tensor operations, or model training logic.**

### Component B: Optical Quality & Autonomous Self-Healing Engine
* **Responsibility**: Continuously monitors incoming optical frames for lens blur (Laplacian variance $< 45.0$), poor contrast, and extreme illumination (glare/underexposure).
* **Boundaries**: Closed-loop optical recovery engine. Autonomously applies digital high-boost unsharp masking, CLAHE, or non-linear gamma curves to restore corrupted frames in memory before inspection.

### Component C: Grain-Neutral Perception & ML Engine (The Detective)
* **Responsibility**: Ingests restored metal surface frames, cancels horizontal brushed metal grain via row-wise mean subtraction, extracts a 21-dimensional descriptor vector, predicts defect classes (`normal`, `scratch`, `crack`, `corrosion`, `dimensional`), and computes a 0.0 to 10.0 severity score.
* **Boundaries**: Pure analytical and mathematical engine. Operates completely independently of the web framework so it can be tested, benchmarked, or upgraded in isolation.

### Component D: Knowledge Retrieval & Maintenance RAG Engine
* **Responsibility**: Indexes plant Standard Operating Procedure (SOP) markdown manuals (`src/data/manuals/`), matches diagnosed defects against repair protocols using cosine similarity ($\ge 0.20$), and synthesizes structured work orders (`WO-M<frame>-<DEFECT>`).
* **Boundaries**: Pure document and safety reasoning engine. Consumes defect alerts and outputs formal OSHA Lockout/Tagout (LOTO 29 CFR 1910.147) directives, PPE requirements, and step-by-step repair guides.

### Component E: Annotation & Visualization Engine (The Painter)
* **Responsibility**: Combines detection results with the original camera frame.
* **Boundaries**: Applies high-contrast crimson overlays on isolated flaw pixels, generates dynamic color-coded severity badges (**Green for Pass**, **Blue for Scratch**, **Orange for Corrosion**, **Red for Crack**, **Purple for Dimensional**), and formats telemetry records for CSV export.

---

## 4. Non-Functional System Attributes

* **Hardware Efficiency**: Architected to execute the complete perception, classification, and RAG pipeline in **sub-100ms per frame** on standard multi-core CPUs without requiring expensive dedicated GPUs.
* **Modularity (Detective vs. Painter)**: The perception and RAG engines are decoupled from the visualization layer, allowing independent automated testing, headless batch processing, and future model upgrades.
* **Self-Healing Optical Reliability**: Automatically corrects optical degradations (vibrational blur, lighting changes) in memory, ensuring zero conveyor line stoppages.
* **OSHA Workplace Safety Standard**: Every synthesized maintenance work order embeds mandatory OSHA 29 CFR 1910.147 Lockout/Tagout protocols and Level 3 PPE requirements to safeguard plant technicians.
* **Privacy & Security**: All image processing and RAG queries execute strictly in local memory. No factory camera feeds are transmitted across external cloud networks.
* **Clean Architecture & Governance**: The project structure adheres strictly to the `MASTER_SDLC_AGENTS` framework with isolated deliverables (`plans/`, `src/`, `tests/`, `reports/`, `Dockerfile`) ready for enterprise containerized release.
