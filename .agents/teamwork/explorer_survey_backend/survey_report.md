# Comprehensive Backend Survey Report: Industrial Mind OS & RCA 8D Incident Studio

**Date**: 2026-10-05  
**Surveyor**: Backend Codebase Explorer (`explorer_survey_backend`)  
**Workspace**: `C:\000 MINE\My Codzz\Industrial Mind OS`  
**Working Directory**: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_survey_backend`  

---

## Executive Summary

Industrial Mind OS is an industrial knowledge intelligence platform built with a Python **FastAPI** backend and a **React + Vite** frontend. The backend integrates a local-first RAG stack combining an embedded **Qdrant** vector store (persisted to disk), an in-memory/JSON-serialized **NetworkX MultiDiGraph**, a fast JSON **DirectMemoryCache** (<15,000 chars direct injection), and a multi-agent **LangGraph** orchestration pipeline backed by **Google Gemini** models.

The current system has no dedicated Root Cause Analysis (RCA), 5-Why/Ishikawa engine, or Eight Disciplines (8D) incident report generation models/endpoints. However, the existing infrastructure provides robust primitives (per-user scoping via `owner_id`, keyword graph traversal, dual-path document ingestion, and citation verification) upon which the new enterprise-grade **Automated RCA & 8D Incident Report Studio** can be cleanly constructed.

---

## 1. Backend Architecture & Framework Overview

### 1.1 Directory Structure
The backend repository is located in `backend/` with the following modular structure:
```
backend/
├── main.py                     # Application entry point, CORS, router mounting
├── pytest.ini                  # Pytest configuration (pythonpath = ., testpaths = tests)
├── requirements.txt            # Production runtime dependencies
├── requirements-dev.txt        # Development dependencies (pytest)
├── industrial_mind_os.db       # SQLite database (Users & auth)
├── qdrant_data/                # Local disk storage for Qdrant vector database (exclusive lock)
├── api/
│   ├── auth.py                 # User authentication endpoints & JWT dependency (get_current_user)
│   ├── auth_schemas.py         # Pydantic schemas for auth (Token, UserCreate, UserResponse)
│   ├── router.py               # Core API router (upload, query, documents, alerts, graph, confluence)
│   └── schemas.py              # Pydantic schemas for query, citations, status
├── agents/
│   ├── orchestrator.py         # Multi-agent LangGraph workflow (Planner -> Retrieval -> Synthesis -> Verifier)
│   └── verification.py         # Pure heuristic scoring function for synthesized outputs
├── core/
│   ├── security.py             # JWT token handling (python-jose) and password hashing (passlib/bcrypt)
│   ├── embeddings.py           # Lazy singleton wrapper for HuggingFace all-MiniLM-L6-v2 (CPU local)
│   ├── text_utils.py           # Text cleaners (e.g. repairing spaced-out PDF text artifacts)
│   └── confluence.py           # Enterprise Confluence Cloud sync engine
├── db/
│   ├── database.py             # SQLAlchemy engine & sessionmaker (sqlite:///./industrial_mind_os.db)
│   └── models.py               # SQLAlchemy ORM models (User model)
├── immune/
│   └── macrophage.py           # Asynchronous Proactive Auditor / Immune System scanner
├── storage/
│   ├── vector_db.py            # Qdrant client wrapper (local disk mode or server)
│   ├── graph_db.py             # NetworkX MultiDiGraph wrapper (graph_db.json)
│   ├── memory_cache.py         # DirectMemoryCache JSON wrapper (memory_cache.json)
│   └── ingestion.py            # Semantic chunking (cosine similarity threshold) & keyword graph builder
└── tests/
    ├── test_ingestion_split.py # Offline semantic splitter chunk boundary tests
    ├── test_scoping.py         # User isolation tests for cache and graph
    ├── test_text_utils.py      # PDF text cleanup unit tests
    └── test_verification.py    # Offline verifier heuristic score unit tests
