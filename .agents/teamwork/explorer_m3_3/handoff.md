# Milestone 3 Handoff Report: API Test Suite Architecture & Verification Strategy

**Author**: `explorer_m3_3`  
**Milestone**: Milestone 3 — RCA API Endpoints & Compliance Audit Packaging (`backend/api/rca_router.py`, `backend/main.py`, `backend/tests/test_rca_api.py`)  
**Parent Orchestrator ID**: `6083de2c-0790-4fdb-80b8-ee776e04b485`  
**Date**: 2026-10-07  

---

## 1. Observation

Direct observations from examining the codebase, dependencies, test harnesses, schemas, and execution environments:

### 1.1 Pytest Configuration & Test Conventions
- **Configuration File**: `backend/pytest.ini` (lines 1–4):
  ```ini
  [pytest]
  testpaths = tests
  pythonpath = .
  ```
  `pythonpath = .` ensures all packages (`api`, `services`, `db`, `core`, `storage`) are directly importable when pytest is executed from `backend/`.
- **Existing Unit Test Suites**:
  - `backend/tests/test_rca_schemas.py` (811 lines, 57 tests): Tests Pydantic v2 domain schemas, ISO 8601 parsing, RPN calculation ($S \times O \times D$), division-by-zero guards, and canonical SHA-256 computation.
  - `backend/tests/test_rca_ingestion.py` (603 lines, 42 tests): Tests `CitationRegistry`, `EvidenceCitationExtractor`, `TimelineExtractor`, deduplication, and out-of-order telemetry sorting.
  - `backend/tests/test_rca_engine.py` (990 lines, 59 tests): Tests `DeductiveRCAEngine`, `FiveWhyTreeBuilder`, `IshikawaClassifier`, `HistoricalMatcher`, `OEMOperatingEnvelopeEngine`, `assemble_eight_d_report`.
  - All 158 unit tests in `backend/tests/` execute with 100% pass rate in **0.45s** via `.\venv\Scripts\pytest tests/test_rca_schemas.py tests/test_rca_engine.py tests/test_rca_ingestion.py`.
- **Existing E2E RCA Test Suite** (`backend/tests/e2e_rca/`):
  - `tests/e2e_rca/conftest.py` (881 lines): Provides contract test harness, session-scoped `client` fixture using `fastapi.testclient.TestClient`, reference engines, and offline fixture logs (`pump_a12_telemetry_logs`, `near_miss_report_text`).
  - `tests/e2e_rca/test_tier1_feature_coverage.py` (50 tests): Covers Features F1–F10 (5 tests per feature). Specifically:
    - Lines 773–846 test Feature F9 (RCA REST API Router): `test_f9_01_api_analyze_returns_valid_8d_report`, `test_f9_02_api_historical_match_returns_matches`, `test_f9_03_api_export_evidence_json`, `test_f9_04_api_export_evidence_html`, `test_f9_05_api_list_reports_returns_summaries`.
    - Lines 852–1004 test Feature F10 (Compliance Audit Package Generator): `test_f10_01_canonical_json_deterministic_hash`, `test_f10_02_tamper_detection_on_telemetry_alteration`, `test_f10_03_html_export_audit_header_and_classes`, `test_f10_04_print_css_page_rules_in_audit_package`, `test_f10_05_sha256_verification_against_hashlib`.
  - `tests/e2e_rca/test_tier2_boundary_corner.py` (50 tests):
    - Lines 657–709 test F9 boundary cases: `test_f9_b01_empty_symptoms_payload_returns_422`, `test_f9_b02_missing_asset_tag_returns_422`, `test_f9_b03_unsupported_export_format_returns_400`, `test_f9_b04_empty_symptoms_historical_match_returns_200_empty`, `test_f9_b05_nonexistent_report_export_handled_gracefully`.
    - Lines 714–803 test F10 boundary cases: empty metadata hash, whitespace/key-order invariance, XSS injection escaping (`<script>alert('xss')</script>`), 1-bit mutation avalanche effect, large 100-event hash scalability (<100ms).
  - `tests/e2e_rca/test_tier3_cross_feature.py` (10 tests): Pairwise integration including `test_cross_08_full_api_workflow_pipeline` (`/analyze` -> `/historical-match` -> `/export-evidence`).
  - `tests/e2e_rca/test_tier4_real_world_scenarios.py` (6 tests): Industrial equipment scenarios (Pump-A12, Steam Turbine TURB-ST-04, Boiler BLR-HP-101).
  - All 116 tests in `backend/tests/e2e_rca/` execute with 100% pass rate in **0.33s**.

