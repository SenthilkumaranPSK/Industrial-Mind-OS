## 2026-10-06T07:04:53Z
You are the Deductive RCA & Preventative Engine Implementer (Worker) for Milestone 2.
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m2

MANDATORY FIRST STEP:
Read the authoritative user request at:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md

Also read the master plan and blueprints prepared by the Explorers:
1. Master Project Plan: C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\orchestrator_1\PROJECT.md
2. 5-Why & Ishikawa Blueprint: C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m2_five_why_ishikawa\analysis.md
3. Historical Matching Blueprint: C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m2_historical_matching\analysis.md
4. OEM & Preventative Blueprint: C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m2_oem_preventative\analysis.md
5. Existing M1 Schemas & Ingestion:
   - `C:\000 MINE\My Codzz\Industrial Mind OS\backend\api\rca_schemas.py`
   - `C:\000 MINE\My Codzz\Industrial Mind OS\backend\services\rca_ingestion.py`
   - `C:\000 MINE\My Codzz\Industrial Mind OS\Near_Miss_Report_2023.txt`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE FILE OWNERSHIP:
You exclusively own and may create/modify only these files:
- `backend/services/rca_engine.py`
- `backend/tests/test_rca_engine.py`
Do NOT edit any other project files.

Your Tasks:
1. Implement `backend/services/rca_engine.py`:
   - `DeductiveRCAEngine` (or corresponding modular classes `FiveWhyGenerator`, `IshikawaClassifier`, `HistoricalMatcher`, `OEMEnvelopeAnalyzer`, `EightDReportAssembler`):
     * 5-Why Recursive Causal Tree: Multi-stage reasoning decomposing symptoms into direct, contributing, and root causes (Levels 1 to 5). Distinguishes between Occurrence Root Cause and Escape / Non-Detection Root Cause. Grounded in `CitationRegistry`, with automatic assumption flagging (`is_unsubstantiated=True`, `assumed_flag=True`) on ungrounded assertions.
     * Ishikawa 6M Fishbone: Classifies causal factors across standard 6M categories: Man, Machine, Material, Method, Measurement, Environment, with citation linking and contribution weights.
     * Historical Near-Miss Matching: Cross-references incidents against `Near_Miss_Report_2023.txt` (Pump-A12 vibration excursion baseline: 5.8 mm/s vs 5.0 mm/s limit, trip threshold 5.5 mm/s, sister assets Pump-A11, Pump-A13). Uses multi-factor similarity scoring (equipment family match, symptom token overlap, parameter excursions) and recurrence risk assessment.
     * OEM Operating Envelope Deviation: Computes `deviation_percent = ((actual - limit) / limit) * 100.0` with division-by-zero protection. Stratifies into NORMAL, WARNING, HIGH, CRITICAL.
     * Preventative Maintenance & Controls Generator: Recommends actionable updates across 4 pillars: SOP Updates, PM Schedule Updates, FMEA Risk Matrix updates (calculating initial vs mitigated target RPN, e.g. 336 down to 16, >90% reduction), and Horizontal Deployment across sister assets.
     * Master 8D Assembler: Synthesizes complete `EightDIncidentReport` conforming strictly to `rca_schemas.py` with canonical SHA-256 seal.
2. Implement `backend/tests/test_rca_engine.py`:
   - Comprehensive unit test suite (35+ test cases) covering all engine capabilities, 5-Why trees, Ishikawa classifications, historical matching against Near_Miss_Report_2023.txt, OEM deviation math, preventative action generation, and full 8D report generation.
3. Verification:
   - Run tests using `backend/venv/Scripts/pytest.exe` (or `python -m pytest` in `backend/`).
   - Ensure all new tests pass 100% and all existing 371 tests also pass without errors or regressions.
   - Confirm all tests run offline without network or Qdrant lock collisions.
4. Write your progress to `progress.md` and complete handoff report to `handoff.md` in your working directory.
5. Send a completion message to the orchestrator via `send_message`.