```

### 1.2 Runtime Environment & Interpreter
- **Python Version**: CPython 3.11.9 (`backend/venv/Scripts/python.exe`)
- **Web Framework**: FastAPI `0.141.1` on Uvicorn `0.52.4` / Starlette `1.6.0`
- **Validation**: Pydantic `2.13.4` (with `pydantic-settings` `2.15.0`)
- **Graph Processing**: NetworkX `3.6.1`
- **Vector Client**: Qdrant-Client `1.19.0`
- **Multi-Agent RAG**: LangGraph `1.2.11`, LangChain Core `1.6.0`, LangChain Google GenAI `4.3.6`
- **ORM / Storage**: SQLAlchemy `2.0.52`, SQLite

---

## 2. Existing Endpoints & API Routing Patterns

### 2.1 Route Mounting (`main.py`)
In `backend/main.py`:
- `auth_router` is mounted at prefix `/api/v1`
- `api_router` is mounted at prefix `/api/v1`
- Base endpoints:
  - `GET /` — API root status
  - `GET /health` — Health check (`{"status": "ok", "service": "industrial-mind-os-core"}`)

### 2.2 Endpoint Catalog
| Method | Path | Summary & Responsibilities | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | User registration (derives unique username from email) | No |
| `POST` | `/api/v1/auth/login` | OAuth2 password form login; returns bearer JWT token | No |
| `GET` | `/api/v1/auth/me` | Returns current user info (`id`, `email`, `username`) | Yes (`get_current_user`) |
| `POST` | `/api/v1/upload` | File upload (PDF, TXT, DOCX, PPTX, CSV, PNG/JPG OCR). Dual-path: <15K chars to `memory_cache`, >=15K to semantic chunking + Qdrant. Both update graph and trigger background immune scan. | Yes |
| `POST` | `/api/v1/query` | Triggers LangGraph multi-agent RAG workflow (Private / Hybrid / Online modes). Runs in `run_in_threadpool`. | Yes |
| `GET` | `/api/v1/documents` | Combined deduplicated list of user's files from `memory_cache` + `vector_db`. | Yes |
| `DELETE` | `/api/v1/documents/{filename}` | Atomic cleanup across `vector_db`, `memory_cache`, and `graph_db`. Returns 404 if 0 items removed. | Yes |
| `GET` | `/api/v1/alerts` | Lists proactive immune system alerts (`macrophage.py`) for calling user. | Yes |
| `DELETE` | `/api/v1/alerts/{alert_id}` | Dismisses a specific alert. | Yes |
| `GET` | `/api/v1/graph/data` | D3/force-directed graph JSON (`nodes`, `links`), capped at top 300 nodes by degree. | Yes |
| `GET` | `/api/v1/graph/stats` | Debug endpoint: node count, edge count, sample nodes/edges, memory cache stats. | Yes |
| `GET` | `/api/v1/suggestions` | Dynamic query suggestions templated from random graph entities. | Yes |
| `POST` | `/api/v1/confluence/sync` | Syncs Confluence space pages via REST API, converts to markdown, feeds to ingestion. | Yes |

### 2.3 Security Invariants
1. **User Scoping**: Every internal store call passes `owner_id=current_user["id"]`.
2. **Legacy Tolerance**: Records with `owner_id=None` remain globally visible so migrations don't break existing demo data.
3. **No Secret Leakage**: `JWT_SECRET_KEY` is strictly required at startup (fails loudly if unset).

---

## 3. Data Stores & Knowledge Representation

Industrial Mind OS uses an embedded, local-first data architecture without external database servers:

### 3.1 Vector Database (`storage/vector_db.py`)
- **Backend**: Qdrant running in local disk mode (`backend/qdrant_data/`).
- **Collection**: `imos_collection` with 384-dimension vectors (Cosine distance).
- **Embedder**: `core/embeddings.py` (`all-MiniLM-L6-v2` via `sentence-transformers` on CPU).
- **Locking Caveat**: Local disk mode acquires an exclusive file lock on `backend/qdrant_data/`. When a backend server is running, any second process attempting to instantiate `QdrantClient(path=...)` fails with an `AlreadyLocked` error.

### 3.2 Knowledge Graph (`storage/graph_db.py`)
- **Backend**: NetworkX `MultiDiGraph` serialized to `backend/graph_db.json`.
- **Relationship Type**: Directed `co-occurs-with` edges between extracted keywords (words >= 4 chars, stopwords stripped).
- **Metadata**: Each edge stores `{"source": filename, "owner_id": owner_id, "relation": "co-occurs-with"}`.
- **Traversal**: `get_context_for_entity(entity, depth=2, file_filter=..., owner_id=...)` conducts an outward BFS over edges, filtered by user ownership and file allowlists.
- **Batching**: Saving is deferred (`autosave=False`) during bulk ingestion to prevent $O(n^2)$ serialization overhead.

### 3.3 Direct Memory Cache (`storage/memory_cache.py`)
- **Backend**: JSON dictionary serialized to `backend/memory_cache.json`.
- **Purpose**: Fast, embedding-free retrieval for files smaller than 15,000 characters. Small documents are stored verbatim and retrieved in full as context.

### 3.4 Proactive Alerts (`immune/macrophage.py`)
- **Backend**: JSON list serialized to `backend/alerts.json`.
- **Purpose**: Captures contradictions, compliance gaps, and historical pattern matches detected by Gemini during document ingestion.

### 3.5 SQL Relational Database (`db/database.py`, `db/models.py`)
- **Backend**: SQLite (`industrial_mind_os.db`).
- **Tables**: `users` table (`id`, `username`, `email`, `hashed_password`, `created_at`).

---

## 4. Location and Modeling of Asset Manuals, Telemetry, & Incident Data

### 4.1 Existing Data & Assets
- **Root Sample**: `Near_Miss_Report_2023.txt` (1,458 bytes).
  - Describes a critical incident for **Pump-A12** (Primary Cooling Loop, Sector 4).
  - Catastrophic mechanical seal failure following 48 hours of sustained vibration at **5.8 mm/s**.
  - OEM limit is **5.0 mm/s**; mandatory shutdown protocol at **> 5.5 mm/s**.
  - Technicians incorrectly assumed the threshold was 6.5 mm/s.
- **Ingestion Pipeline for CSVs**:
  - `POST /api/v1/upload` reads `.csv` files row-by-row and converts each row into a structured record string (`[Record N] Col: val | ...`). This is how telemetry logs and maintenance spreadsheets are currently handled.

### 4.2 Current Modeling Gaps for RCA / 8D Studio
Currently, the codebase lacks structured domain models for:
1. **Equipment Entities**: No schema defining equipment tag, serial number, equipment class/type, location, critical operating envelopes (e.g. vibration threshold, temperature range, pressure max), or associated OEM manual filenames.
2. **Failure Symptoms & Incidents**: No structured schema for incident reports (symptom description, timestamp, telemetry readings, observed conditions).
3. **8D Disciplines**: No schema representing D1 (Team), D2 (Problem Description), D3 (Interim Containment), D4 (Root Cause Analysis with 5-Why & Ishikawa), D5 (Corrective Actions), D6 (Validation), D7 (Preventive Actions), D8 (Team Recognition).
4. **Verifiable Citations**: No normalized schema mapping causal assertions to citation IDs, source files, and evidentiary snippets.

---

## 5. Recommended API Architecture for RCA & 8D Studio

To satisfy R1-R4 and the automated backend verification acceptance criteria, we recommend structuring the RCA subsystem as follows:

### 5.1 New Dedicated Router & Endpoints (`api/rca_router.py`)
Mount under `/api/v1/rca`:

1. `POST /api/v1/rca/analyze`:
   - **Input**: `RCAIncidentRequest` containing `equipment_tag`, `incident_timestamp`, `failure_symptoms`, `telemetry_data` (optional key-value metrics like `{"vibration": 5.8, "temperature": 82}`), and `selected_files`.
   - **Action**:
     - Extracts incident evidence & builds a chronological failure timeline (R1).
     - Traverses knowledge graph and manuals to establish OEM limits vs observed values.
     - Runs the deductive 5-Why and Ishikawa (Fishbone) analysis engine (R2).
     - Matches symptoms against historical records (e.g. `Near_Miss_Report_2023.txt`) and OEM operating envelopes (R4).
     - Flags any unsubstantiated assumptions where citations are absent.
     - Assembles the complete Eight Disciplines (8D) report.
   - **Output**: `EightDReportResponse` conforming strictly to the structured Pydantic schema.

2. `POST /api/v1/rca/historical-match`:
   - Dedicated endpoint to search for similar past incidents, near-misses, and OEM envelope violations for an equipment tag or symptom list.

3. `POST /api/v1/rca/export-evidence`:
   - Generates a certified, timestamped compliance evidence package (self-contained HTML and downloadable payload) with complete audit trail, evidence citations, and formal 8D certification metadata.

4. `GET /api/v1/rca/reports`:
   - Retrieves previously generated or saved 8D reports scoped to `owner_id`.

### 5.2 Pydantic Schema Architecture (`api/rca_schemas.py`)
```python
class CitationObject(BaseModel):
    citation_id: str
    source_document: str
    snippet: str
    relevance_score: float
    verified: bool = True