### 1.2 FastAPI App Structure in `backend/main.py`
- Direct inspection of `backend/main.py` (lines 8–51):
  ```python
  from fastapi import FastAPI
  from api.router import api_router
  from api.auth import router as auth_router
  from db.database import engine, Base
  from db import models

  Base.metadata.create_all(bind=engine)
  ...
  app = FastAPI(title="Industrial Mind OS API", version="1.0.0")
  app.include_router(auth_router, prefix="/api/v1")
  app.include_router(api_router, prefix="/api/v1")
  ```
- Empirically verified via `.\venv\Scripts\python -c "from fastapi.testclient import TestClient; from main import app; c = TestClient(app); resp = c.get('/health'); print(resp.status_code, resp.json())"`:
  - App instantiates cleanly without requiring external services.
  - SQLite creates local table metadata in `sqlite:///./industrial_mind_os.db` automatically.
  - `TestClient(app)` executes in-process ASGI requests with zero network port binding.

### 1.3 Schemas & Models Contract in `backend/api/rca_schemas.py`
- Request models:
  - `RCAAnalyzeRequest`: `asset_tag: str`, `symptoms: List[str] = Field(..., min_length=1)`, `incident_timestamp: str`, `telemetry_data: Optional[Dict[str, Any]] = Field(default_factory=dict)`.
  - `HistoricalMatchRequest`: `asset_tag: str`, `symptoms: List[str]`, `telemetry_features: Optional[Dict[str, Any]] = Field(default_factory=dict)`.
  - `ExportEvidenceRequest`: `report_id: str`, `format: str = Field(default="html")`.
- Response models:
  - `EightDIncidentReport`: Root report containing disciplines D1–D8, `timeline: List[TimelineEvent]`, `citations: List[CitationObject]`, `checksum_sha256: str`, method `compute_canonical_sha256() -> str`.
  - `HistoricalMatch`: `matched_report_id: str`, `title: str`, `similarity_score: float`, `matching_symptoms: List[str]`, `preventative_recommendations: List[str]`.
  - `ExportEvidenceResponse`: `content: str`, `sha256_checksum: str`, `filename: str`.
  - `EightDIncidentReportSummary`: `report_id: str`, `created_at: str`, `asset_tag: str`, `severity_score: int`, `rpn_score: int`, `title: str`, `status: str`, `checksum_sha256: str`.

### 1.4 Peer Exploration Findings (`explorer_m3_1` & `explorer_m3_2`)
- `explorer_m3_1`:
  - Router will be defined in `backend/api/rca_router.py` with `router = APIRouter(prefix="/rca", tags=["Root Cause Analysis (8D)"])` and registered in `backend/main.py` via `app.include_router(rca_router, prefix="/api/v1")`.
  - Provides thread-safe in-memory cache `RCAReportStore` with `threading.Lock`.
  - Routes:
    1. `POST /api/v1/rca/analyze`
    2. `POST /api/v1/rca/historical-match`
    3. `POST /api/v1/rca/export-evidence`
    4. `GET /api/v1/rca/reports`
    5. `GET /api/v1/rca/reports/{report_id}`
- `explorer_m3_2`:
  - Compliance generator produces certified HTML and JSON packages.
  - JSON format: serialized canonical representation, `filename="{report_id}_evidence_package.json"`.
  - HTML format: print-ready ISO 9001:2015 / IATF 16949 audit header (`class="audit-header"`), `@page { size: letter portrait; margin: 15mm 18mm; }`, `@media print`, SHA-256 seal badge (`class="sha-seal"`), XSS sanitization, `filename="{report_id}_compliance_audit.html"`.

