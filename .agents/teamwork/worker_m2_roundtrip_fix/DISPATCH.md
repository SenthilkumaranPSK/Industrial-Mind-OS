## 2026-10-07T05:21:04Z
You are worker_m2_roundtrip_fix.
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m2_roundtrip_fix

Authoritative Request:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md

Master Project Plan:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\orchestrator_1\PROJECT.md

Reviewer Findings (REQUEST_CHANGES report):
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\reviewer_m2_recheck\handoff.md

Auditor Report (CLEAN report):
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\auditor_m2_recheck\handoff.md

Write Ownership:
You own exclusively:
- backend/services/rca_engine.py
- backend/tests/test_rca_engine.py
Do not modify any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Detailed Tasks:
1. Rebuild EightDIncidentReport in backend/services/rca_engine.py:
   At line ~181 where OEMDeviation and PreventativeControls are rebuilt with _patched_oem_compute_deviation, add:
   ```python
   EightDIncidentReport.__pydantic_complete__ = False
   EightDIncidentReport.model_rebuild(force=True)
   ```
   Verify that serializing an 8D report to JSON via model_dump_json() and deserializing via EightDIncidentReport.model_validate_json() preserves the lower-bound excursion (e.g. deviation_percent == +46.67%, SeverityLevel.CRITICAL) AND preserves the SHA-256 seal (reloaded.verify_checksum() is True).

2. General Asset Fallback Isolation in assemble_eight_d_report & IshikawaClassifier:
   In `backend/services/rca_engine.py`, when `family` is "General Rotating Asset" (or any uncataloged rotating asset like GEN-1 or COMP-01), do NOT default to centrifugal pump ceramic mechanical seal narratives in D2, D3, D5, D8 or IshikawaClassifier. Instead, provide generic rotating machinery failure narratives (e.g., dynamic unbalance, bearing fatigue / misalignment, lubrication breakdown) so non-pump assets never leak ceramic mechanical seal text.

3. Add Tests in backend/tests/test_rca_engine.py:
   - Test JSON roundtrip persistence: Verify an 8D incident report with a lower-bound deviation (e.g. TURB-ST-04 lube oil pressure 0.8 bar) survives `model_validate_json(rep.model_dump_json())`, retains deviation > 0, CRITICAL severity, and `reloaded.verify_checksum() is True`.
   - Test general rotating asset narrative isolation: Verify that an asset like `GEN-1` or `COMP-01` produces an 8D report without 'ceramic' in `d2_problem.what` or `d5_permanent_actions`.

4. Execute Tests:
   Run via powershell:
   - backend\venv\Scripts\pytest.exe backend/tests/test_rca_engine.py -v
   - backend\venv\Scripts\pytest.exe backend/tests/test_adversarial_m2_stress.py -v
   - backend\venv\Scripts\pytest.exe backend/tests/ -q
   Ensure 100% pass with 0 failures.

5. Deliverables:
   Write a comprehensive handoff report following the 5-component protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method) to:
   C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m2_roundtrip_fix\handoff.md
   Maintain progress.md in your directory.
   Notify orchestrator via send_message.
