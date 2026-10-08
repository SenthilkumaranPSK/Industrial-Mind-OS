# Project: Automated Root Cause Analysis (RCA) & 8D Incident Report Studio

## Architecture
The system integrates an enterprise-grade Automated RCA & 8D Incident Report Studio into Industrial Mind OS.
It is composed of two primary tracks operating concurrently:
1. **Implementation Track**:
   - **M1: Backend Schemas, Ingestion & Timeline Extraction Engine** (`backend/api/rca_schemas.py`, `backend/services/rca_ingestion.py`): Accepts failure symptoms, timestamps, equipment tags; extracts chronological telemetry and alarm events; establishes verifiable source citation registry.
   - **M2: Deductive Root Cause Analysis Engine & Preventative Matching** (`backend/services/rca_engine.py`): Multi-stage deductive reasoning executing 5-Why causal trees, Ishikawa 6M classification, explicit assumption flagging (`is_unsubstantiated`), historical near-miss similarity matching (`Near_Miss_Report_2023.txt`), and OEM operating envelope deviation calculations.
   - **M3: RCA API Endpoints & Compliance Audit Packaging** (`backend/api/rca_router.py`, `backend/main.py`): REST endpoints (`/api/v1/rca/analyze`, `/api/v1/rca/historical-match`, `/api/v1/rca/export-evidence`, `/api/v1/rca/reports`), SHA-256 tamper-evident checksums, compliance audit package renderer.
   - **M4: Interactive 8D Incident Studio Frontend** (`frontend/src/components/EightDStudio/*`, `frontend/src/components/ArtifactPanel.jsx`, `frontend/src/components/Sidebar.jsx`): Interactive studio component with 4 tabs (Overview, 5-Why Tree & Fishbone SVG, Timeline rail, Corrective Actions), citation drill-down via `SourceViewerModal`, print-ready compliance audit package export with `@media print`.
   - **M5: Final Milestone - E2E Verification & Adversarial Hardening**: Pass 100% of the E2E test suite (Tiers 1-4) and Tier 5 adversarial coverage hardening.
2. **E2E Testing Track**:
   - Independent test harness and test suites (Tiers 1-4) verifying end-to-end RCA report generation, Pydantic validation, citation grounding, and export integrity without implementation dependencies. Publishes `TEST_READY.md`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | 8D Pydantic Domain Schemas | 18 production-ready schemas (D1-D8, 5W2H, Severity/RPN, Citations, Timeline, 5-Why, Fishbone, Actions) | M1 | ORIGINAL_REQUEST §R1, §AC Backend |