---

## 2. Logic Chain

From these direct observations, we derive the structural and behavioral design for the Milestone 3 API test suite `backend/tests/test_rca_api.py`:

```
[Observation 1.1: pytest.ini testpaths=tests, pythonpath=.]
  + [Observation 1.2: backend/main.py mounts routers on app, TestClient(app) runs in-process]
  --> Test file must be placed at backend/tests/test_rca_api.py and test the actual mounted app.

[Observation 1.4: explorer_m3_1 defines 5 endpoints under /api/v1/rca]
  + [Authoritative Request §AC Backend: Pytest test suite covering RCA report generation passes 100%]
  --> Test suite must provide end-to-end integration coverage for all 5 endpoints across happy path,
      negative, boundary, and cryptographic assertions.

[Observation 1.1: e2e_rca/test_tier2_boundary_corner asserts 422 for missing fields/empty symptoms, 400 for bad format, 200 for empty match]
  --> Specific status codes must be strictly verified:
      - 422 Unprocessable Entity for schema validation failures
      - 400 Bad Request for unsupported export format (e.g., format="xml")
      - 404 Not Found for GET /api/v1/rca/reports/{non_existent_id}
      - 200 OK with [] for POST /api/v1/rca/historical-match with empty symptoms.

[Observation 1.3 & 1.4: Canonical SHA-256 computed over sorted JSON excluding checksum_sha256]
  --> Cryptographic integrity tests must verify:
      1. sha256_checksum in ExportEvidenceResponse exactly matches report.checksum_sha256.
      2. Recomputing SHA-256 over canonical JSON parsed from exported content matches the seal bit-for-bit.
      3. HTML contains data-checksum and human-readable seal matching the digest.
      4. Avalanche effect: a 1-character alteration to report data invalidates the digest (>50 bits changed).

[Observation 1.1: Unit and E2E test suites complete in < 0.5s with zero network dependencies]
  --> Test execution must remain 100% offline, deterministic, and isolated across test runs via fixture store cleanup.
```

---

## 3. Detailed Architecture of `backend/tests/test_rca_api.py`

The test suite will contain **30 distinct test cases** organized into 8 functional groups:

### 3.1 Test Hierarchy & Inventory

```
backend/tests/test_rca_api.py
├── Group 1: Router Mounting & OpenAPI Schema Inspection (3 tests)
│   ├── test_rca_router_mounted_in_main_app
│   ├── test_openapi_schema_contains_rca_endpoints
│   └── test_openapi_json_endpoint_accessible
│
├── Group 2: Happy Path Tests — POST /api/v1/rca/analyze (4 tests)
│   ├── test_analyze_pump_asset_returns_full_8d_report
│   ├── test_analyze_turbine_asset_detects_envelope_and_causes
│   ├── test_analyze_boiler_asset_generates_valid_report
│   └── test_analyze_generic_asset_fallback_without_error
│
├── Group 3: Happy Path Tests — POST /api/v1/rca/historical-match (3 tests)
│   ├── test_historical_match_pump_a12_baseline
│   ├── test_historical_match_sister_asset_pump_a11
│   └── test_historical_match_unmatched_asset_returns_empty_list
│
├── Group 4: Happy Path Tests — POST /api/v1/rca/export-evidence (4 tests)
│   ├── test_export_evidence_json_format
│   ├── test_export_evidence_html_format
│   ├── test_export_evidence_content_matches_stored_report
│   └── test_export_evidence_headers_and_filename
│
├── Group 5: Happy Path Tests — GET /api/v1/rca/reports & {report_id} (4 tests)
│   ├── test_list_reports_empty_returns_200_empty_list
│   ├── test_list_reports_populated_returns_summaries
│   ├── test_get_single_report_by_id_success
│   └── test_list_reports_summary_field_contract
│
├── Group 6: Negative & Boundary Test Cases (6 tests)
│   ├── test_analyze_missing_required_fields_returns_422
│   ├── test_analyze_empty_symptoms_list_returns_422
│   ├── test_analyze_invalid_timestamp_format_returns_422
│   ├── test_export_evidence_unsupported_format_returns_400
│   ├── test_export_evidence_missing_report_id_returns_422
│   └── test_get_nonexistent_report_returns_404
│
├── Group 7: Cryptographic Integrity & Tamper Evident Verification (3 tests)
│   ├── test_exported_checksum_matches_canonical_report_hash
│   ├── test_exported_html_embeds_matching_sha256_seal
│   └── test_tamper_detection_avalanche_effect
│
└── Group 8: Concurrency, Thread Safety & Offline Safety (3 tests)
    ├── test_concurrent_analyze_requests_thread_safe
    ├── test_pure_offline_execution_zero_network_calls
    └── test_execution_performance_under_budget
```

