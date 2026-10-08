## 2026-10-06T07:28:30Z

You are the Remediation Implementer (Worker) for Milestone 2.
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m2_remediation

MANDATORY FIRST STEP:
Read:
1. C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md
2. C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\reviewer_m2_1\handoff.md
3. C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\challenger_m2_2\handoff.md
4. C:\000 MINE\My Codzz\Industrial Mind OS\backend\services\rca_engine.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE FILE OWNERSHIP:
You exclusively own and may edit only these files:
- `backend/services/rca_engine.py`
- `backend/tests/test_rca_engine.py`

Your Tasks:
Implement the 5 specific remediations demanded by Reviewer 1 in `reviewer_m2_1/handoff.md` (and address Challenger 2's edge cases):
1. Remediation 1: Dynamic 5-Why Causal Tree Construction in `FiveWhyTreeBuilder.build_tree`:
   - Replace the static 5-node Pump-A12 ceramic seal instantiation with dynamic causal synthesis.
   - Detect the asset family (e.g. Pump, Turbine, Boiler, Motor, Compressor) from `asset_tag` or symptoms/telemetry.
   - Synthesize Level 1 (observed symptom), Level 2 (component failure), Level 3 (process deviation), Level 4 (monitoring/alarm gap), Level 5 (systemic threshold/interlock defect) dynamically using the actual asset, symptoms, and telemetry excursions.
   - Support non-pump assets (e.g., steam turbine `TURB-ST-04` overspeed/bearing temperature, industrial boiler `BLR-HP-101` thermal runaway/thermocouple drift) authentically.
2. Remediation 2: Dynamic Keyword-Based Ishikawa 6M Classifier:
   - Activate and use the `KEYWORDS` dictionary in `IshikawaClassifier.classify_causes`.
   - Route and synthesize causes across Man, Machine, Material, Method, Measurement, and Environment based on keyword matching against symptoms, telemetry, and asset context, rather than returning a static Pump-A12 dictionary.
3. Remediation 3: Dynamic Preventative Controls & Sister Asset Resolution in `generate_preventative_controls`:
   - Resolve sister assets dynamically based on equipment family or naming prefix (e.g. `TURB-ST-04` -> sister assets `TURB-ST-01`, `TURB-ST-02`; `BLR-HP-101` -> `BLR-HP-102`, `BLR-HP-103`). Do NOT default unrelated equipment to `Pump-A11` and `Pump-A13`.
   - Tailor SOP updates, PM updates, and actions to the actual parameter breached and asset type.
   - In FMEA RPN mitigation, ensure mitigated RPN never exceeds initial RPN even if initial RPN < 16.
4. Remediation 4: Fix OEM Envelope Lower-Bound (`nominal_min`) & Negative Limit Math:
   - In `analyze_oem_deviations` and `compute_single_deviation`, support both `nominal_max` and `nominal_min`.
   - If a parameter specifies `nominal_min`, check whether `actual_val < nominal_min`. If `actual_val <= trip_limit` (where trip_limit is less than nominal_min), trigger `CRITICAL` or `HIGH`.
   - E.g., for `TURB-ST-04`, `lube_oil_pressure_bar: 0.8` (nominal_min: 1.5, trip_limit: 1.0) must be classified as CRITICAL / HIGH, NOT NORMAL!
   - Use `abs(envelope_limit)` for division-by-zero protection.
5. Remediation 5: Semantic Citation Grounding:
   - In `FiveWhyTreeBuilder` and `IshikawaClassifier`, match citations to causes based on keyword/text overlap with citation excerpts, rather than blindly attaching all citation IDs to every node.
   - Allow ungrounded claims to be flagged with `is_unsubstantiated=True` and `assumed_flag=True` as required by §R2.
6. Tests & Verification:
   - Add unit tests in `backend/tests/test_rca_engine.py` covering turbine `TURB-ST-04`, boiler `BLR-HP-101`, lower-bound pressure drops, dynamic 6M classification, and dynamic sister asset resolution.
   - Run `backend/venv/Scripts/pytest.exe` to ensure 100% pass rate with zero regressions across all suites (M1 + M2 + E2E).
7. Document your work in `handoff.md` and send a completion message to the orchestrator.