| F2 | Incident Evidence & Citation Registry | Autonomous citation ID generator linking source files, excerpts, and sections with confidence scores | M1 | ORIGINAL_REQUEST §R1 |
| F3 | Chronological Timeline Reconstruction | Autonomous event sequence extractor compiling timestamped telemetry, alarms, and operator logs | M1 | ORIGINAL_REQUEST §R1 |
| F4 | Deductive 5-Why Causal Tree Engine | Recursive why-branching decomposing failure into direct, contributing, and root causes | M2 | ORIGINAL_REQUEST §R2 |
| F5 | Ishikawa 6M Fishbone Classifier | Decomposes causal factors into Man, Machine, Material, Method, Measurement, Environment | M2 | ORIGINAL_REQUEST §R2 |
| F6 | Assumption Flagging & Grounding Verifier | Strict rule engine verifying citations for every causal claim, setting `is_unsubstantiated=True` on ungrounded claims | M2 | ORIGINAL_REQUEST §R2, §AC Backend |
| F7 | Historical Near-Miss Similarity Matching | Cross-references incidents against historical records (e.g. `Near_Miss_Report_2023.txt`) and calculates similarity | M2 | ORIGINAL_REQUEST §R4 |
| F8 | OEM Operating Envelope Deviation Analysis | Compares incident telemetry against OEM thresholds, computing deviation percentages and preventative maintenance updates | M2 | ORIGINAL_REQUEST §R4 |
| F9 | RCA REST API Router | FastAPI router mounting `/analyze`, `/historical-match`, `/export-evidence`, and `/reports` under `/api/v1/rca` | M3 | ORIGINAL_REQUEST §AC Backend |
| F10 | Certified Compliance Audit Package Generator | Timestamped, SHA-256 tamper-evident certified evidence package generator (HTML & JSON) | M3 | ORIGINAL_REQUEST §R3, §AC Backend/Frontend |
| F11 | 8D Studio Navigation & Layout | Tabbed studio component (Overview, 5-Why Tree, Timeline, Corrective Actions) integrated in ArtifactPanel & Sidebar | M4 | ORIGINAL_REQUEST §R3, §AC Frontend |
| F12 | Interactive 5-Why & Fishbone SVG Visualizers | Responsive vector diagrams with clickable nodes, status indicators, and print-ready rendering | M4 | ORIGINAL_REQUEST §R3, §AC Frontend |
| F13 | Interactive Timeline Rail | Chronological event visualization with telemetry callouts and source citation badge drill-downs | M4 | ORIGINAL_REQUEST §R3, §AC Frontend |
| F14 | Citation Drill-Down Modal Integration | Seamless integration with `SourceViewerModal` to inspect exact source document evidence snippets | M4 | ORIGINAL_REQUEST §R3 |
| F15 | Print-Ready Compliance Audit Export | One-click export triggering `@media print` A4 formatting with ISO 9001/IATF 16949 audit headers and signatures | M4 | ORIGINAL_REQUEST §R3, §AC Frontend |
| F16 | E2E Test Suite (Tiers 1-4) | Comprehensive opaque-box test suite verifying 100% of RCA endpoints, schemas, citations, and export | M5 | ORIGINAL_REQUEST §AC Backend |
| F17 | Adversarial Hardening (Tier 5) | Adversarial coverage stress-testing verifying edge cases, malformed payloads, and tamper protection | M5 | Project Pattern Phase 2 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend Schemas & Timeline Ingestion | Pydantic v2 schemas (`rca_schemas.py`), evidence citation registry, and chronological timeline extractor (`rca_ingestion.py`) with unit tests | none | DONE |
| M2 | Deductive RCA & Preventative Engine | 5-Why tree generator, Ishikawa 6M classifier, assumption flagger, historical near-miss matcher, OEM envelope deviation engine (`rca_engine.py`) with unit tests | M1 | IN_PROGRESS |
| M3 | RCA API Endpoints & Audit Package Backend | FastAPI router (`rca_router.py`), route mounting in `main.py`, SHA-256 audit package export generator with unit/integration tests | M1, M2 | PLANNED |
| M4 | Frontend 8D Studio & Interactive Visualizers | Interactive 8D Incident Studio components (`frontend/src/components/EightDStudio/*`), integration in `ArtifactPanel.jsx` & `Sidebar.jsx`, citation modal drill-downs, print CSS | M3 (API contracts) | PLANNED |
| M5 | Final Milestone: 100% E2E Pass & Hardening | Phase 1: 100% E2E test suite pass across all tiers. Phase 2: Tier 5 adversarial stress testing and verification | M1, M2, M3, M4, E2E Test Track | PLANNED |


---

## Interface Contracts

### 1. Ingestion & Schemas Contract (`backend/api/rca_schemas.py`)
- `CitationObject`: `citation_id: str`, `source_doc: str`, `section: Optional[str]`, `excerpt: str`, `confidence: float`
- `TimelineEvent`: `event_id: str`, `timestamp: str`, `event_type: str` (TELEMETRY_ALARM, OPERATOR_ACTION, SYSTEM_FAILURE, MAINTENANCE_LOG), `description: str`, `equipment_tag: str`, `citation_ids: List[str]`, `parameters: Dict[str, Any]`
- `FiveWhyNode`: `why_id: str`, `level: int` (1-5), `cause_statement: str`, `citation_ids: List[str]`, `is_root_cause: bool`, `is_unsubstantiated: bool`
- `FishboneBranch`: `category: str` (Man, Machine, Material, Method, Measurement, Environment), `causes: List[str]`, `citation_ids: List[str]`
- `HistoricalMatch`: `matched_report_id: str`, `title: str`, `similarity_score: float`, `matching_symptoms: List[str]`, `preventative_recommendations: List[str]`
- `OEMDeviation`: `parameter_name: str`, `oem_envelope_limit: float`, `actual_incident_value: float`, `deviation_percent: float`, `unit: str`, `is_exceeded: bool`
- `EightDIncidentReport`:
  - `report_id: str`, `created_at: str`, `asset_tag: str`, `severity_score: int` (1-10), `rpn_score: int` (1-1000)
  - `d1_team`: `TeamFormation` (leader, members, champion)
  - `d2_problem`: `ProblemDescription` (what, where, when, who, why, how, how_many)
  - `d3_containment`: `List[ContainmentAction]` (action, verified_effective, owner)
  - `d4_root_causes`: `RootCauseAnalysis` (five_why_chain, fishbone_analysis, occurrence_root_cause, escape_root_cause)
  - `d5_permanent_actions`: `List[CorrectiveAction]`
  - `d6_validation`: `ValidationPlan` (metrics, validation_date, status)
  - `d7_preventative_controls`: `PreventativeControls` (sop_updates, pm_updates, oem_deviations, historical_matches)
  - `d8_recognition`: `TeamRecognition`
  - `citations`: `List[CitationObject]`
  - `checksum_sha256`: `str`