### 3.2 Fixtures & Isolation Strategy

```python
import pytest
from fastapi.testclient import TestClient
from main import app
from api.rca_router import rca_report_store

@pytest.fixture(autouse=True)
def clean_report_store():
    """
    Guarantees test isolation by clearing the in-memory report store
    before and after each test case.
    """
    rca_report_store.clear()
    yield
    rca_report_store.clear()

@pytest.fixture
def client():
    """Provides an in-process ASGI TestClient bound to main.app."""
    with TestClient(app) as test_client:
        yield test_client
```

### 3.3 Test Case Specifications

#### Group 1: Router Mounting & OpenAPI Schema Inspection
1. **`test_rca_router_mounted_in_main_app(client)`**:
   - Inspects `[route.path for route in app.routes]`.
   - Asserts inclusion of:
     - `/api/v1/rca/analyze` (POST)
     - `/api/v1/rca/historical-match` (POST)
     - `/api/v1/rca/export-evidence` (POST)
     - `/api/v1/rca/reports` (GET)
     - `/api/v1/rca/reports/{report_id}` (GET)
2. **`test_openapi_schema_contains_rca_endpoints(client)`**:
   - Calls `app.openapi()`.
   - Verifies `"/api/v1/rca/analyze"` exists in `openapi["paths"]` with `post` method.
   - Verifies summary, tags (contains `"Root Cause Analysis (8D)"`), and response code `200`.
   - Verifies `"/api/v1/rca/export-evidence"` requestBody schema references `ExportEvidenceRequest`.
3. **`test_openapi_json_endpoint_accessible(client)`**:
   - `client.get("/openapi.json")` returns `200 OK`.
   - JSON payload contains `/api/v1/rca/` paths.

#### Group 2: Happy Path Tests — `POST /api/v1/rca/analyze`
4. **`test_analyze_pump_asset_returns_full_8d_report(client)`**:
   - Payload: `asset_tag="Pump-A12"`, `symptoms=["mechanical seal failure", "vibration 5.8 mm/s"]`, `incident_timestamp="2023-11-04T08:00:00Z"`, `telemetry_data={"vibration_mm_s": 5.8, "temperature_c": 62.0}`.
   - Asserts:
     - Status: `200 OK`.
     - `report_id` regex match `^8D-[0-9]{4}-[A-Za-z0-9_\-]+$`.
     - Disciplines D1–D8 fully populated:
       - `d1_team.leader` non-empty, `len(d1_team.members) >= 1`.
       - `d2_problem.incident_title` non-empty, `d2_problem.initial_severity == 8`.
       - `d3_containment` list non-empty, `effectiveness_pct >= 90.0`.
       - `d4_root_causes.five_why_chain`: 5 nodes, level 1 to 5, level 5 `is_root_cause=True`.
       - `d4_root_causes.fishbone_analysis.branches`: all 6M categories present (Man, Machine, Material, Method, Measurement, Environment).
       - `d5_permanent_actions`: at least 1 action addressing root cause.
       - `d6_validation.status`: non-empty validation plan.
       - `d7_preventative_controls.oem_deviations`: contains vibration excursion (+16.0% deviation, CRITICAL).
       - `d8_recognition.signoff_status == "APPROVED"`.
     - `checksum_sha256`: 64-char hex string.
     - `timeline`: at least 1 event chronologically sorted.
     - `citations`: list of `CitationObject` with valid `confidence >= 0.8`.
