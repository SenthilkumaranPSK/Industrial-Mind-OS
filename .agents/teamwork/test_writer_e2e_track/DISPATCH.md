## 2026-10-05T13:41:54Z
You are the E2E Test Suite Writer for the Automated Root Cause Analysis (RCA) & 8D Incident Report Studio.
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\test_writer_e2e_track

MANDATORY FIRST STEP:
Read:
1. C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md
2. C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\orchestrator_1\PROJECT.md
3. C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\spec_miner_survey_domain_2\spec_report.md

Your Objective:
Design and build the comprehensive opaque-box E2E test suite (Tiers 1-4) in accordance with the E2E Testing Track principles in PROJECT.md:
1. Create `TEST_INFRA.md` at project root documenting test architecture, runner commands, test case inventory, and coverage thresholds.
2. In directory `backend/tests/e2e_rca/` (or `tests/e2e_rca/` with proper pytest integration):
   - `conftest.py`: Fixtures for sample industrial equipment reports, telemetry logs, maintenance logs, and mock data.
   - `test_tier1_feature_coverage.py`: Feature coverage (>=5 test cases per feature for features F1 through F10).
   - `test_tier2_boundary_corner.py`: Boundary and corner cases (>=5 test cases per feature: empty inputs, extreme telemetry deviations, zero citations, malformed timestamps, maximum RPN values).
   - `test_tier3_cross_feature.py`: Cross-feature combinations and pairwise integration tests (combining timeline extraction with 5-Why reasoning, OEM envelope deviation with preventative actions, 8D generation with compliance export).
   - `test_tier4_real_world_scenarios.py`: Realistic industrial incident scenarios:
     * Scenario 1: Pump-A12 vibration anomaly and inboard ceramic seal failure (grounded in `Near_Miss_Report_2023.txt`).
     * Scenario 2: High-pressure steam turbine overspeed trip with lubrication failure.
     * Scenario 3: Industrial boiler thermal runaway due to thermocouple calibration drift.
3. Verify the tests execute cleanly via `pytest` (using `backend/venv/Scripts/pytest.exe` or `python -m pytest`). All tests MUST run completely offline without external network or Google Gemini API dependencies, and without locking `backend/qdrant_data/`.
4. When the test suite is complete and verified, create `TEST_READY.md` at project root summarising runner commands and coverage metrics per the template in PROJECT.md.
5. Write your handoff report to `handoff.md` in your working directory and notify the orchestrator via `send_message`.
