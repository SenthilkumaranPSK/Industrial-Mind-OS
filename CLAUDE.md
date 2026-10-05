# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Industrial Mind OS is an Industrial Knowledge Intelligence platform: a multi-agent RAG system that ingests industrial documents (PDF/DOCX/PPTX/CSV/TXT/images) and answers engineer questions via a LangGraph agentic pipeline, backed by a vector DB, a keyword graph, and a proactive "immune system" that scans new uploads for conflicts against existing knowledge.

Two independent apps in one repo, no shared tooling/monorepo config:
- `backend/` — FastAPI + LangGraph (Python)
- `frontend/` — React + Vite (JS)

`README.md` is the product-facing overview and its stack section is current. It duplicates the setup steps and env-var list below — keep the two in sync when either changes.

## Commands

### Backend (from `backend/`)
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Requires a `.env` in `backend/` (copy `backend/.env.example` — see Environment variables below). The app **refuses to start without `JWT_SECRET_KEY`**; that's deliberate (see Security invariants).

Use a CPython 3.11 interpreter for `venv`. `bcrypt` is no longer hard-pinned, so newer interpreters are less likely to produce the silently-broken venv this repo used to hit, but 3.11 is what the existing `venv/` uses and what the deps are known-good on. If `pip install` reports success but `import bcrypt`/`passlib` then fails, the resolver quietly dropped them — check `venv/Scripts/python.exe --version`, delete `venv/` and recreate it by invoking the 3.11 `python.exe` directly by its full path (in Git Bash the `py -3.11` selector doesn't reliably reach the `py` launcher).

First backend start downloads the HuggingFace `all-MiniLM-L6-v2` embedding model (see Embeddings below) — expect a slow first run and a working network connection.

### Tests (from `backend/`)
```bash
pip install -r requirements-dev.txt
python -m pytest                        # whole suite
python -m pytest tests/test_scoping.py  # one file
python -m pytest -k "legacy"            # one test by name
```
`pytest.ini` sets `pythonpath = .` so tests import `core.*`/`storage.*` without installing the package. The suite is deliberately built out of seams that need no LLM, no network and no Qdrant lock: `core/text_utils.py`, `agents/verification.py`, the splitter (via an injected fake embedder), and the per-user scoping rules (via `tmp_path`-backed stores). **Keep it that way** — anything that imports `agents/orchestrator.py` or `api/router.py` transitively boots the Qdrant local client and takes the `qdrant_data/` lock, which fails if a backend is already running.

There is no frontend test runner and no `lint` script.

### Frontend (from `frontend/`)
```bash
npm install
npm run dev       # Vite dev server
npm run build
npm run preview
```

### Debugging endpoints
`GET /health`, `GET /docs` (Swagger), and `GET /api/v1/graph/stats` — the last dumps node/edge counts, sample edges and the memory-cache file list *for the calling user*, and is the fastest way to see what's actually indexed.

## Environment variables (backend)

Required — the app will not start or will not function without these:
- `GOOGLE_API_KEY` — powers every LLM call (synthesis, planning/query-rephrasing, web-query refinement, image OCR, the immune-system auditor) via `langchain-google-genai` (Gemini).
- `JWT_SECRET_KEY` — signs/verifies local auth JWTs. `core/security.py` raises at import time if it's missing.

Optional (feature-gated, code degrades gracefully if absent):
- `TAVILY_API_KEY` — primary web search provider for Online/Hybrid mode.
- `FIRE_CRAWL_API_KEY` — secondary web search fallback if Tavily is unset/fails.
- If neither is set, web search falls back to `duckduckgo-search` (no key needed).
- `CORS_ORIGINS` — comma-separated allowed browser origins. Defaults to the local Vite dev servers. Must be set when the frontend is deployed anywhere else.
- `MAX_UPLOAD_MB` — upload size ceiling, default 25.
- `QDRANT_URL` / `QDRANT_API_KEY` — switch Qdrant from local disk mode to a server (see below).

Frontend: `VITE_API_URL`. `src/api.js` exports the single `API_URL` const every component imports; there are no hardcoded origins anywhere else.

## Architecture

### Security invariants
Three rules the code now enforces; don't regress them.

1. **Every store is scoped by `owner_id`.** `vector_db.search`/`delete_by_filename`/`list_filenames`/`count_by_filename`, `memory_cache.get_context`/`list_files`/`delete_file`, `graph_db.get_context_for_entity`/`get_graph_data`/`delete_by_filename`/`get_random_entities`, and `immune_system.list_alerts`/`dismiss` all take an owner and filter on it. The API layer passes `current_user["id"]` into all of them. Adding a new read path means adding the owner filter too.
2. **Legacy un-owned data stays readable by everyone.** Rows written before scoping existed have `owner_id: None` (memory cache, graph edges) or no `user_id` key at all (Qdrant points). Every visibility check treats those as globally visible, so upgrading didn't orphan existing data. `DirectMemoryCache._load` logs a warning naming the legacy files. If you ever want strict isolation, that fallback is the thing to remove — deliberately, not by accident.
3. **No secrets or internals in HTTP responses.** Handlers log with `logger.exception` and return a generic `detail`. `JWT_SECRET_KEY` has no default. CORS origins are explicit (`allow_origins=["*"]` with `allow_credentials=True` is rejected by browsers anyway).

Ownership is enforced on delete by checking whether anything was actually removed: `DELETE /documents/{filename}` returns 404 when all three stores report zero removals, so "doesn't exist" and "belongs to someone else" are indistinguishable to the caller.

### Data stores are all local/embedded — there is no external DB server to stand up
- **Vector DB**: `backend/storage/vector_db.py` — Qdrant. Defaults to **local disk-persisted mode** (`QdrantClient(path=...)`) writing to `backend/qdrant_data/`, collection `imos_collection`. Local mode holds an **exclusive lock** on that directory, so only one backend process can run at a time; set `QDRANT_URL` to use a real server and lift that limit.
- **Graph DB**: `backend/storage/graph_db.py` — a NetworkX `MultiDiGraph` (not Neo4j) serialized to `backend/graph_db.json`.
- **Memory cache**: `backend/storage/memory_cache.py` — a dict of `{filename: {"content": str, "owner_id": str|None}}` serialized to `backend/memory_cache.json`. Small documents (<15,000 chars) live here and bypass vector embedding entirely ("direct injection").
- **Alerts**: `backend/alerts.json` — immune-system findings, persisted because they're the output of an expensive LLM call.
- **Auth/users**: `backend/db/database.py` (SQLAlchemy, `industrial_mind_os.db`) + `db/models.py` (`User`). `main.py` calls `Base.metadata.create_all` on startup. Passwords hashed with passlib/bcrypt, tokens signed with `python-jose` in `core/security.py`; `api/auth.py::get_current_user` decodes the bearer token and loads the `User` row per-request. Registration is email+password only — `username` is derived from the email's local part (`_derive_username`), with a numeric suffix on collision.

All of these files/directories are gitignored; deleting them resets state.

Deleting a document must clean up three places in lockstep — `vector_db.delete_by_filename`, `memory_cache.delete_file`, `graph_db.delete_by_filename` — all wired together in `DELETE /documents/{filename}`.

### Graph writes must be batched
`graph_db.add_relationship(..., autosave=True)` serializes the **entire** graph to JSON on every call. Bulk paths pass `autosave=False` and call `graph_db.save()` once at the end (`ingestion_pipeline.populate_graph` does this). Per-edge saving is what forced the old 100-chunk indexing cap; if you add a bulk write path, batch it the same way or you'll reintroduce quadratic ingest.

### Embeddings
`core/embeddings.py::LocalEmbedder` is a lazy singleton wrapping HuggingFace `all-MiniLM-L6-v2`, run **locally on CPU** — embeddings never hit an API. Its 384 dimensions are hardcoded as the Qdrant collection's `vector_size`, so swapping the model requires deleting `backend/qdrant_data/` and re-ingesting. The same embedder serves chunk embedding and the splitter's similarity check.

### Request flow
`main.py` mounts two routers under `/api/v1`: `api/auth.py` (`/auth/*`) and `api/router.py` (`/upload`, `/query`, `/documents`, `/alerts`, `/graph/data`, `/graph/stats`, `/suggestions`, `/confluence/sync`).

The LangGraph pipeline and the vision OCR call are synchronous and slow, so the handlers wrap them in `run_in_threadpool` rather than calling them inline — doing otherwise blocks the event loop for every other request, including `/health`.

### Ingestion (`POST /api/v1/upload`)
Uploads are read fully into memory and rejected above `MAX_UPLOAD_MB`. Per-extension extraction happens inline in the route handler (not a shared parser abstraction):
- `csv` → manual `csv.reader`, one "[Record N] Col: val | ..." block per row
- `pptx` → `python-pptx`, shape text per slide
- `pdf` → `pypdf`, then `core/text_utils.clean_spaced_text()` repairs the "s p a c e d   o u t" artifact. That regex is word-boundary anchored on purpose: an unanchored version eats the previous word's last letter and glues on the next word.
- `docx` → `python-docx`, falls back to raw UTF-8 decode on failure
- `png`/`jpg`/`jpeg` → `gemini-2.5-pro` vision OCR (requires `GOOGLE_API_KEY`)
- everything else → raw UTF-8 decode

Then `DIRECT_INJECTION_THRESHOLD` (15,000 chars) splits the paths:
- **< threshold** → stored in `memory_cache`, graph edges built synchronously, immune scan queued as a background task.
- **>= threshold** → chunked by `storage/ingestion.py`'s semantic splitter (sentence boundaries; breaks when cosine similarity between consecutive sentence embeddings drops below 0.70), embedded, upserted to Qdrant, graph-populated, then immune-scanned — all in a `BackgroundTasks` job.

Both paths **replace** on re-upload: stale vectors and graph edges for that filename+owner are deleted before re-indexing, so uploading the same file twice doesn't double-count it at retrieval.

`populate_graph` indexes every chunk by default. It accepts `max_chunks` for callers that want a ceiling, and logs a warning naming exactly what it skipped — silent truncation here reads as full coverage when it isn't. Graph population is keyword co-occurrence, not entity extraction: stopword-filtered keywords (>=4 chars, 20 per chunk) linked by `co-occurs-with` edges tagged with source filename and owner.

`GET /documents` pages through the whole Qdrant collection via `list_filenames`. It must keep paginating: a single large document can exceed any one page of *points* and would otherwise hide every other file.

### Query pipeline — LangGraph agent (`backend/agents/orchestrator.py`)
```
planner → adaptive_retrieval → web_search → memory_builder → synthesizer → verifier
                                                                              │
                                                              (confidence<60 & retry<2)
                                                                              ↓
                                                                           planner (loop)
```
- **planner**: rephrases multi-part/comparison queries using the fast/cheap `gemini-2.5-flash` (`FAST_MODEL`).
- **adaptive_retrieval**: pulls from `memory_cache`, Qdrant, and the graph — all three skipped when `mode == "Online"`, all three scoped by `owner_id` and by the chat's `files` allowlist. Sets the `strategy` string shown in the Insight Panel.
- **web_search**: only for `mode in ("Online", "Hybrid")`. Tavily → Firecrawl → DuckDuckGo, first success wins.
- **memory_builder**: concatenates all four context lists, dedupes by exact content, builds `fused_context` and `citations`.
- **synthesizer**: `gemini-2.5-pro` (`SYNTHESIS_MODEL`) with mode-specific strict instructions. Expected to emit `[ARTIFACT: Name] <html>...</html> [/ARTIFACT]` blocks for comparisons/dashboards instead of markdown tables.
- **verifier**: no LLM call. Delegates to `agents/verification.py::score_answer` (pure function, unit-tested) which scores on refusal phrases, length, `[Source:` density and markdown structure. Feeds `should_loop`, which retries through `planner` once if confidence < 60.

`mode` is `"Private"` / `"Hybrid"` / `"Online"` and is threaded through nearly every node, changing both retrieval and synthesis prompt strictness. `POST /query` post-processes `sources` per mode (Online drops anything without a `Web:` prefix; each mode has its own "nothing found" label).

`files` on `AgentState` is the chat-scoped filename allowlist ("Document Gating"); `owner_id` is the user scope. Both filter all three internal stores.

### Proactive Auditor / "Immune System" (`backend/immune/macrophage.py`)
Compares a newly ingested document against that user's `memory_cache` contents in one LLM call, flagging CONTRADICTION / COMPLIANCE GAP / HISTORICAL PATTERN or replying `SAFE`. Runs on **both** upload paths. Inputs are bounded (`MAX_EXISTING_KNOWLEDGE_CHARS`, `MAX_NEW_DOC_CHARS`) so a large knowledge base can't blow the context window, and the document is excluded from its own comparison set. Findings persist to `alerts.json` and surface via `GET /alerts` / `DELETE /alerts/{id}`, driving the notification bell.

### Confluence sync (`backend/core/confluence.py`)
`POST /api/v1/confluence/sync` pulls all pages from a Confluence Cloud space (REST + basic auth), converts HTML to markdown (`markdownify`), and feeds pages through the same ingestion pipeline as uploads, stamped with the syncing user's id.

### Frontend structure
Single-page app. All state (auth token, chats, messages, uploaded files, alerts, active artifact) lives in `App.jsx` via `useState` and is passed down as props; per-chat history persists to `localStorage` keyed by user email (`imos_chats_<email>`, `imos_current_chat_<email>`). The auth token is `imos_token`, sent as a Bearer token on every call.

**Cleaned dead code**: Unused prototype pages (`src/pages/*`), `Hero.jsx`, `Layout.jsx`, `ChatMessage.jsx`, and the unused `react-router-dom` dependency have been removed.

Key components: `ChatInterface.jsx` (message list; strips `[ARTIFACT]` blocks from previews; owns the print-to-PDF audit export) and `ChatMessage.jsx` (bubble chrome + collapsible agent thought-process viewer); `MarkdownRenderer.jsx` owns the `[ARTIFACT: …][/ARTIFACT]` regex extraction and hands blocks to `ArtifactPanel.jsx`, which sniffs html/code/table type; `InsightPanel.jsx` (confidence/strategy/citations); `GraphVisualizer.jsx`/`MindMap.jsx` (`react-force-graph-2d` over `GET /graph/data`, server-capped at top 300 nodes by degree — the response carries `total_nodes` and `capped` so the UI can say so); `SourceSelectionModal.jsx` (document gating UI); `Sidebar.jsx` (file list + alerts bell). `components/Auth/AuthShell.jsx` holds the shared two-pane login/register layout; `Login.jsx`/`Register.jsx` supply only their form fields as children.