5. **`test_analyze_turbine_asset_detects_envelope_and_causes(client)`**:
   - Payload: `asset_tag="TURB-ST-04"`, `symptoms=["rotor overspeed", "bearing temperature high"]`, `incident_timestamp="2023-11-04T12:00:00Z"`, `telemetry_data={"speed_rpm": 3450.0, "bearing_temp_c": 118.0}`.
   - Asserts:
     - Status `200 OK`.
     - Asset tag recorded as `"TURB-ST-04"`.
     - Envelope deviation identifies rotor speed exceedance vs 3,300 RPM envelope.
     - 5-Why and Fishbone trees successfully constructed.
6. **`test_analyze_boiler_asset_generates_valid_report(client)`**:
   - Payload: `asset_tag="BLR-HP-101"`, `symptoms=["superheater tube leak", "pressure drop", "thermocouple drift"]`, `incident_timestamp="2023-11-04T16:00:00Z"`, `telemetry_data={"pressure_bar": 92.0, "superheat_temp_c": 560.0}`.
   - Asserts:
     - Status `200 OK`.
     - Report conforms to schema with valid RPN score ($S \times O \times D$).
7. **`test_analyze_generic_asset_fallback_without_error(client)`**:
   - Payload: `asset_tag="COMPRESSOR-C03"`, `symptoms=["unusual gear whining", "motor overload trip"]`, `incident_timestamp="2023-11-04T18:00:00Z"`.
   - Asserts:
     - Status `200 OK`.
     - Gracefully constructs 8D report using fallback engineering rules without raising 500.

#### Group 3: Happy Path Tests — `POST /api/v1/rca/historical-match`
8. **`test_historical_match_pump_a12_baseline(client)`**:
   - Payload: `asset_tag="Pump-A12"`, `symptoms=["vibration", "ceramic seal", "coolant leak"]`.
   - Asserts:
     - Status `200 OK`.
     - Response is a list with `len >= 1`.
     - First match `matched_report_id == "NM-2023-PUMP-A12"`.
     - `similarity_score >= 0.8`.
     - `matching_symptoms` contains `"vibration"`.
     - `preventative_recommendations` non-empty.
9. **`test_historical_match_sister_asset_pump_a11(client)`**:
   - Payload: `asset_tag="Pump-A11"`, `symptoms=["vibration 5.8 mm/s"]`.
   - Asserts:
     - Status `200 OK`.
     - Successfully cross-references sister asset Pump-A12 near-miss record.
10. **`test_historical_match_unmatched_asset_returns_empty_list(client)`**:
    - Payload: `asset_tag="CONVEYOR-CV-99"`, `symptoms=["belt tearing", "idler bearing seizure"]`.
    - Asserts:
      - Status `200 OK`.
      - Returns `[]` or list with 0 high-confidence matches.

#### Group 4: Happy Path Tests — `POST /api/v1/rca/export-evidence`
11. **`test_export_evidence_json_format(client)`**:
    - Pre-populates a report via `/analyze`.
    - Payload: `{"report_id": rep_id, "format": "json"}`.
    - Asserts:
      - Status `200 OK`.
      - `filename == f"{rep_id}_evidence_package.json"`.
      - `len(sha256_checksum) == 64`.
      - `content` parses via `json.loads()` into a dict containing `"d1_team"`, `"d2_problem"`, `"d4_root_causes"`.
