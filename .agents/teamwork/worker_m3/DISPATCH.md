## 2026-10-07T05:56:06Z

You are worker_m3.
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m3

Authoritative Request:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md

Master Project Plan:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\orchestrator_1\PROJECT.md

Explorer Reports:
- C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m3_1\handoff.md
- C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m3_2\handoff.md
- C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m3_3\handoff.md

Write Ownership:
You own exclusively:
- backend/api/rca_router.py
- backend/services/compliance_package.py
- backend/api/rca_schemas.py (adjust HistoricalMatchRequest.symptoms to allow empty list without 422, adjust ExportEvidenceRequest.format to allow string so router can return 400 Bad Request)
- backend/main.py (mount rca_router under prefix="/api/v1")
- backend/tests/test_rca_api.py
Do not modify any other files without cause.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Detailed Tasks:
1. Implement Certified Compliance Audit Package Generator in backend/services/compliance_package.py:
   - Functions:
     - `generate_compliance_package(report: EightDIncidentReport, format: str = "html") -> tuple[str, str, str]`: returns `(content, sha256_checksum, filename)`
     - `build_audit_html(report: EightDIncidentReport) -> str`: print-ready HTML with `<!DOCTYPE html>`, ISO 9001:2015 Clause 10.2 / IATF 16949 / AIAG 8D header, `<div class="audit-header" data-checksum="...">`, `<p class="sha-seal">Certified SHA-256 Checksum: ...</p>`, CSS print rules `@page { size: letter portrait; margin: 15mm 18mm; }`, `@media print`, formatted disciplines D1-D8, 5-Why causal tree, 6M Fishbone, OEM deviations, Citations table with confidence scores, quality manager sign-off block, and HTML entity escaping (`html.escape`) to prevent XSS.
     - `build_audit_json(report: EightDIncidentReport) -> str`: canonical JSON representation ensuring root access to `"d1_team"` and canonical hash.
     - `verify_compliance_checksum(report: EightDIncidentReport) -> bool`.

2. Update Schema adjustments in backend/api/rca_schemas.py:
   - In `HistoricalMatchRequest`: change `symptoms: List[str] = Field(..., min_length=1)` to `symptoms: List[str] = Field(default_factory=list)` (or allow empty list), so that `symptoms=[]` returns HTTP 200 with an empty list `[]` per test_f9_b04.
   - In `ExportEvidenceRequest`: remove or relax `@field_validator("format")` so that invalid formats (e.g. `format="xml"`) pass Pydantic schema validation and allow the route handler to raise `HTTPException(status_code=400, detail=...)` per test_f9_b03 (which explicitly asserts HTTP 400 Bad Request, NOT 422).

3. Implement FastAPI Router in backend/api/rca_router.py:
   - `router = APIRouter(prefix="/rca", tags=["Root Cause Analysis (8D)"])`
   - `rca_router = router`
   - Implement thread-safe in-memory `RCAReportStore` with `threading.Lock`:
     - `add(report: EightDIncidentReport)`
     - `get(report_id: str) -> Optional[EightDIncidentReport]`
     - `list_all() -> List[EightDIncidentReportSummary]`
     - `get_or_fallback(report_id: str) -> EightDIncidentReport`: if `report_id` not found in store, generate an authentic fallback demo report (e.g. for `8D-NONEXISTENT` as tested by test_f9_b05) so evidence export succeeds with HTTP 200.
   - Endpoints:
     - `POST /api/v1/rca/analyze`: accepts `RCAAnalyzeRequest`, generates `EightDIncidentReport` via `rca_engine.assemble_eight_d_report` / `RCAEngine`, caches it in `RCAReportStore`, returns `EightDIncidentReport` (200 OK). Invalid payload returns 422.
     - `POST /api/v1/rca/historical-match`: accepts `HistoricalMatchRequest`, calls `match_historical_records(req.asset_tag, req.symptoms, req.telemetry_features)` (or `HistoricalMatcher`), returns `List[HistoricalMatch]` (200 OK). Empty symptoms returns `[]` (200 OK).
     - `POST /api/v1/rca/export-evidence`: accepts `ExportEvidenceRequest`, validates `req.format.lower() in ("html", "json")` (if not, raises HTTPException(400)), fetches report via `store.get_or_fallback(req.report_id)`, calls `generate_compliance_package(report, req.format)`, returns `ExportEvidenceResponse(content=content, sha256_checksum=checksum, filename=filename)` (200 OK).
     - `GET /api/v1/rca/reports`: returns `List[EightDIncidentReportSummary]` from `store.list_all()` (200 OK).
     - `GET /api/v1/rca/reports/{report_id}`: returns `EightDIncidentReport` if found (200 OK), or raises HTTPException(404) if not found.

4. Mount Router in backend/main.py:
   - Import `from api.rca_router import rca_router`
   - Register `app.include_router(rca_router, prefix="/api/v1")`

5. Implement Comprehensive Integration Tests in backend/tests/test_rca_api.py:
   - Use FastAPI `TestClient(app)` from `main.py`.
   - Test all 5 endpoints:
     - Router mounting and OpenAPI schema presence under `/api/v1/rca/*`.
     - Happy path for `/analyze` across pumps, steam turbines, boilers, and generic assets.
     - Happy path for `/historical-match` (matches found and empty symptoms returning `[]`).
     - Happy path for `/export-evidence` (both HTML and JSON with SHA-256 seal validation).
     - Happy path for `GET /reports` and `GET /reports/{report_id}`.
     - Status code validations: 200, 400 (unsupported export format), 404 (unknown report lookup on GET /reports/{id}), 422 (missing asset_tag, empty symptoms on /analyze).
     - Full pipeline workflow (`/analyze` -> `/historical-match` -> `/export-evidence`).
     - Offline safety and concurrency checks.

6. Execute Full Test Suite:
   Run via powershell:
   - backend\venv\Scripts\pytest.exe backend/tests/test_rca_api.py -v
   - backend\venv\Scripts\pytest.exe backend/tests/test_rca_engine.py -v
   - backend\venv\Scripts\pytest.exe backend/tests/test_rca_schemas.py -v
   - backend\venv\Scripts\pytest.exe backend/tests/test_adversarial_m2_stress.py -v
   - backend\venv\Scripts\pytest.exe backend/tests/ -q
   Ensure 100% pass with 0 failures across all tests!