### 2. API Contract (`backend/api/rca_router.py`)
- `POST /api/v1/rca/analyze`:
  - Input: `RCAAnalyzeRequest` (`asset_tag: str`, `symptoms: List[str]`, `incident_timestamp: str`, `telemetry_data: Optional[Dict]`)
  - Output: `EightDIncidentReport`
- `POST /api/v1/rca/historical-match`:
  - Input: `HistoricalMatchRequest` (`asset_tag: str`, `symptoms: List[str]`, `telemetry_features: Optional[Dict]`)
  - Output: `List[HistoricalMatch]`
- `POST /api/v1/rca/export-evidence`:
  - Input: `ExportEvidenceRequest` (`report_id: str`, `format: str` = "html" | "json")
  - Output: `ExportEvidenceResponse` (`content: str`, `sha256_checksum: str`, `filename: str`)
- `GET /api/v1/rca/reports`:
  - Output: `List[EightDIncidentReportSummary]`

### 3. Frontend Component Contract (`frontend/src/components/EightDStudio/EightDIncidentStudio.jsx`)
- Props: `report: EightDIncidentReport`, `onSourceClick: (source) => void`, `onExportAuditPackage: () => void`, `onClose: () => void`
- Tabs:
  1. `Overview`: 5W2H Problem summary, D1 team, D8 recognition, RPN risk meter, SHA-256 badge.
  2. `5-Why Tree & Fishbone`: Interactive SVG tree showing causal depth, root cause highlight, assumption flags, and Ishikawa 6M diagram.
  3. `Timeline`: Vertical chronological rail with telemetry callouts and citation badges.
  4. `Corrective Actions`: D3 Containment vs D5 Permanent vs D7 Preventative action matrix, OEM envelope deviation bars, and historical match cards.

---

## Code Layout
### Backend Files
- `backend/api/rca_schemas.py` (Owned by M1): Pydantic v2 schemas for all 8D disciplines, citations, timelines, and analysis requests.
- `backend/services/rca_ingestion.py` (Owned by M1): Evidence ingestion, citation extraction, and chronological timeline reconstruction.
- `backend/services/rca_engine.py` (Owned by M2): 5-Why causal reasoning, Ishikawa classification, assumption verifier, historical near-miss matcher, OEM envelope analysis.
- `backend/api/rca_router.py` (Owned by M3): FastAPI endpoints for RCA analysis, matching, and evidence export.
- `backend/main.py` (Owned by M3): Router registration for `/api/v1/rca`.
- `backend/tests/test_rca_schemas.py` (Owned by M1): Unit tests for Pydantic models.
- `backend/tests/test_rca_engine.py` (Owned by M2): Unit tests for 5-Why, Ishikawa, assumption flagging, and historical matching.
- `backend/tests/test_rca_api.py` (Owned by M3): API integration tests using FastAPI TestClient.

### Frontend Files
- `frontend/src/components/EightDStudio/EightDIncidentStudio.jsx` (Owned by M4): Main studio container with 4-tab navigation and audit export header.
- `frontend/src/components/EightDStudio/OverviewTab.jsx` (Owned by M4): D1-D8 overview, 5W2H problem card, RPN risk meter, SHA-256 seal.
- `frontend/src/components/EightDStudio/FiveWhyFishboneTab.jsx` (Owned by M4): SVG 5-Why tree visualizer and Ishikawa 6M diagram.
- `frontend/src/components/EightDStudio/TimelineTab.jsx` (Owned by M4): Chronological event rail with telemetry badges and citation links.
- `frontend/src/components/EightDStudio/CorrectiveActionsTab.jsx` (Owned by M4): Action matrices, OEM envelope deviation charts, historical matches.
- `frontend/src/components/EightDStudio/printStyles.css` (Owned by M4): Print-ready `@media print` styling for ISO 9001/IATF 16949 compliance.
- `frontend/src/components/ArtifactPanel.jsx` (Owned by M4): Hooking 8D artifact rendering into the studio component.
- `frontend/src/components/Sidebar.jsx` (Owned by M4): Direct launch button for 8D Incident Studio.

### E2E Test Files (Owned by E2E Testing Track)
- `tests/e2e_rca/conftest.py`: E2E test runner configuration and fixtures.
- `tests/e2e_rca/test_tier1_feature_coverage.py`: Tier 1 tests (≥5 per feature).
- `tests/e2e_rca/test_tier2_boundary_corner.py`: Tier 2 tests (boundaries, missing citations, extreme values).
- `tests/e2e_rca/test_tier3_cross_feature.py`: Tier 3 pairwise integration tests.
- `tests/e2e_rca/test_tier4_real_world_scenarios.py`: Tier 4 realistic industrial incident scenarios (Pump-A12 ceramic seal failure, turbine overspeed, boiler pressure anomaly).
- `TEST_INFRA.md`: E2E test architecture index.
- `TEST_READY.md`: E2E test suite ready notification with coverage matrix.