12. **`test_export_evidence_html_format(client)`**:
    - Pre-populates a report via `/analyze`.
    - Payload: `{"report_id": rep_id, "format": "html"}`.
    - Asserts:
      - Status `200 OK`.
      - `filename == f"{rep_id}_compliance_audit.html"`.
      - `len(sha256_checksum) == 64`.
      - `content` starts with `<!DOCTYPE html>`.
      - Contains `class="audit-header"`, `class="sha-seal"`, `"ISO 9001:2015"`.
      - Contains `@page { size: letter portrait; margin: 15mm 18mm; }` and `@media print`.
13. **`test_export_evidence_content_matches_stored_report(client)`**:
    - Compares values inside exported JSON directly with the response from `GET /api/v1/rca/reports/{report_id}`.
    - Asserts `exported["report_id"] == rep_id` and `exported["rpn_score"] == original["rpn_score"]`.
14. **`test_export_evidence_headers_and_filename(client)`**:
    - Validates response model contract: `ExportEvidenceResponse` fields `content`, `sha256_checksum`, `filename`.

#### Group 5: Happy Path Tests — `GET /api/v1/rca/reports` & `{report_id}`
15. **`test_list_reports_empty_returns_200_empty_list(client)`**:
    - Clean store.
    - `client.get("/api/v1/rca/reports")` returns `200 OK` with `[]`.
16. **`test_list_reports_populated_returns_summaries(client)`**:
    - Creates 2 reports via `/analyze` (Pump-A12 and TURB-ST-04).
    - `client.get("/api/v1/rca/reports")` returns `200 OK` with `len == 2`.
17. **`test_get_single_report_by_id_success(client)`**:
    - Creates a report via `/analyze`.
    - `client.get(f"/api/v1/rca/reports/{rep_id}")` returns `200 OK`.
    - Body is full `EightDIncidentReport` with all D1–D8 disciplines.
18. **`test_list_reports_summary_field_contract(client)`**:
    - Verifies each item in `GET /api/v1/rca/reports` contains:
      - `report_id: str`
      - `created_at: str`
      - `asset_tag: str`
      - `severity_score: int`
      - `rpn_score: int`
      - `title: str` (and `incident_title: str` for dual compatibility)
      - `status: str`
      - `checksum_sha256: str` (and `sha256_checksum: str`)

#### Group 6: Negative & Boundary Test Cases
19. **`test_analyze_missing_required_fields_returns_422(client)`**:
    - Subcase a: Missing `asset_tag` -> `422 Unprocessable Entity`.
    - Subcase b: Missing `symptoms` -> `422 Unprocessable Entity`.
    - Subcase c: Missing `incident_timestamp` -> `422 Unprocessable Entity`.
    - Subcase d: Non-dictionary `telemetry_data` (e.g. `"telemetry_data": "invalid"`) -> `422 Unprocessable Entity`.
20. **`test_analyze_empty_symptoms_list_returns_422(client)`**:
    - Payload with `symptoms=[]` -> returns `422 Unprocessable Entity` (`min_length=1` rule).
21. **`test_analyze_invalid_timestamp_format_returns_422(client)`**:
    - Payload with `incident_timestamp="not-a-timestamp"` -> returns `422 Unprocessable Entity`.
    - Payload with `incident_timestamp="2023-99-99"` -> returns `422 Unprocessable Entity`.
22. **`test_export_evidence_unsupported_format_returns_400(client)`**:
    - Payload with `{"report_id": "8D-2023-PUMP-A12", "format": "xml"}` -> returns **`400 Bad Request`** (strictly 400, not 422, matching E2E `test_f9_b03`).
    - Payload with `{"report_id": "8D-2023-PUMP-A12", "format": "pdf"}` -> returns **`400 Bad Request`**.
23. **`test_export_evidence_missing_report_id_returns_422(client)`**:
    - Payload with `{"format": "json"}` (missing `report_id`) -> returns `422 Unprocessable Entity`.
24. **`test_get_nonexistent_report_returns_404(client)`**:
    - `client.get("/api/v1/rca/reports/8D-DOES-NOT-EXIST")` -> returns **`404 Not Found`** with descriptive error message.

