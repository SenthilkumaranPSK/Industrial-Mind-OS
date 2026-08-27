# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Industrial Mind OS is an Industrial Knowledge Intelligence platform: a multi-agent RAG system that ingests industrial documents (PDF/DOCX/PPTX/CSV/TXT/images) and answers engineer questions via a LangGraph agentic pipeline, backed by a vector DB, a keyword graph, and a proactive "immune system" that scans new uploads for conflicts against existing knowledge.

Two independent apps in one repo, no shared tooling/monorepo config:
- `backend/` — FastAPI + LangGraph (Python)
- `frontend/` — React + Vite (JS)

There are no automated tests in this repo (no test files, no test runner configured).

## Commands

### Backend (from `backend/`)
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Requires a `.env` in `backend/` (copy `backend/.env.example` — see Environment variables below).

### Frontend (from `frontend/`)
```bash
npm install
npm run dev       # Vite dev server
npm run build
npm run preview
```
No `lint` or `test` script is defined in `package.json`.

## Environment variables (backend)

Required:
- `ANTHROPIC_API_KEY` — powers every LLM call (synthesis, planning/query-rephrasing, web-query refinement, image OCR, the immune-system auditor) via `langchain-anthropic`. Nothing in the agent pipeline works without it.
- `JWT_SECRET_KEY` — signs/verifies local auth JWTs (`core/security.py`). Falls back to a hardcoded dev default if unset — always set a real value outside local dev. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.

Optional (feature-gated, code degrades gracefully if absent):
- `TAVILY_API_KEY` — primary web search provider for Online/Hybrid mode.
- `FIRE_CRAWL_API_KEY` — secondary web search fallback if Tavily is unset/fails.
- If neither is set, web search falls back to `duckduckgo-search` (no key needed).

