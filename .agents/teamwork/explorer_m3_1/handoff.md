# Milestone 3 Handoff Report: Router Architecture, Endpoints & State Management

**Author**: `explorer_m3_1`  
**Working Directory**: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m3_1`  
**Target Milestone**: Milestone 3 — RCA API Endpoints & Compliance Audit Packaging (`backend/api/rca_router.py`, `backend/main.py`, `backend/tests/test_rca_api.py`)  
**Parent Orchestrator ID**: `6083de2c-0790-4fdb-80b8-ee776e04b485`  

---

## 1. Observation

Direct observations from examining the codebase, dependencies, schemas, and test suites:

### 1.1 Router Registration in `backend/main.py`
In `backend/main.py` (lines 48–51):
```python
# Include core API routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")
```
- Existing routers are mounted on `app` with `prefix="/api/v1"`.
- `backend/api/auth.py` defines `router = APIRouter(prefix="/auth", tags=["Authentication"])`.
- When mounted in `main.py` under `prefix="/api/v1"`, endpoints resolve to `/api/v1/auth/...`.
- `backend/api/router.py` defines `api_router = APIRouter()`, resolving to `/api/v1/upload`, `/api/v1/query`, etc.
- To maintain this architectural convention for Milestone 3, `backend/api/rca_router.py` must define:
  ```python
  router = APIRouter(prefix="/rca", tags=["Root Cause Analysis (8D)"])
  rca_router = router  # convenience alias
  ```
  and `backend/main.py` will mount it via:
  ```python
  from api.rca_router import rca_router
  app.include_router(rca_router, prefix="/api/v1")
  ```
  yielding routes rooted at `/api/v1/rca/...`.

### 1.2 M1 Pydantic Schemas in `backend/api/rca_schemas.py`
Examined `backend/api/rca_schemas.py` (655 lines):
- Request/Response Models:
  - `RCAAnalyzeRequest` (lines 586–607): `asset_tag: str`, `symptoms: List[str]`, `incident_timestamp: str`, `telemetry_data: Optional[Dict[str, Any]] = None`. Validates ISO timestamp format.
  - `HistoricalMatchRequest` (lines 610–617): `asset_tag: str`, `symptoms: List[str] = Field(..., min_length=1)`, `telemetry_features: Optional[Dict[str, Any]] = None`.
    *Key observation*: `min_length=1` is currently enforced on `symptoms`.
  - `ExportEvidenceRequest` (lines 619–632): `report_id: str`, `format: str = "html"`. Has `@field_validator("format")` raising `ValueError` on unsupported formats.
  - `ExportEvidenceResponse` (lines 634–641): `content: str`, `sha256_checksum: str`, `filename: str`.
  - `EightDIncidentReportSummary` (lines 643–654): `report_id: str`, `created_at: str`, `asset_tag: str`, `severity_score: int`, `rpn_score: int`, `title: str`, `status: str`, `checksum_sha256: str`.
  - `EightDIncidentReport` (lines 480–580): Canonical master schema with disciplines D1–D8, `timeline: List[TimelineEvent]`, `citations: List[CitationObject]`, `checksum_sha256: str`, and method `compute_canonical_sha256() -> str`.

### 1.3 M2 Engine Capabilities in `backend/services/rca_engine.py`
Examined `backend/services/rca_engine.py` (2293 lines):
- `DeductiveRCAEngine` (line 2170) / `RCAEngine` (line 2290):
  - `analyze_incident(request: RCAAnalyzeRequest, near_miss_filepath: Optional[str] = None) -> EightDIncidentReport`: Executes complete pipeline (citation extraction from `Near_Miss_Report_2023.txt`, timeline reconstruction, OEM deviation analysis, historical matching, 4-pillar preventative controls, recursive 5-Why tree, Ishikawa 6M classification, full D1–D8 assembly via `assemble_eight_d_report`, and canonical SHA-256 calculation).
- `assemble_eight_d_report` (line 1663): Synthesizes disciplines D1–D8, auto-calculates RPN, and applies canonical SHA-256 seal.
- `match_historical_records` (line 936) / `HistoricalMatcher.match` (line 844) / `HistoricalNearMissMatcher.match` (line 918): Multi-factor historical matching. Returns `List[ExtendedHistoricalMatch]` (subclass of `HistoricalMatch`). Handles empty symptoms safely by returning `[]`.
  *Key observation*: Function name is `match_historical_records`; creating an alias `match_historical_near_misses = match_historical_records` provides 100% compliance with the dispatch specification.
- `analyze_oem_deviations` (line 487) / `compute_oem_deviation` (line 470).
- `generate_preventative_controls` (line 1520).

### 1.4 E2E Test Suite Contract & Boundary Expectations
Inspected `backend/tests/e2e_rca/conftest.py`, `test_tier1_feature_coverage.py`, and `test_tier2_boundary_corner.py`:
- `test_f9_01_api_analyze_returns_valid_8d_report`: Calls `POST /api/v1/rca/analyze` with valid payload, expects `200`, valid `report_id` starting with `8D-`, disciplines D1/D2/D4, RPN scoring, and non-empty SHA-256 checksum.
- `test_f9_02_api_historical_match_returns_matches`: Calls `POST /api/v1/rca/historical-match`, expects `200` with list containing `NM-2023-PUMP-A12`.
- `test_f9_03_api_export_evidence_json`: Calls `POST /api/v1/rca/export-evidence` with `format="json"`, expects `200`, filename ending in `.json`, 64-char `sha256_checksum`, and valid JSON body containing `"d1_team"`.
- `test_f9_04_api_export_evidence_html`: Calls `POST /api/v1/rca/export-evidence` with `format="html"`, expects `200`, filename ending in `.html`, `<!DOCTYPE html>`, `audit-header`, and 64-char `sha256_checksum`.
- `test_f9_05_api_list_reports_returns_summaries`: Calls `GET /api/v1/rca/reports`, expects `200` and list of summaries with keys `report_id`, `severity_score`, `sha256_checksum`.
- `test_f9_b01_empty_symptoms_payload_returns_422`: `POST /api/v1/rca/analyze` with `symptoms=[]` returns `422`.
- `test_f9_b02_missing_asset_tag_returns_422`: `POST /api/v1/rca/analyze` with missing `asset_tag` returns `422`.
- `test_f9_b03_unsupported_export_format_returns_400`: `POST /api/v1/rca/export-evidence` with `format="xml"` expects `400 Bad Request` (NOT 422!).
- `test_f9_b04_empty_symptoms_historical_match_returns_200_empty`: `POST /api/v1/rca/historical-match` with `symptoms=[]` expects `200 OK` with an empty list `[]` (NOT 422!).
- `test_f9_b05_nonexistent_report_export_handled_gracefully`: `POST /api/v1/rca/export-evidence` with unknown report ID (e.g. `8D-NONEXISTENT`) returns `200 OK` with a valid fallback evidence package.
- `test_cross_08_full_api_workflow_pipeline`: Executes `/analyze` -> `/historical-match` -> `/export-evidence` (HTML & JSON).
- `test_f10_03` & `test_f10_04`: HTML export contains certified audit header `audit-header`, SHA-256 seal `sha-seal`, ISO 9001:2015 text, `@page { size: letter portrait; margin: 15mm 18mm; }`, and `@media print`.
- `test_f10_b03`: HTML export must sanitize inputs (e.g. `<script>alert('xss')</script>`) to prevent XSS.

---

## 2. Logic Chain

From these observations, we derive the structural and behavioral requirements for Milestone 3:

### 2.1 Route Definitions & Mounting
1. Mounting `rca_router` on `app` with `prefix="/api/v1"` requires `rca_router = APIRouter(prefix="/rca", tags=["Root Cause Analysis (8D)"])`.
2. This establishes the exact REST paths:
   - `POST /api/v1/rca/analyze`
   - `POST /api/v1/rca/historical-match`
   - `POST /api/v1/rca/export-evidence`
   - `GET /api/v1/rca/reports`
   - `GET /api/v1/rca/reports/{report_id}`

### 2.2 Status Codes & Validation Logic
1. **POST /api/v1/rca/analyze**:
   - `RCAAnalyzeRequest` has `symptoms: List[str] = Field(..., min_length=1)` and `asset_tag: str`.
   - When `asset_tag` is missing or `symptoms=[]`, Pydantic validation automatically raises `RequestValidationError` -> FastAPI returns **HTTP 422**.
   - On valid payload, engine runs deductive analysis, generates complete `EightDIncidentReport`, stores it in the thread-safe registry, and returns **HTTP 200**.
2. **POST /api/v1/rca/historical-match**:
   - Observation 1.4 noted `test_f9_b04` tests `symptoms=[]` expecting **HTTP 200** with `[]`.
   - In `backend/api/rca_schemas.py`, line 615 currently has `symptoms: List[str] = Field(..., min_length=1)`. If `min_length=1` is kept, `symptoms=[]` will trigger 422, failing `test_f9_b04`.
   - Therefore, `HistoricalMatchRequest` must be updated to `symptoms: List[str] = Field(default_factory=list)` (or `min_length=0`).
   - When `symptoms` is empty or no matches are found, `HistoricalMatcher.match()` returns `[]`, and the endpoint returns **HTTP 200**.
3. **POST /api/v1/rca/export-evidence**:
   - Observation 1.4 noted `test_f9_b03` tests `format="xml"` and explicitly asserts `resp.status_code == 400`.
   - If Pydantic's `field_validator` in `ExportEvidenceRequest` raises `ValueError`, FastAPI defaults to **422**.
   - To guarantee HTTP 400 for invalid formats while returning 422 for malformed schema payloads (e.g. missing `report_id`), `format` in `ExportEvidenceRequest` should accept any string (`format: str = "html"`), and the route handler must check:
     ```python
     if req.format.lower() not in ("html", "json"):
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail=f"Unsupported format '{req.format}': must be 'html' or 'json'",
         )
     ```
   - Observation 1.4 noted `test_f9_b05` tests `report_id="8D-NONEXISTENT"` expecting **HTTP 200** with a valid fallback package.
   - Therefore, if `report_id` is not present in the in-memory store, the store generates a graceful fallback demo report, computes its canonical SHA-256 hash, and renders the requested export, returning **HTTP 200**.
4. **GET /api/v1/rca/reports**:
   - Retrieves all stored reports from the in-memory store.
   - Returns a list of `EightDIncidentReportSummary` objects with **HTTP 200**. If empty, returns `[]` with **HTTP 200**.
5. **GET /api/v1/rca/reports/{report_id}**:
   - Convenience endpoint for fetching a single report.
   - If found in store: returns `EightDIncidentReport` with **HTTP 200**.
   - If not found: raises `HTTPException(status_code=404, detail=f"Report '{report_id}' not found")` returning **HTTP 404**.

### 2.3 In-Memory Thread-Safe Report State Management
1. FastAPI executes synchronous route handlers in a thread pool (`fastapi.concurrency.run_in_threadpool`) and asynchronous handlers on the event loop.
2. Concurrent requests modifying or reading report state concurrently could cause race conditions or dictionary mutation errors.
3. Solution: Implement `RCAReportStore` encapsulating an in-memory dictionary `_reports: Dict[str, EightDIncidentReport]` guarded by a `threading.Lock`.
4. The store provides atomic operations: `get()`, `save()`, `list_all()`, `delete()`, `clear()`, and `get_or_create_fallback()`.
5. Pre-populating or generating demo reports on fallback guarantees both unit tests and ad-hoc exports succeed seamlessly.

### 2.4 Compliance Evidence Package Generation (HTML & JSON)
1. **JSON Export**:
   - Serializes `report.model_dump(mode="json")` formatted with 2-space indentation.
   - Checksum: `report.checksum_sha256` or `report.compute_canonical_sha256()`.
   - Filename: `{report.report_id}_evidence_package.json`.
2. **HTML Export**:
   - Renders a standalone, print-ready HTML document adhering to ISO 9001:2015 Clause 10.2 / IATF 16949 Section 10.2.3.
   - Contains:
     - `@page { size: letter portrait; margin: 15mm 18mm; }` and `@media print` rules.
     - Header: `<div class="audit-header" data-checksum="{sha256_checksum}">`
     - SHA-256 seal: `<p class="sha-seal">Certified SHA-256 Checksum: {sha256_checksum}</p>`
     - Complete D1–D8 discipline cards, RPN risk scoring, timeline table, and documentary citations table.
     - Dynamic text sanitization via `html.escape()` to defeat XSS injection attacks.
   - Filename: `{report.report_id}_compliance_audit.html`.

### 2.5 Dual-Field Schema Compatibility
1. E2E tests check `sha256_checksum` and `incident_title` on summary objects (`test_tier1_feature_coverage.py:845`), while `backend/api/rca_schemas.py` defines `checksum_sha256` and `title`.
2. Similarly, E2E tests check `data["audit_metadata"]["sha256_checksum"]` on report objects (`test_tier1_feature_coverage.py:789`), while M1 schemas define top-level `checksum_sha256`.
3. To ensure 100% interoperability with both M1 unit tests and E2E test suites, models must provide both fields via Pydantic validators or default properties.

---

## 3. Caveats

1. **In-Memory Volatility**: The in-memory report store resides in process memory and resets upon server restart. For persistent production storage beyond Milestone 3, a persistent database backend (e.g. SQLite / PostgreSQL) could be wired in, though the current project specification requires an in-memory thread-safe registry.
2. **Unauthenticated Public Access for RCA Routes**: Existing core endpoints in `backend/api/router.py` require `current_user: dict = Depends(get_current_user)`. The E2E RCA test harness and unit tests execute API calls without authorization tokens. RCA endpoints should remain accessible without mandatory token enforcement, with optional user attribution if provided.
3. **No Caveats on Implementation Boundary**: Investigation was conducted strictly read-only; no source code files in `backend/` were altered.

---

## 4. Conclusion & Proposed Architecture

Milestone 3 requires the creation of `backend/api/rca_router.py`, updating `backend/main.py`, minor schema tweaks in `backend/api/rca_schemas.py`, and implementing integration tests in `backend/tests/test_rca_api.py`.

### 4.1 Detailed Design for `backend/api/rca_router.py`

```python
"""
Industrial Mind OS - Automated Root Cause Analysis (RCA) & 8D Studio Router
Location: backend/api/rca_router.py

Compliant with AIAG 8D, ISO 9001:2015 Clause 10.2, IATF 16949 Section 10.2.3.
Provides REST endpoints:
- POST /api/v1/rca/analyze
- POST /api/v1/rca/historical-match
- POST /api/v1/rca/export-evidence
- GET /api/v1/rca/reports
- GET /api/v1/rca/reports/{report_id}
"""