class TimelineEvent(BaseModel):
    timestamp: str
    event_description: str
    parameter_name: Optional[str] = None
    observed_value: Optional[float] = None
    threshold_limit: Optional[float] = None
    severity: str  # NORMAL, WARNING, CRITICAL
    citation_id: Optional[str] = None

class FiveWhyNode(BaseModel):
    level: int  # 1 to 5
    question: str
    answer: str
    is_root_cause: bool = False
    is_assumption: bool = False
    citation_id: Optional[str] = None

class IshikawaCategory(BaseModel):
    category: str  # Machine, Method, Material, Manpower, Measurement, Milieu/Environment
    factors: List[str]
    citations: List[str] = []

class D1Team(BaseModel):
    champion: str
    leader: str
    members: List[str]

class D2ProblemDescription(BaseModel):
    what: str
    where: str
    when: str
    magnitude: str
    equipment_tag: str

class D3InterimContainment(BaseModel):
    actions: List[str]
    verification_status: str

class D4RootCauseAnalysis(BaseModel):
    timeline: List[TimelineEvent]
    five_whys: List[FiveWhyNode]
    ishikawa: List[IshikawaCategory]
    direct_cause: str
    contributing_causes: List[str]
    root_cause_statement: str
    unsubstantiated_assumptions: List[str] = []