#### Group 7: Cryptographic Integrity & Tamper Evident Verification
25. **`test_exported_checksum_matches_canonical_report_hash(client)`**:
    - Creates report via `/analyze`.
    - Calls `/export-evidence` with `format="json"`.
    - Parses JSON content back into dict, removes `checksum_sha256`.
    - Serializes with `json.dumps(obj, sort_keys=True, separators=(",", ":"))`.
    - Recomputes SHA-256 via `hashlib.sha256()`.
    - Asserts computed digest == `response.json()["sha256_checksum"]` == original `report["checksum_sha256"]`.
26. **`test_exported_html_embeds_matching_sha256_seal(client)`**:
    - Calls `/export-evidence` with `format="html"`.
    - Extracts `sha256_checksum` from API response.
    - Asserts HTML content contains `f'data-checksum="{sha256_checksum}"'`.
    - Asserts HTML content contains `f'Certified SHA-256 Checksum: {sha256_checksum}'`.
27. **`test_tamper_detection_avalanche_effect(client)`**:
    - Takes canonical exported JSON string.
    - Mutates single character in asset tag (e.g. `"Pump-A12"` -> `"Pump-A13"`).
    - Recomputes SHA-256 digest of tampered text.
    - Converts original and tampered hex digests to integers and counts XOR differing bits:
      `bin(int(orig, 16) ^ int(tampered, 16)).count("1")`.
    - Asserts differing bits > 50 (validating cryptographic avalanche effect).

#### Group 8: Concurrency, Thread Safety & Offline Safety
28. **`test_concurrent_analyze_requests_thread_safe(client)`**:
    - Uses `concurrent.futures.ThreadPoolExecutor(max_workers=5)` to submit 10 simultaneous `/analyze` requests with differing asset tags.
    - All 10 requests return `200 OK`.
    - In-memory report store retains all 10 reports with unique IDs and zero data corruption.
29. **`test_pure_offline_execution_zero_network_calls(client, monkeypatch)`**:
    - Monkeypatches `socket.socket.connect` to raise `RuntimeError("Network access attempted during offline test!")`.
    - Executes complete API lifecycle: `/analyze` -> `/historical-match` -> `/export-evidence` -> `/reports`.
    - Verifies complete suite executes with zero network attempts.
30. **`test_execution_performance_under_budget(client)`**:
    - Measures wall-clock execution time of `/analyze` endpoint for Pump-A12.
    - Asserts complete report generation, timeline reconstruction, 5-Why branching, 6M Fishbone classification, and SHA-256 hashing completes in `< 250ms`.

---

## 4. Implementation Guidelines for Implementer (`worker_m3`)

### 4.1 Schema Alignments Needed in `backend/api/rca_schemas.py`
To satisfy both unit tests and E2E tests (`test_f9_b03` and `test_f9_b04`):
1. **`HistoricalMatchRequest`**:
   Change `symptoms: List[str] = Field(..., min_length=1)` to:
   ```python
   symptoms: List[str] = Field(default_factory=list, description="List of failure symptoms")
   ```
   This allows `POST /api/v1/rca/historical-match` with `symptoms=[]` to return `200 OK` with `[]` instead of 422.
2. **`ExportEvidenceRequest`**:
   Remove the Pydantic `@field_validator("format")` that raises `ValueError` (which FastAPI turns into 422), and allow `format: str = "html"`. The format validation check (`if req.format.lower() not in ("html", "json"): raise HTTPException(400, ...)`) must occur inside `rca_router.py` to return **HTTP 400 Bad Request**.
3. **Dual Compatibility on Summary and Report**:
   Ensure `EightDIncidentReportSummary` provides both `title` and `incident_title`, and both `checksum_sha256` and `sha256_checksum`. Ensure `EightDIncidentReport` provides `checksum_sha256` and an `audit_metadata` property containing `sha256_checksum`.

### 4.2 Exact Implementation Structure for `backend/tests/test_rca_api.py`