import html
import json
import logging
import threading
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

from api.rca_schemas import (
    EightDIncidentReport,
    EightDIncidentReportSummary,
    ExportEvidenceRequest,
    ExportEvidenceResponse,
    HistoricalMatch,
    HistoricalMatchRequest,
    RCAAnalyzeRequest,
)
from services.rca_engine import (
    DeductiveRCAEngine,
    assemble_eight_d_report,
    match_historical_records,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rca", tags=["Root Cause Analysis (8D)"])
rca_router = router  # Module alias


# ==============================================================================
# THREAD-SAFE IN-MEMORY REPORT STORE
# ==============================================================================

class RCAReportStore:
    """
    Thread-safe in-memory storage registry for EightDIncidentReport objects.
    Guarantees concurrency safety using an internal threading.Lock.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._reports: Dict[str, EightDIncidentReport] = {}

    def get(self, report_id: str) -> Optional[EightDIncidentReport]:
        with self._lock:
            return self._reports.get(report_id)

    def save(self, report: EightDIncidentReport) -> EightDIncidentReport:
        with self._lock:
            self._reports[report.report_id] = report
            return report

    def list_all(self) -> List[EightDIncidentReport]:
        with self._lock:
            return list(self._reports.values())

    def delete(self, report_id: str) -> bool:
        with self._lock:
            return self._reports.pop(report_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._reports.clear()

    def get_or_create_fallback(self, report_id: str) -> EightDIncidentReport:
        """
        Retrieves existing report or synthesizes a valid fallback report
        to ensure graceful export handling per E2E test specifications.
        """
        with self._lock:
            if report_id in self._reports:
                return self._reports[report_id]

            # Generate compliant fallback report
            clean_tag = "Pump-A12"
            fallback_rep = assemble_eight_d_report(
                asset_tag=clean_tag,
                symptoms=["mechanical seal failure", "high vibration 5.8 mm/s"],
                incident_timestamp="2023-11-04T08:00:00Z",
                telemetry_data={"vibration_mm_s": 5.8},
                report_id=report_id if report_id.startswith("8D-") else f"8D-2023-{report_id}",
            )
            # Ensure custom report_id is honored
            fallback_rep.report_id = report_id
            fallback_rep.compute_canonical_sha256()
            self._reports[report_id] = fallback_rep
            return fallback_rep


# Global singleton store instance
report_store = RCAReportStore()


# ==============================================================================
# AUDIT PACKAGE HTML RENDERER
# ==============================================================================

def render_audit_html(report: EightDIncidentReport) -> str:
    """
    Renders print-ready compliance audit HTML package with certified SHA-256 seal.
    Sanitizes dynamic text via html.escape to prevent XSS injection.
    """
    checksum = report.checksum_sha256 or report.compute_canonical_sha256()
    safe_rep_id = html.escape(report.report_id)
    safe_asset = html.escape(report.asset_tag)
    safe_what = html.escape(report.d2_problem.what)
    safe_where = html.escape(report.d2_problem.where)
    safe_when = html.escape(report.d2_problem.when)
    safe_leader = html.escape(report.d1_team.leader)
    safe_champion = html.escape(report.d1_team.champion)
    safe_occ_cause = html.escape(report.d4_root_causes.occurrence_root_cause)
    safe_esc_cause = html.escape(report.d4_root_causes.escape_root_cause)

    # Containment rows
    containment_rows = "".join(
        f"<tr><td>{html.escape(c.action_id)}</td><td>{html.escape(c.action)}</td>"
        f"<td>{html.escape(c.owner)}</td><td>{c.effectiveness_pct}%</td><td>{html.escape(c.status.value)}</td></tr>"
        for c in report.d3_containment
    )

    # 5-Why rows
    five_why_rows = "".join(
        f"<tr><td>Level {node.level}</td><td>{html.escape(node.cause_statement)}</td>"
        f"<td>{'YES (Root Cause)' if node.is_root_cause else 'No'}</td>"
        f"<td>{'YES (Assumed)' if node.is_unsubstantiated else 'Grounded'}</td></tr>"
        for node in report.d4_root_causes.five_why_chain
    )

    # Corrective action rows
    pca_rows = "".join(
        f"<tr><td>{html.escape(pca.pca_id)}</td><td>{html.escape(pca.action)}</td>"
        f"<td>{html.escape(pca.owner)}</td><td>{html.escape(pca.status.value)}</td></tr>"
        for pca in report.d5_permanent_actions
    )

    # Timeline rows
    timeline_rows = "".join(
        f"<tr><td>{html.escape(evt.timestamp)}</td><td>{html.escape(evt.event_type)}</td>"
        f"<td>{html.escape(evt.description)}</td></tr>"
        for evt in report.timeline
    )

    # Citation rows
    citation_rows = "".join(
        f"<tr><td><code>{html.escape(c.citation_id)}</code></td><td>{html.escape(c.source_doc)}</td>"
        f"<td>{html.escape(c.excerpt)}</td><td>{c.confidence:.2f}</td></tr>"
        for c in report.citations
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>8D Compliance Audit Package - {safe_rep_id}</title>
  <style>
    @page {{ size: letter portrait; margin: 15mm 18mm; }}
    @media print {{
      body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; font-size: 10pt; color: #111; }}
      .no-print {{ display: none; }}
      .page-break {{ page-break-after: always; }}
    }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #1e293b; line-height: 1.5; margin: 20px; }}
    .audit-header {{ border: 2px solid #1e3a8a; background: #f8fafc; padding: 16px; border-radius: 6px; margin-bottom: 24px; }}
    .audit-header h1 {{ margin: 0 0 8px 0; font-size: 16pt; color: #1e3a8a; letter-spacing: 0.5px; }}
    .sha-seal {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 9pt; background: #e2e8f0; padding: 6px 10px; border-radius: 4px; display: inline-block; word-break: break-all; margin: 6px 0; }}
    .meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px; font-size: 9pt; }}
    .section-card {{ border: 1px solid #cbd5e1; border-radius: 6px; padding: 14px; margin-bottom: 18px; }}
    .section-card h2 {{ margin: 0 0 10px 0; font-size: 12pt; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 9pt; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; font-weight: 600; color: #334155; }}
    .badge {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 8pt; font-weight: bold; background: #e2e8f0; }}
    .badge-critical {{ background: #fee2e2; color: #991b1b; }}
  </style>
</head>
<body>
  <div class="audit-header" data-checksum="{checksum}">
    <h1>8D INCIDENT COMPLIANCE AUDIT EVIDENCE PACKAGE</h1>
    <p><strong>Report ID:</strong> {safe_rep_id} | <strong>Asset Tag:</strong> {safe_asset}</p>
    <p class="sha-seal">Certified SHA-256 Checksum: {checksum}</p>
    <p style="margin: 4px 0 0 0; font-size: 9pt; color: #475569;">
      <strong>Standard:</strong> ISO 9001:2015 Clause 10.2 / IATF 16949 Section 10.2.3 / AIAG 8D
    </p>
    <div class="meta-grid">
      <div><strong>Severity Score:</strong> {report.severity_score}/10</div>
      <div><strong>RPN Score:</strong> {report.rpn_score}</div>
      <div><strong>Sign-off Status:</strong> {html.escape(report.d8_recognition.signoff_status.value)}</div>
    </div>
  </div>

  <div class="section-card">
    <h2>D1: Team Formation & D8: Recognition</h2>
    <p><strong>Leader:</strong> {safe_leader} | <strong>Champion:</strong> {safe_champion}</p>
    <p><strong>Approver:</strong> {html.escape(report.d8_recognition.approver_name)} ({html.escape(report.d8_recognition.approver_role)})</p>
    <p><em>{html.escape(report.d8_recognition.recognition_notes)}</em></p>
  </div>

  <div class="section-card">
    <h2>D2: Problem Description (5W2H)</h2>
    <p><strong>What:</strong> {safe_what}</p>
    <p><strong>Where:</strong> {safe_where}</p>
    <p><strong>When:</strong> {safe_when}</p>
  </div>

  <div class="section-card">
    <h2>D3: Interim Containment Actions (ICA)</h2>
    <table>
      <thead><tr><th>ID</th><th>Action</th><th>Owner</th><th>Effectiveness</th><th>Status</th></tr></thead>
      <tbody>{containment_rows}</tbody>
    </table>
  </div>

  <div class="section-card">
    <h2>D4: Root Cause Analysis (5-Why & Ishikawa)</h2>
    <p><strong>Occurrence Root Cause:</strong> {safe_occ_cause}</p>
    <p><strong>Escape Root Cause:</strong> {safe_esc_cause}</p>
    <table>
      <thead><tr><th>Level</th><th>Cause Statement</th><th>Root Cause?</th><th>Evidence</th></tr></thead>
      <tbody>{five_why_rows}</tbody>
    </table>
  </div>

  <div class="section-card">
    <h2>D5: Permanent Corrective Actions (PCA)</h2>
    <table>
      <thead><tr><th>ID</th><th>Action</th><th>Owner</th><th>Status</th></tr></thead>
      <tbody>{pca_rows}</tbody>
    </table>
  </div>

  <div class="section-card">
    <h2>Timeline: Chronological Event Sequence</h2>
    <table>
      <thead><tr><th>Timestamp</th><th>Type</th><th>Description</th></tr></thead>
      <tbody>{timeline_rows}</tbody>
    </table>
  </div>

  <div class="section-card">
    <h2>Citations: Verifiable Documentary Grounding</h2>
    <table>
      <thead><tr><th>Citation ID</th><th>Source Document</th><th>Excerpt</th><th>Confidence</th></tr></thead>
      <tbody>{citation_rows}</tbody>
    </table>
  </div>
</body>
</html>"""


# ==============================================================================
# REST API ENDPOINTS
# ==============================================================================

@router.post(
    "/analyze",
    response_model=EightDIncidentReport,
    status_code=status.HTTP_200_OK,
    summary="Execute Deductive RCA & Assemble 8D Report",
)
async def analyze_incident(req: RCAAnalyzeRequest):
    """
    Accepts failure symptoms, timestamp, and asset tag.
    Executes full deductive RCA pipeline: timeline extraction, OEM envelope analysis,
    historical matching, 5-Why tree, Ishikawa 6M classification, and D1-D8 report synthesis.
    Stores generated report in in-memory registry and returns complete EightDIncidentReport.
    """
    try:
        engine = DeductiveRCAEngine()
        report = engine.analyze_incident(req)
        report_store.save(report)
        logger.info(f"Successfully generated 8D report {report.report_id} for {req.asset_tag}")
        return report
    except Exception as e:
        logger.exception(f"Error analyzing incident for {req.asset_tag}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate 8D incident report: {str(e)}",
        )


@router.post(
    "/historical-match",
    response_model=List[HistoricalMatch],
    status_code=status.HTTP_200_OK,
    summary="Cross-Reference Incident Against Historical Near-Misses",
)
async def historical_match(req: HistoricalMatchRequest):
    """
    Compares failure symptoms and telemetry against historical near-miss records.
    Returns matched records with similarity score and preventative lessons learned.
    """
    try:
        # Handles empty symptoms safely by returning empty list
        if not req.symptoms:
            return []

        matches = match_historical_records(
            asset_tag=req.asset_tag,
            symptoms=req.symptoms,
            telemetry_features=req.telemetry_features,
        )
        return matches
    except Exception as e:
        logger.exception(f"Error executing historical match for {req.asset_tag}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Historical matching failed: {str(e)}",
        )


@router.post(
    "/export-evidence",
    response_model=ExportEvidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Export Certified Evidence Package (HTML or JSON)",
)
async def export_evidence(req: ExportEvidenceRequest):
    """
    Fetches the 8D incident report and renders a certified evidence package.
    Supports 'html' (print-ready ISO 9001/IATF 16949 audit package) and 'json'.
    Includes SHA-256 tamper-evident fingerprint.
    """
    fmt = (req.format or "html").strip().lower()
    if fmt not in ("html", "json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{req.format}': must be 'html' or 'json'",
        )

    try:
        report = report_store.get(req.report_id)
        if not report:
            # Graceful fallback demo package per E2E boundary test specification
            logger.warning(f"Report '{req.report_id}' not found in registry. Generating fallback package.")
            report = report_store.get_or_create_fallback(req.report_id)

        checksum = report.checksum_sha256 or report.compute_canonical_sha256()

        if fmt == "json":
            dumped = report.model_dump(mode="json")
            content = json.dumps(dumped, indent=2)
            filename = f"{report.report_id}_evidence_package.json"
        else:
            content = render_audit_html(report)
            filename = f"{report.report_id}_compliance_audit.html"

        return ExportEvidenceResponse(
            content=content,
            sha256_checksum=checksum,
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error exporting evidence package for {req.report_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.get(
    "/reports",
    response_model=List[EightDIncidentReportSummary],
    status_code=status.HTTP_200_OK,
    summary="List All Generated 8D Incident Reports",
)
async def list_reports():
    """
    Returns summary metadata for all reports currently registered in memory.
    """
    try:
        reports = report_store.list_all()
        summaries = []
        for rep in reports:
            title = rep.d2_problem.incident_title or rep.d2_problem.what
            status_str = (
                rep.d8_recognition.signoff_status.value
                if hasattr(rep.d8_recognition.signoff_status, "value")
                else str(rep.d8_recognition.signoff_status)
            )
            summaries.append(
                EightDIncidentReportSummary(
                    report_id=rep.report_id,
                    incident_title=title,
                    title=title,
                    asset_tag=rep.asset_tag,
                    severity_score=rep.severity_score,
                    rpn_score=rep.rpn_score,
                    created_at=rep.created_at,
                    status=status_str,
                    checksum_sha256=rep.checksum_sha256,
                    sha256_checksum=rep.checksum_sha256,
                )
            )
        return summaries
    except Exception as e:
        logger.exception("Error listing 8D incident reports")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not list reports: {str(e)}",
        )


@router.get(
    "/reports/{report_id}",
    response_model=EightDIncidentReport,
    status_code=status.HTTP_200_OK,
    summary="Fetch Full 8D Incident Report by ID",
)
async def get_report_by_id(report_id: str):
    """
    Fetches complete EightDIncidentReport object from the registry by its unique ID.
    Returns 404 if not found.
    """
    report = report_store.get(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found in registry.",
        )
    return report
```

---

### 4.2 Modifications Required in `backend/main.py`

In `backend/main.py`:
1. Import `rca_router`:
   ```python
   from api.rca_router import rca_router
   ```
2. Include the router under `/api/v1`:
   ```python
   # Include core API routes
   app.include_router(auth_router, prefix="/api/v1")
   app.include_router(api_router, prefix="/api/v1")
   app.include_router(rca_router, prefix="/api/v1")
   ```

---

### 4.3 Schema Enhancements in `backend/api/rca_schemas.py`

To ensure zero regressions across both unit tests and E2E contract test suites:
1. **`HistoricalMatchRequest`**:
   Change:
   ```python
   symptoms: List[str] = Field(default_factory=list, description="List of failure symptoms")
   ```
   (Removes `min_length=1` so `test_f9_b04` with `symptoms=[]` returns 200 with an empty list).
2. **`ExportEvidenceRequest`**:
   Remove the `@field_validator("format")` raising `ValueError` (or make it lenient), delegating the `400 Bad Request` raise to the FastAPI route handler so that invalid formats return HTTP 400 (per `test_f9_b03`) instead of 422.
3. **`EightDIncidentReportSummary`**:
   Add dual-compatible fields:
   ```python
   class EightDIncidentReportSummary(BaseModel):
       model_config = ConfigDict(extra="ignore")
       report_id: str
       created_at: str
       asset_tag: str
       severity_score: int
       rpn_score: int
       title: str = Field(default="")
       incident_title: Optional[str] = Field(None)
       status: str = Field(default="APPROVED")
       checksum_sha256: str = Field(default="")
       sha256_checksum: Optional[str] = Field(None)
   ```
   with a model validator syncing `title` <-> `incident_title` and `checksum_sha256` <-> `sha256_checksum`.
4. **`EightDIncidentReport`**:
   Add dual compatibility for `audit_metadata`:
   ```python
   audit_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
   ```
   synced automatically during `calculate_rpn_and_sort_timeline` and `compute_canonical_sha256`.

---

### 4.4 Engine Aliases in `backend/services/rca_engine.py`
Add explicit module alias:
```python
match_historical_near_misses = match_historical_records
```
This guarantees that any caller expecting `rca_engine.match_historical_near_misses` finds it directly.

---

### 4.5 Integration Test Suite Design (`backend/tests/test_rca_api.py`)

The implementer should create `backend/tests/test_rca_api.py` utilizing `fastapi.testclient.TestClient(app)` from `backend/main.py`:
1. `test_post_analyze_success`: 200 OK, returns `report_id` matching `^8D-[0-9]{4}-`, full D1–D8, 64-char SHA-256.
2. `test_post_analyze_missing_asset_tag_422`: 422 Unprocessable Entity.
3. `test_post_analyze_empty_symptoms_422`: 422 Unprocessable Entity.
4. `test_post_historical_match_success`: 200 OK, returns list of historical matches.
5. `test_post_historical_match_empty_symptoms_200`: 200 OK, returns `[]`.
6. `test_post_export_evidence_json`: 200 OK, valid JSON, matching SHA-256.
7. `test_post_export_evidence_html`: 200 OK, valid HTML with `@page`, `audit-header`, matching SHA-256.
8. `test_post_export_evidence_invalid_format_400`: 400 Bad Request on `format="xml"`.
9. `test_post_export_evidence_nonexistent_fallback_200`: 200 OK, valid fallback package.
10. `test_get_reports_list`: 200 OK, returns list of summaries.
11. `test_get_report_by_id_found`: 200 OK.
12. `test_get_report_by_id_not_found_404`: 404 Not Found.
13. `test_thread_safe_concurrency`: Concurrent requests to analyze, list, and export execute without exceptions.

---

## 5. Verification Method

To independently verify this design during/after Milestone 3 implementation:

### 5.1 Automated Pytest Commands
Execute from repository root (`C:\000 MINE\My Codzz\Industrial Mind OS`):

1. **Unit & API Integration Tests**:
   ```powershell
   pytest backend/tests/test_rca_api.py -v
   pytest backend/tests/test_rca_schemas.py backend/tests/test_rca_engine.py -v
   ```
2. **E2E RCA Contract Tests (Tiers 1–4)**:
   ```powershell
   pytest backend/tests/e2e_rca/test_tier1_feature_coverage.py -k "test_f9 or test_f10" -v
   pytest backend/tests/e2e_rca/test_tier2_boundary_corner.py -k "test_f9 or test_f10" -v
   pytest backend/tests/e2e_rca/test_tier3_cross_feature.py -k "test_cross_08 or test_cross_07" -v
   ```

### 5.2 Files to Inspect
- `backend/api/rca_router.py` (New file)
- `backend/main.py` (Route inclusion: lines 48–52)
- `backend/api/rca_schemas.py` (Relaxed validation on `HistoricalMatchRequest`, `ExportEvidenceRequest`)
- `backend/services/rca_engine.py` (Alias `match_historical_near_misses`)
- `backend/tests/test_rca_api.py` (New integration test file)

### 5.3 Invalidation Conditions
- Any route handler returning 500 on valid inputs.
- `POST /api/v1/rca/export-evidence` returning 422 instead of 400 when `format="xml"`.
- `POST /api/v1/rca/historical-match` returning 422 instead of 200 when `symptoms=[]`.
- Failure of `test_f9_b05` (graceful fallback export for unknown report IDs).
- Any race condition observed under multi-threaded concurrency.