Frontend: `VITE_API_URL` (defaults to `http://localhost:8000` when unset — note a couple of fetch calls in `App.jsx` hardcode `localhost:8000` directly instead of using this var, so don't assume every call respects a custom `VITE_API_URL`).

## Architecture

### Data stores are all local/embedded — there is no external DB server to stand up
- **Vector DB**: `backend/storage/vector_db.py` — Qdrant client in **local disk-persisted mode** (`QdrantClient(path=...)`), storing to `backend/qdrant_data/`. Not a Qdrant server.
- **Graph DB**: `backend/storage/graph_db.py` — a NetworkX `MultiDiGraph` (not Neo4j, despite `neo4j` being in requirements.txt) serialized to `backend/graph_db.json` on every write.
- **Memory cache**: `backend/storage/memory_cache.py` — a plain dict serialized to `backend/memory_cache.json`. Small documents (<15,000 chars) are stored here directly and bypass vector embedding entirely ("direct injection").
- **Auth/users**: `backend/db/database.py` (SQLAlchemy engine, `industrial_mind_os.db`) + `db/models.py` (`User` table) is the auth store — local JWT auth, not Supabase. `main.py` calls `Base.metadata.create_all` on startup to create tables. Passwords are hashed with passlib/bcrypt and tokens signed with `python-jose` in `core/security.py`; `api/auth.py::get_current_user` decodes the bearer token and loads the `User` row per-request. Registration is email+password only — `username` is auto-derived from the email's local part (`_derive_username` in `api/auth.py`), with a numeric suffix on collision.

Because these stores are files/embedded processes, deleting a document must clean up three places in lockstep: `vector_db.delete_by_filename`, `memory_cache.delete_file`, `graph_db.delete_by_filename` (all wired together in `api/router.py`'s `DELETE /documents/{filename}`).

### Request flow
`main.py` mounts two routers under `/api/v1`: `api/auth.py` (`/auth/*` — register/login/`get_current_user`, backed by the local SQLite `User` table and JWTs, see Auth/users above) and `api/router.py` (everything else: upload, query, documents, alerts, graph, confluence sync).

### Ingestion (`POST /api/v1/upload` in `api/router.py`)
Per-extension text extraction happens inline in the route handler (not a shared parser abstraction):
- `csv` → manual `csv.reader`, one "[Record N] Col: val | ..." block per row
- `pptx` → `python-pptx`, shape text per slide
- `pdf` → `pypdf`, then `clean_spaced_text()` repairs the "s p a c e d   o u t" character-spacing artifact common in PDF extraction
- `docx` → `python-docx`, falls back to raw UTF-8 decode on failure
- `png`/`jpg`/`jpeg` → sent to `claude-sonnet-5` (vision) for OCR/structured extraction (requires `ANTHROPIC_API_KEY`)
- everything else → raw UTF-8 decode

Then: **<15,000 chars** → stored directly in `memory_cache` + graph keyword edges built (bypasses embedding/Qdrant), and the immune system's `scan_for_conflicts` runs as a background task. **>=15,000 chars** → chunked via `storage/ingestion.py`'s semantic splitter (splits on sentence boundaries, breaks a chunk when cosine similarity between consecutive sentence embeddings drops below 0.70, using the local HF embedder), embedded, upserted to Qdrant, and graph-populated — all in a `BackgroundTasks` job.

Graph population (`ingestion_pipeline.populate_graph`) is keyword co-occurrence, not entity extraction: it pulls stopword-filtered keywords (>=4 chars) per chunk and links adjacent keywords with a `co-occurs-with` edge tagged with the source filename. This is what `graph_db.get_context_for_entity` traverses at query time (a BFS over `MultiDiGraph`, filtered by `file_filter` when a chat has restricted its knowledge scope).

### Query pipeline — LangGraph agent (`backend/agents/orchestrator.py`)
A `StateGraph` with a shared `AgentState` TypedDict, wired as:
```
planner → adaptive_retrieval → web_search → memory_builder → synthesizer → verifier
                                                                              │
                                                              (confidence<60 & retry<2)
                                                                              ↓
                                                                           planner (loop)
```
- **planner**: rephrases multi-part/comparison queries into cleaner search keywords using the fast/cheap `claude-haiku-4-5-20251001` model (`FAST_MODEL` in `orchestrator.py`).
- **adaptive_retrieval**: pulls from `memory_cache`, Qdrant (`vector_context`), and the graph (`graph_context`) — all three are skipped entirely when `mode == "Online"`. Sets a human-readable `strategy` string surfaced to the frontend's Insight Panel.
- **web_search**: only runs for `mode in ("Online", "Hybrid")`. Provider order: Tavily → Firecrawl → DuckDuckGo, first success wins. Query refinement before search also uses the fast Claude model.
- **memory_builder**: concatenates all four context lists, dedupes by exact content match, builds `fused_context` and `citations`.
- **synthesizer**: calls the main `claude-sonnet-5` model (`SYNTHESIS_MODEL` — "the brain") with mode-specific strict instructions. It is expected to emit `[ARTIFACT: Name] <html>...</html> [/ARTIFACT]` blocks for comparisons/dashboards instead of markdown tables — the frontend (`ArtifactPanel.jsx` / `ChatMessage.jsx`) parses that marker.
- **verifier**: purely heuristic (no LLM call) confidence scoring based on bad-phrase detection, answer length, citation density (`[Source:` count), and markdown structure — feeds `should_loop`, which retries through `planner` at most once if confidence < 60.

`mode` is one of `"Private"` (internal docs only), `"Hybrid"` (internal + web), or `"Online"` (web only) — this string is threaded through nearly every node and changes both retrieval and the synthesis system prompt's strictness.

`files` on `AgentState` is a chat-scoped allowlist of filenames ("Document Gating") — when set, it filters both the Qdrant search (`file_filter` on `vector_db.search`) and the graph traversal (`file_filter` on `graph_db.get_context_for_entity`), so different chats can be scoped to different document subsets.

### Proactive Auditor / "Immune System" (`backend/immune/macrophage.py`)
Runs as a `BackgroundTasks` job triggered only on the direct-injection (small-file) upload path. Compares the new document's full text against everything currently in `memory_cache` via one LLM call, asking it to flag CONTRADICTION / COMPLIANCE GAP / HISTORICAL PATTERN, or reply `SAFE`. Non-safe results are appended to an in-process `immune_system.alerts` list (not persisted to disk — resets on backend restart) and surfaced via `GET /api/v1/alerts` / `DELETE /api/v1/alerts/{id}`, driving the frontend's notification bell.

### Confluence sync (`backend/core/confluence.py`)
`POST /api/v1/confluence/sync` pulls all pages from a Confluence Cloud space via REST API + basic auth (email + API token), converts HTML to markdown (`markdownify`), and feeds pages through the same ingestion pipeline as file uploads.

### Frontend structure
Single-page app — despite `react-router-dom` being a dependency and a `src/pages/` directory existing (`Home.jsx`, `Query.jsx`, `Upload.jsx`), no `<Router>`/`<Routes>` is actually wired up in `App.jsx`/`main.jsx`. All state (auth token, chats, messages, uploaded files, alerts, active artifact) lives in `App.jsx` via `useState` and is passed down as props; per-chat history is persisted to `localStorage` keyed by user email. Treat `src/pages/*` as effectively unused legacy code unless you're the one wiring up routing.

Auth token (`imos_token`) is stored in `localStorage` and sent as a Bearer token on every API call; the backend validates it locally by decoding the JWT and loading the user from SQLite (`api/auth.py::get_current_user`) — no external auth provider involved.

Key components: `ChatInterface.jsx`/`ChatMessage.jsx` (chat + `[ARTIFACT]` block rendering), `InsightPanel.jsx` (confidence/strategy/citations sidebar), `GraphVisualizer.jsx`/`MindMap.jsx` (`react-force-graph-2d` rendering of `GET /api/v1/graph/data`, server-capped at top 300 nodes by degree), `SourceSelectionModal.jsx` (per-chat document gating UI), `Sidebar.jsx` (file list + alerts bell). `components/Auth/AuthShell.jsx` holds the shared two-pane login/register layout (backdrop, pipeline diagram, feature grid, form card chrome); `Login.jsx`/`Register.jsx` supply only their form fields as children.