```python
"""
Industrial Mind OS - RCA API Integration Test Suite
Location: backend/tests/test_rca_api.py

Verifies:
1. FastAPI Router mounting in backend/main.py and OpenAPI spec exposure.
2. Happy path tests across all 5 endpoints:
   - POST /api/v1/rca/analyze (Pump, Turbine, Boiler, Generic assets)
   - POST /api/v1/rca/historical-match (Baseline, Sister assets, Unmatched)
   - POST /api/v1/rca/export-evidence (JSON & HTML compliance packages)
   - GET /api/v1/rca/reports (Summary listings)
   - GET /api/v1/rca/reports/{report_id} (Single report retrieval)
3. Negative & Boundary test cases (422 for missing fields/empty symptoms, 400 for bad format, 404 for missing report).
4. Cryptographic integrity & canonical SHA-256 seal verification.
5. Concurrency, thread safety, and pure-offline operation.
"""

from __future__ import annotations

import hashlib
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from main import app
from api.rca_router import rca_report_store
from api.rca_schemas import EightDIncidentReport, RCAAnalyzeRequest

# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(autouse=True)
def clean_report_store():
    """Isolate tests by clearing in-memory store before and after each test."""
    rca_report_store.clear()
    yield
    rca_report_store.clear()


@pytest.fixture
def client():
    """In-process ASGI TestClient bound to main.app."""
    with TestClient(app) as test_client:
        yield test_client

# ... Implement 30 test cases following the detailed specifications in Section 3 ...
```

---

## 5. Caveats

1. **In-Memory Store Resets**: The `rca_report_store` stores reports in memory. In multi-process production deployments (e.g. multiple Uvicorn workers), each worker would have its own memory space unless backed by Redis or SQLite. For Milestone 3 and test automation, the thread-safe in-memory store (`RCAReportStore` with `threading.Lock`) is the specified design.
2. **Public Unauthenticated Access**: In accordance with the E2E test harness requirements and Milestone 3 specifications, `/api/v1/rca/*` endpoints do not require bearer token authentication.
3. **No Caveats on Implementation Boundary**: As explorer, this investigation was conducted strictly read-only; no production backend files or test files were modified.

---

## 6. Conclusion

1. **Test Suite Location**: The API integration test suite must be placed in `backend/tests/test_rca_api.py`.
2. **Test Scope & Coverage**: 30 comprehensive integration test cases covering:
   - Route mounting & OpenAPI inspection
   - Happy path across diverse industrial assets (Pumps, Turbines, Boilers, Generic)
   - Historical matching (baseline, sister assets, unmatched)
   - Evidence packaging (JSON & print-ready HTML with ISO/IATF metadata)
   - Report listing & single report retrieval
   - Boundary & Negative validation (HTTP 422, 400, 404)
   - SHA-256 cryptographic verification & tamper detection
   - Concurrency & 100% offline safety
3. **Verification Command**:
   ```powershell
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\backend"
   .\venv\Scripts\pytest tests/test_rca_api.py -v
   ```
   Combined regression command:
   ```powershell
   .\venv\Scripts\pytest tests/test_rca_schemas.py tests/test_rca_engine.py tests/test_rca_ingestion.py tests/test_rca_api.py tests/e2e_rca/ -v
   ```

---

## 7. Verification Method

To independently verify the architecture and execution readiness:

1. **Inspect Handoff Artifact**:
   Confirm file exists at `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m3_3\handoff.md`.
2. **Verify Current Regression Baseline**:
   Run unit tests and E2E tests to ensure 100% baseline pass:
   ```powershell
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\backend"
   .\venv\Scripts\pytest tests/test_rca_schemas.py tests/test_rca_engine.py tests/test_rca_ingestion.py tests/e2e_rca/
   ```
   Expected: 274 passed in < 1.0s.
3. **Post-Implementation Verification (by Worker M3)**:
   Once `rca_router.py` is mounted in `main.py` and `test_rca_api.py` is written:
   ```powershell
   .\venv\Scripts\pytest tests/test_rca_api.py -v
   ```
   Expected: 30 passed in < 1.5s with zero warnings or errors.
