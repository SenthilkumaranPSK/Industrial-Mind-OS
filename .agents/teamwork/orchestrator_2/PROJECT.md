# Master Plan & Architecture: Enterprise Automated RCA & 8D Studio
**Project Name**: Automated Root Cause Analysis & 8D Studio Integration  
**Owner**: Orchestrator (orchestrator_2, Gen 2)  
**Status**: COMPLETED  
**Last Updated**: 2026-10-08T04:32:00Z  

---

## 1. Architecture Overview
- **Backend Architecture**: FastAPI-based modular design under `backend/api/` and `backend/services/`.
  - Pydantic v2 schemas: `backend/api/rca_schemas.py`
  - Ingestion & Timeline Extractor: `backend/services/rca_ingestion.py`
  - Deductive RCA & Preventative Engine: `backend/services/rca_engine.py`
  - Certified Compliance Package Generator: `backend/services/compliance_package.py`
  - RCA REST Router: `backend/api/rca_router.py` mounted at `/api/v1` in `backend/main.py`
- **Frontend Architecture**: React 18 + Vite + Tailwind CSS + Lucide Icons in `frontend/src/components/EightDStudio/`.
  - Master container: `EightDIncidentStudio.jsx` (Header, 4 tabs, print dossier, modal/embedded modes)
  - Tabs: `OverviewTab.jsx`, `FiveWhyFishboneTab.jsx`, `TimelineTab.jsx`, `CorrectiveActionsTab.jsx`
  - Print Styles: `printStyles.css` (ISO 9001:2015 Clause 10.2 & IATF 16949 Section 10.2.3 compliant)
  - Integration: `ArtifactPanel.jsx` (auto-detection), `Sidebar.jsx` (launcher), `App.jsx` (modal launcher & citation routing to `SourceViewerModal`)

---

## 2. Feature Inventory
| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| F1 | Evidence Citation Object Schema | Pydantic v2 model verifying source doc, section, excerpt, and confidence score | M1 | DONE |
| F2 | Chronological Incident Timeline Schema | Timeline events model with UTC timestamps, event types, equipment tag, and parameters | M1 | DONE |
| F3 | Automated Timeline Extractor | Ingestion engine parsing operator logs, alarms, telemetry excursions into chronological sequence | M1 | DONE |
| F4 | 5-Why Causal Tree Generator | Deductive 5-level why chain linking causes to evidence citations with root cause identification | M2 | DONE |
| F5 | Ishikawa 6M Fishbone Classifier | 6M classification (Man, Machine, Material, Method, Measurement, Environment) | M2 | DONE |
| F6 | Unsubstantiated Assumption Flagger | Automatic flagging of ungrounded causal hypotheses lacking verifiable citations | M2 | DONE |
| F7 | Historical Near-Miss Similarity Matcher | Cosine similarity vector search matching historical incident database records | M2 | DONE |
| F8 | OEM Envelope Deviation Engine | Telemetry boundary checking computing % excursion, severity, and threshold limits | M2 | DONE |
| F9 | Multi-Asset Preventive Action Matrix | Automated generation of D3 containment, D5 PCA, and D7 preventative controls with horizontal read-across | M2 | DONE |
| F10 | Certified Compliance Audit Package Generator | Standalone certified HTML and JSON export with canonical SHA-256 seal and print CSS | M3 | DONE |
| F11 | RCA REST API Router | FastAPI router at `/api/v1/rca/*` (/analyze, /historical-match, /export-evidence, /reports) | M3 | DONE |
| F12 | 8D Studio Container & Navigation | Master 4-tab studio container with incident header, RPN gauge, and SHA-256 seal | M4 | DONE |
| F13 | Overview Tab (D1, D2, D8) | Multi-disciplinary team, 5W2H problem statement, AIAG-VDA risk meter, and sign-off | M4 | DONE |
| F14 | Interactive SVG 5-Why & Fishbone Visualizers | SVG 5-Why tree with #root-glow aura and Ishikawa 6M fishbone with split layout mode | M4 | DONE |
| F15 | Interactive Timeline Rail | Chronological event rail with T+ offsets, 3-zone telemetry gauge, and citations | M4 | DONE |
| F16 | Corrective Actions Tab | D3 vs D5 vs D7 matrices, OEM deviation bars, and historical near-miss cards | M4 | DONE |
| F17 | ISO 9001 / IATF 16949 Print Dossier | Compliant print stylesheet and embedded complete D1-D8 print dossier | M4 | DONE |

---

## 3. Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend Schemas & Timeline Ingestion | Pydantic v2 schemas (`rca_schemas.py`), evidence citation registry, and timeline extractor (`rca_ingestion.py`) | none | DONE |
| M2 | Deductive RCA & Preventative Engine | 5-Why generator, Ishikawa 6M classifier, historical matcher, OEM envelope engine (`rca_engine.py`) | M1 | DONE |
| M3 | RCA API Endpoints & Audit Package Backend | FastAPI router (`rca_router.py`), route mounting in `main.py`, SHA-256 compliance package export generator | M1, M2 | DONE |
| M4 | Frontend 8D Studio & Interactive Visualizers | Interactive 8D Studio components (`EightDStudio/*`), integration in `ArtifactPanel.jsx` & `Sidebar.jsx`, print CSS | M3 | DONE |
| M5 | Final Milestone: 100% E2E Pass & Hardening | Phase 1: 100% E2E test suite pass across all tiers. Phase 2: Tier 5 adversarial stress testing and verification | M1-M4, E2E Test Track | DONE |
