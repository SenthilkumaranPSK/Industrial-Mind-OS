## 2026-10-05T13:52:01Z
You are the Backend Schemas & Ingestion Implementer (Worker) for Milestone 1.
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m1

MANDATORY FIRST STEP:
Read the authoritative user request at:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md

Also read the architecture and blueprints prepared by the Explorers:
1. Master Project Plan: C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\orchestrator_1\PROJECT.md
2. Schemas Blueprint: C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m1_schemas\analysis.md
3. Timeline Blueprint: C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m1_timeline\analysis.md
4. Citations Blueprint: C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m1_citations\analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE FILE OWNERSHIP:
You exclusively own and may create/modify only these files:
- `backend/api/rca_schemas.py`
- `backend/services/rca_ingestion.py`
- `backend/tests/test_rca_schemas.py`
- `backend/tests/test_rca_ingestion.py`
Do NOT edit any other project files.

Your Tasks:
1. Implement `backend/api/rca_schemas.py`:
   - All 17 Pydantic v2 domain models: `CitationObject`, `TimelineEvent`, `FiveWhyNode`, `FishboneBranch`, `FishboneAnalysis`, `HistoricalMatch`, `OEMDeviation`, `ContainmentAction`, `CorrectiveAction`, `PreventativeControls`, `ValidationPlan`, `TeamFormation`, `ProblemDescription`, `EightDIncidentReport`, `RCAAnalyzeRequest`, `ExportEvidenceRequest`, `ExportEvidenceResponse`.
   - Validators for RPN calculation (Severity * Occurrence * Detection), severity score ranges (1-10), ISO 8601 parsing, division-by-zero protection on OEM deviation percentages, SHA-256 canonical digest computation and tamper verification methods (`compute_canonical_sha256()`, `verify_checksum()`).
2. Implement `backend/services/rca_ingestion.py`:
   - `TimelineExtractor`: Parses timestamps, extracts telemetry readings (vibration, temperature, pressure, RPM), computes deviations against OEM envelopes (including Pump-A12 baseline: 5.8 mm/s vs 5.0 mm/s limit, trip threshold 5.5 mm/s), classifies event types (`TELEMETRY_ALARM`, `OPERATOR_ACTION`, `SYSTEM_FAILURE`, `MAINTENANCE_LOG`), and builds chronological event logs.
   - `CitationRegistry`: In-memory thread-safe citation store with deduplication and deterministic citation IDs (`CITE-{SLUG}-{SEQ:03d}`).
   - `EvidenceCitationExtractor`: Multi-modal source document traversal across `Near_Miss_Report_2023.txt`, memory cache, and uploaded documents to extract citation objects with exact text excerpts, line/section info, and confidence scores.
   - `verify_causal_grounding`: Analyzes causal nodes, checks citation references against the registry, computes Citation Grounding Ratio (CGR), and automatically flags ungrounded assertions (`is_unsubstantiated=True`, `assumption_flag=True`).
3. Implement `backend/tests/test_rca_schemas.py`:
   - 40+ comprehensive unit tests covering all models, validation errors, boundary conditions, RPN calculations, and SHA-256 tamper detection.
4. Implement `backend/tests/test_rca_ingestion.py`:
   - 25+ comprehensive unit tests covering chronological sorting, out-of-order logs, telemetry deviation calculations, Near_Miss_Report_2023.txt parsing, citation indexing, excerpt retrieval, and assumption flagging.
5. Verification:
   - Run tests using `backend/venv/Scripts/pytest.exe` (or `python -m pytest` in `backend/`).
   - Ensure all new tests pass 100% and the existing 27 regression tests also pass without errors.
   - Confirm all tests run offline without network or Qdrant lock collisions.
6. Write your progress to `progress.md` and complete handoff report to `handoff.md` in your working directory.
7. Send a completion message to the orchestrator via `send_message`.
