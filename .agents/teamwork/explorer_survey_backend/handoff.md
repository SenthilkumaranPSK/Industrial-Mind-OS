# Handoff Report: Backend Codebase Survey & RCA 8D Studio Architecture

**Agent**: `explorer_survey_backend`  
**Working Directory**: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_survey_backend`  
**Target Recipient**: Orchestrator / Caller (`ef889b9f-7189-4139-bdab-296efd4f52ff`)  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

1. **Authoritative Requirements**:
   - `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md`, lines 13–35 specify:
     - R1: Incident Evidence & Timeline Extraction (failure symptoms, timestamps, equipment tags, traversing manuals/logs/knowledge graph).
     - R2: Deductive Root Cause Analysis Engine (5-Why and Ishikawa/Fishbone, grounded in documentation, flagging unsubstantiated assumptions).
     - R3: Interactive 8D Report Artifact Studio (frontend studio component and exportable HTML/PDF evidence artifact conforming to full Eight Disciplines).
     - R4: Preventative Action & Historical Matching (cross-referencing against historical near-misses and OEM operating envelopes).
     - Acceptance Criteria: Pytest test suite covering RCA report generation endpoints passes 100%; strict Pydantic schema validation; retrieval verification linking assertions to citation objects.

2. **Existing Backend Framework & Entry Point**:
   - `backend/main.py`, lines 10–15:
     ```python
     from api.router import api_router
     from api.auth import router as auth_router
     from db.database import engine, Base
     from db import models
     Base.metadata.create_all(bind=engine)
     ```
   - Lines 49–50 mount both routers:
     ```python
     app.include_router(auth_router, prefix="/api/v1")
     app.include_router(api_router, prefix="/api/v1")
     ```

3. **Existing API Endpoints & Handlers**:
   - `backend/api/router.py`:
     - Line 59: `@api_router.post("/upload", response_model=StatusResponse)`
     - Line 220: `@api_router.post("/query", response_model=QueryResponse)`
     - Line 287: `@api_router.delete("/documents/{filename}", response_model=StatusResponse)`
     - Line 319: `@api_router.get("/alerts")`
     - Line 330: `@api_router.delete("/alerts/{alert_id}")`
     - Line 338: `@api_router.get("/documents")`
     - Line 357: `@api_router.get("/graph/data")`
     - Line 363: `@api_router.get("/suggestions")`
     - Line 387: `@api_router.post("/confluence/sync", response_model=StatusResponse)`
     - Line 410: `@api_router.get("/graph/stats")`
   - `backend/api/auth.py`:
     - Line 47: `@router.post("/register", response_model=auth_schemas.UserResponse)`
     - Line 67: `@router.post("/login", response_model=auth_schemas.Token)`
     - Line 80: `@router.get("/me")`
     - Lines 14–35 define `get_current_user(token, db)` returning `{"id": str(user.id), "email": user.email, "username": user.username}`.

4. **Data Stores & Ownership Scoping**:
   - `backend/storage/vector_db.py`: Qdrant client in local disk mode (`backend/qdrant_data/`, collection `imos_collection`, vector_size 384, cosine distance).
   - `backend/storage/graph_db.py`: NetworkX `MultiDiGraph` serialized to `backend/graph_db.json`. Edges created by `ingestion_pipeline.populate_graph` as `co-occurs-with`.
   - `backend/storage/memory_cache.py`: JSON dictionary serialized to `backend/memory_cache.json`.
   - `backend/immune/macrophage.py`: Asynchronous auditor scanning for CONTRADICTION, COMPLIANCE GAP, HISTORICAL PATTERN, persisted to `backend/alerts.json`.
   - `backend/db/database.py` & `models.py`: SQLite `industrial_mind_os.db` with `User` table (`id`, `username`, `email`, `hashed_password`, `created_at`).
   - Every store filters by `owner_id`.

5. **Sample Industrial & Near-Miss Data**:
   - `Near_Miss_Report_2023.txt`: Incident on 2023-11-04 for `Pump-A12` in Primary Cooling Loop, Sector 4.
   - Vibration 5.8 mm/s for 48 hours prior to failure shattered inboard ceramic seals. OEM manual limit is 5.0 mm/s; shutdown protocol threshold is >5.5 mm/s.

6. **Testing Suite & Seam Rules**:
   - Command: `.\venv\Scripts\pytest.exe` executed from `backend/`.
   - Result:
     ```
     collected 27 items
     tests\test_ingestion_split.py ..... [ 18%]
     tests\test_scoping.py ..........    [ 55%]
     tests\test_text_utils.py .....      [ 74%]
     tests\test_verification.py .......  [100%]
     ============================= 27 passed in 0.50s ==============================
     ```
   - Invariant noted in `CLAUDE.md`, line 37:
     `"The suite is deliberately built out of seams that need no LLM, no network and no Qdrant lock... anything that imports agents/orchestrator.py or api/router.py transitively boots the Qdrant local client and takes the qdrant_data/ lock, which fails if a backend is already running."`

7. **Runtime Environment & Installed Libraries**:
   - Python 3.11.9 (`backend\venv\Scripts\python.exe`).
   - Installed: `fastapi==0.141.1`, `pydantic==2.13.4`, `networkx==3.6.1`, `qdrant-client==1.19.0`, `langgraph==1.2.11`, `langchain-core==1.6.0`, `langchain-google-genai==4.3.6`, `sentence-transformers==6.1.0`, `sqlalchemy==2.0.52`, `pytest==9.1.1`, `jinja2==3.1.6`, `numpy==2.4.6`, `scikit-learn==1.9.1`.

---

## 2. Logic Chain

1. **From Observation 1 to Missing Capabilities**:
   - Requirement R1–R4 requires incident evidence ingestion, chronological timeline reconstruction, 5-Why & Ishikawa reasoning, historical near-miss cross-referencing, and structured 8D report generation.
   - Observation 3 shows existing endpoints only cover general RAG chat (`/query`), file upload (`/upload`), and proactive alerts (`/alerts`).
   - Therefore, a dedicated RCA subsystem (`api/rca_router.py` or equivalent endpoints) and corresponding domain models (`api/rca_schemas.py`) must be introduced to fulfill the contract.

2. **From Observation 4 and 5 to RCA Retrieval Modeling**:
   - Observation 4 shows document and graph data are keyed by filename and user `owner_id`.
   - Observation 5 shows real industrial incident data (`Near_Miss_Report_2023.txt`) centers on `equipment_tag` ("Pump-A12"), operational parameters ("vibration: 5.8 mm/s"), and OEM limits ("5.0 mm/s").
   - Therefore, the RCA timeline and historical matching engine must index or cross-reference equipment tags, parameters, and historical incident records directly against internal stores and OEM limits to extract authoritative source citations.

3. **From Observation 6 to Test Architecture Design**:
   - Observation 6 demonstrates all existing 27 tests run offline in 0.50s without booting Qdrant or calling Gemini.
   - Any test that imports modules with un-mocked Qdrant or live Gemini dependencies will fail or hang when a development server holds `backend/qdrant_data/`.
   - Therefore, the RCA deductive engine, timeline builder, 5-Why/Ishikawa analyzer, and 8D report generation must be implemented as clean, decoupled service classes (`services/rca_engine.py`) accepting mockable or in-memory stores. This guarantees 100% test pass rate in pytest under offline conditions.

4. **From Observation 7 to Implementation Readiness**:
   - All necessary dependencies (FastAPI, Pydantic v2, NetworkX, Jinja2, Pytest) are already present in `backend/venv`.
   - Therefore, implementation can proceed immediately without installing new packages or altering system-level environments.

---

## 3. Caveats

- **No Live LLM in Tests**: The RCA engine implementation must include a deterministic fallback / rule-based deductive reasoning mode for offline testing and when `GOOGLE_API_KEY` is unavailable or placeholder.
- **Qdrant Single-Process Mode**: Running pytest while the FastAPI dev server is running requires that tests do NOT instantiate a local `QdrantClient(path="qdrant_data")`. All tests must use injected or mock stores.
- **Frontend Sync**: Frontend currently renders artifacts via `[ARTIFACT: Name]` blocks in `MarkdownRenderer.jsx` and `ArtifactPanel.jsx`. The 8D studio can be exposed both as an interactive artifact and via direct API JSON for the tabbed studio navigation.

---

## 4. Conclusion

The backend codebase of Industrial Mind OS is well-structured, modern (FastAPI + Pydantic v2 + Python 3.11), and cleanly isolated. To deliver the Automated RCA & 8D Incident Report Studio:
1. **Pydantic Models (`api/rca_schemas.py`)**: Define strict schemas for Eight Disciplines (D1–D8), severity scores, timeline events, 5-Why chains, Ishikawa categories, and verifiable citation objects.
2. **Core RCA Engine (`services/rca_engine.py`)**: Implement timeline extraction, 5-Why & Ishikawa multi-stage deductive reasoning, assumption flagging, and historical near-miss matching (leveraging `Near_Miss_Report_2023.txt` and OEM envelopes).
3. **API Endpoints (`api/rca_router.py`)**: Expose `POST /api/v1/rca/analyze`, `POST /api/v1/rca/historical-match`, `POST /api/v1/rca/export-evidence`, and `GET /api/v1/rca/reports`, registered in `backend/main.py`.
4. **Test Suite (`tests/test_rca_engine.py`, `tests/test_rca_api.py`)**: Test all 8D schema validations, causal citation verification, 5-Why chains, and API endpoints using FastAPI's `TestClient` in an offline, lock-free manner.

---

## 5. Verification Method

To independently verify all findings in this report:
1. **Verify Python Environment**:
   ```bash
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\backend"
   .\venv\Scripts\python.exe --version
   # Expected: Python 3.11.9
   ```
2. **Verify Existing Pytest Suite**:
   ```bash
   cd "C:\000 MINE\My Codzz\Industrial Mind OS\backend"
   .\venv\Scripts\pytest.exe
   # Expected: 27 passed in ~0.50s
   ```
3. **Verify Key Files Inspected**:
   - `backend/main.py` (FastAPI app & routers)
   - `backend/api/router.py` (Current endpoints)
   - `backend/storage/vector_db.py` & `graph_db.py` (Data stores)
   - `Near_Miss_Report_2023.txt` (Historical near-miss sample)
   - `survey_report.md` in this directory (`C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_survey_backend\survey_report.md`)
4. **Invalidation Condition**:
   - Findings would be invalidated if new endpoints or existing RCA models are discovered outside `backend/` or if the test suite fails when executed.