class D5CorrectiveActions(BaseModel):
    actions: List[str]
    target_dates: List[str]
    responsible_parties: List[str]

class D6ValidationResults(BaseModel):
    validation_method: str
    results_summary: str
    confirmed_effective: bool

class D7PreventativeActions(BaseModel):
    pm_updates: List[str]
    oem_envelope_controls: List[str]
    training_and_sop: List[str]

class D8TeamRecognition(BaseModel):
    acknowledgments: str
    closure_date: str

class EightDReport(BaseModel):
    report_id: str
    equipment_tag: str
    created_at: str
    severity_score: float  # e.g. 1.0 to 10.0
    d1_team: D1Team
    d2_problem: D2ProblemDescription
    d3_containment: D3InterimContainment
    d4_root_cause: D4RootCauseAnalysis
    d5_corrective_actions: D5CorrectiveActions
    d6_validation: D6ValidationResults
    d7_preventive_actions: D7PreventativeActions
    d8_team_recognition: D8TeamRecognition
    citations: List[CitationObject]
    historical_matches: List[dict] = []
    compliance_certified: bool = True
```

---

## 6. Test Runner, Pytest Structure & Testing Seams

### 6.1 Test Infrastructure
- **Test Runner**: Pytest `9.1.1` via `backend/venv/Scripts/pytest.exe`.
- **Configuration**: `backend/pytest.ini`
  ```ini
  [pytest]
  testpaths = tests
  pythonpath = .
  ```
- **Execution Command**:
  ```bash
  cd backend
  .\venv\Scripts\pytest.exe
  ```
- **Current Test Status**: **27 passing in 0.50 seconds** (100% pass rate).

### 6.2 Existing Test Seams & Invariants
`CLAUDE.md` explicitly warns:
> *"The suite is deliberately built out of seams that need no LLM, no network and no Qdrant lock... anything that imports agents/orchestrator.py or api/router.py transitively boots the Qdrant local client and takes the qdrant_data/ lock, which fails if a backend is already running."*

### 6.3 RCA Testing Seam Strategy
To ensure that backend pytest verification passes with 100% success rate without taking the Qdrant lock or requiring an external LLM API key:
1. **Decouple the Core Engine Logic**: Implement the RCA deductive reasoning, 5-Why chain generator, Ishikawa classifier, timeline builder, historical matcher, and schema validator as pure/injectable services (e.g. `services/rca_engine.py` or `rca/engine.py`).
2. **Injectable Retrieval & Knowledge Sources**: Accept an abstract or mockable knowledge provider (mock manuals, mock historical near-misses, mock graph context).
3. **Unit & Integration Suite (`tests/test_rca_engine.py`, `tests/test_rca_endpoints.py`)**:
   - Test schema conformance (all 8D sections, severity score, citations present and strictly validated).
   - Test 5-Why generation logic (direct cause -> intermediate contributing -> root cause).
   - Test Ishikawa 6M categorization (Machine, Method, Material, Manpower, Measurement, Milieu).
   - Test assumption flagging (claims without citation IDs are flagged in `unsubstantiated_assumptions`).
   - Test historical matching (e.g. matching 5.8 mm/s against `Near_Miss_Report_2023.txt` threshold).
   - Test FastAPI endpoint execution using FastAPI `TestClient` with mocked dependencies.

---

## 7. Installed Dependencies Audit

All necessary dependencies are already installed in `backend/venv`:
- `fastapi==0.141.1`
- `pydantic==2.13.4`, `pydantic-settings==2.15.0`
- `networkx==3.6.1`
- `qdrant-client==1.19.0`
- `langgraph==1.2.11`
- `langchain-core==1.6.0`, `langchain-google-genai==4.3.6`
- `sentence-transformers==6.1.0`
- `sqlalchemy==2.0.52`
- `python-jose==3.5.0`, `passlib==1.7.4`, `bcrypt==3.2.2`
- `pytest==9.1.1`, `anyio==4.14.2`
- `jinja2==3.1.6` (ideal for certified HTML report templating)
- `numpy==2.4.6`, `scipy==1.17.1`, `scikit-learn==1.9.1`

No additional external library installations are strictly required to build the complete RCA & 8D Studio backend.

---

## 8. Summary of Findings & Next Steps

1. **Backend Foundation**: The existing FastAPI architecture is clean, highly modular, and fully functional.
2. **Data & Knowledge Assets**: Unstructured data ingestion and graph co-occurrence exist, but structured models for equipment tags, telemetry envelopes, failure symptoms, and 8D reports must be created.
3. **Testing Health**: Current tests pass completely in 0.5s; all new RCA tests must follow the established offline, lock-free seam pattern.
4. **Actionable Implementation Path**:
   - Define Pydantic 8D schemas (`api/rca_schemas.py`).
   - Implement the deductive RCA engine, timeline builder, 5-Why & Ishikawa analyzer, and historical matcher (`services/rca_engine.py`).
   - Mount new endpoints in `api/rca_router.py` (or `api/router.py`) and wire to `main.py`.
   - Add comprehensive offline pytest tests in `tests/test_rca_engine.py` and `tests/test_rca_api.py`.
