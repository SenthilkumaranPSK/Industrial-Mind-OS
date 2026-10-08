# Handoff Report — Milestone 2 Remediation Review & Adversarial Challenge

**Reviewer**: `reviewer_m2_recheck` (Objective Reviewer & Adversarial Critic)  
**Date**: 2026-10-07T05:22:00Z  
**Target Milestone**: Milestone 2 (Deductive RCA & Preventative Engine Remediations)  
**Reviewed Artifacts**:
- `backend/services/rca_engine.py` (Implementation)
- `backend/tests/test_rca_engine.py` (Unit & Remediation Tests)
- `backend/tests/test_adversarial_m2_stress.py` (Adversarial Stress Test Suite)
- `backend/api/rca_schemas.py` (Domain Models)

---

## Review Summary

**Verdict**: **`REQUEST_CHANGES`**  
**Integrity Status**: **CLEAN (No intentional cheating, hardcoding, or facade implementations detected)**  
**Correctness & Robustness Status**: **CRITICAL DATA CORRUPTION & DIGITAL SEAL FAILURE IDENTIFIED IN PERSISTENCE / JSON ROUND-TRIP**

The Worker has made commendable and substantial progress. The 5 assigned remediations have been implemented with genuine dynamic logic:
- Dynamic 5-Why synthesis and multi-asset taxonomy for Steam Turbines and High-Pressure Boilers completely eliminate pump ceramic seal text for those equipment families.
- The Ishikawa 6M classifier dynamically maps domain categories without static pump defaults.
- Horizontal sister asset resolution correctly parses naming prefixes and numbering sequences.
- Bounded FMEA RPN mitigation enforces $RPN_{\text{mitigated}} \le RPN_{\text{initial}}$ across all boundaries, fixing negative risk reductions.
- Semantic token citation matching properly isolates substantiated nodes and auto-flags ungrounded causal claims.
- All 4 previously failing adversarial tests in `test_adversarial_m2_stress.py` now pass (`26 passed, 4 xpassed`).
- The entire backend test suite reports 100% pass rate (`454 passed, 4 xpassed`).

**However, adversarial stress testing uncovered a critical flaw in Remediation 4 (Lower-Bound OEM Envelope Math)**:
While lower-bound telemetry excursions (e.g. turbine lube oil pressure dropping to 0.8 bar) evaluate correctly in memory, `rca_engine.py:177-180` failed to call `EightDIncidentReport.model_rebuild(force=True)`. Consequently, when an 8D report is serialized to JSON and reloaded (via API response serialization, database retrieval, or client ingestion), Pydantic v2 executes the unpatched cached core validator:
1. The lower-bound deviation is mutated from `+46.67% (CRITICAL)` to `-46.67% (LOW)`.
2. The canonical SHA-256 seal is broken: `reloaded.verify_checksum()` returns `False`!

Additionally, uncataloged assets of family `"General Rotating Asset"` (e.g. `GEN-1`, `COMP-01`) fall back to pump mechanical seal text in D2, D3, D5, and D8 because `assemble_eight_d_report` only branches on `Steam Turbine` and `High-Pressure Boiler`.

---

## 1. Observation

### 1.1 Test Suite Verification Commands and Outputs

1. **RCA Engine Unit & Remediation Test Suite**:
   - Command: `backend\venv\Scripts\pytest.exe backend/tests/test_rca_engine.py -v`
   - Result:
     ```text
     ============================= 57 passed in 0.27s ==============================
     ```
   - Observed: All 50 original tests and 7 new remediation tests (`test_51` through `test_57`) passed.

2. **Adversarial Stress Test Suite**:
   - Command: `backend\venv\Scripts\pytest.exe backend/tests/test_adversarial_m2_stress.py -v`
   - Result:
     ```text
     ======================== 26 passed, 4 xpassed in 0.18s ========================
     ```
   - Observed: All 4 tests previously marked `xfail` by Challenger 2 (`test_zero_similarity_symptoms_on_known_asset_leakage`, `test_empty_or_whitespace_symptoms_sanitization`, `test_nan_and_inf_json_roundtrip_integrity`, `test_mitigated_rpn_never_exceeds_initial_rpn`) now pass without regressions.

3. **Full Backend Test Suite**:
   - Command: `backend\venv\Scripts\pytest.exe backend/tests/ -q`
   - Result:
     ```text
     454 passed, 4 xpassed, 1 warning in 1.75s
     ```
   - Observed: 100% pass rate across all modules.

---

### 1.2 Empirical Failure 1: Lower-Bound Deviation Reversion & SHA-256 Seal Invalidation on JSON Round-Trip [CRITICAL]

- **File**: `backend/services/rca_engine.py:177-180`
- **Code**:
  ```python
  OEMDeviation.__pydantic_decorators__.model_validators["compute_deviation"].func = _patched_oem_compute_deviation
  OEMDeviation.compute_deviation = _patched_oem_compute_deviation
  OEMDeviation.__pydantic_complete__ = False
  OEMDeviation.model_rebuild(force=True)
  PreventativeControls.__pydantic_complete__ = False
  PreventativeControls.model_rebuild(force=True)
  # NOTE: EightDIncidentReport is NOT rebuilt here!
  ```
- **Empirical Execution Command**:
  ```powershell
  backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from api.rca_schemas import EightDIncidentReport; from services.rca_engine import assemble_eight_d_report; rep = assemble_eight_d_report('TURB-ST-04', ['low lube'], '2024-01-01T00:00:00Z', telemetry_data={'lube_oil_pressure_bar': 0.8}); reloaded = EightDIncidentReport.model_validate_json(rep.model_dump_json()); print('In-memory verify:', rep.verify_checksum()); print('Reloaded verify:', reloaded.verify_checksum()); print('Reloaded deviation %:', reloaded.d7_preventative_controls.oem_deviations[0].deviation_percent); print('Reloaded severity:', reloaded.d7_preventative_controls.oem_deviations[0].severity_level)"
  ```
- **Verbatim Output**:
  ```text
  In-memory verify: True
  Reloaded verify: False
  Reloaded deviation %: -46.67
  Reloaded severity: SeverityLevel.LOW
  ```
- **Observed Result**:
  In-memory, the report is generated with `deviation_percent = +46.67%` and `SeverityLevel.CRITICAL`. However, upon serializing to JSON and reloading via `EightDIncidentReport.model_validate_json()`, the un-rebuilt core validator reverts the lower-bound parameter to `-46.67%` and `SeverityLevel.LOW`. This mutation causes `reloaded.verify_checksum()` to fail (`False`), corrupting the digital seal and triggering false positive tamper detection.

---

### 1.3 Empirical Failure 2: Uncataloged Assets Fallback Leaks Pump Narrative in 8D Disciplines [MAJOR]

- **File**: `backend/services/rca_engine.py:1669-1844`, `1337-1393`
- **Code in `assemble_eight_d_report`**:
  ```python
  if family == "Steam Turbine":
      ...
  elif family == "High-Pressure Boiler":
      ...
  else:
      # Centrifugal pump (default)
      d2_problem = ProblemDescription(
          what=f"Catastrophic ceramic mechanical seal fracture and coolant fluid leak ({symptom_str})",
          ...
      )
  ```
- **Code in `detect_asset_family` (line 1012)**:
  For an asset that is not a turbine, boiler, or pump (e.g. `GEN-1` generator or `COMP-01` compressor), `detect_asset_family` returns `"General Rotating Asset"`.
- **Empirical Execution Command**:
  ```powershell
  backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from services.rca_engine import assemble_eight_d_report; rep = assemble_eight_d_report('GEN-1', ['bearing vibration'], '2024-01-01T00:00:00Z'); print('GEN-1 D2 What:', rep.d2_problem.what); print('GEN-1 D5 Action:', rep.d5_permanent_actions[1].action)"
  ```
- **Verbatim Output**:
  ```text
  GEN-1 D2 What: Catastrophic ceramic mechanical seal fracture and coolant fluid leak (bearing vibration)
  GEN-1 D5 Action: Replace shattered ceramic seal with upgraded silicon carbide (SiC) flexible composite seal assembly.
  ```
- **Observed Result**:
  While `FiveWhyTreeBuilder` has a generic branch for `"General Rotating Asset"` (lines 1188-1200), `assemble_eight_d_report` and `IshikawaClassifier` fall back to the pump seal narrative whenever equipment is not a Steam Turbine or High-Pressure Boiler.

---

## 2. Logic Chain

### 2.1 Remediation Audit by Component

1. **Remediation 1: Dynamic Asset Family Resolution & 5-Why Synthesis**:
   - *Observation*: Turbine (`TURB-ST-04`) and Boiler (`BLR-HP-101`) tests (`test_51`, `test_52`) assert absence of ceramic seal narratives.
   - *Logic*: `detect_asset_family` properly identifies steam turbines and high-pressure boilers. In `FiveWhyTreeBuilder.build_tree`, causal chains dynamically instantiate turbine lube oil film collapse / rotor overspeed or boiler superheater metallurgical creep.
   - *Status*: **VERIFIED & FUNCTIONAL** for specified asset families. (Minor gap: uncataloged assets leak in 8D assembly, see §1.3).

2. **Remediation 2: Dynamic Ishikawa 6M Classifier**:
   - *Observation*: `test_54` checks 6M categories for turbines.
   - *Logic*: `IshikawaClassifier` decomposes causes across Man, Machine, Material, Method, Measurement, and Environment with active domain keywords. Causes for turbines reference governors and journal bearings rather than mechanical seals.
   - *Status*: **VERIFIED & FUNCTIONAL**.

3. **Remediation 3: Dynamic Preventative Controls & Sister Asset Resolution**:
   - *Observation*: `test_55` tests `resolve_sister_assets` across multiple tag structures (`TURB-ST-04` -> `["TURB-ST-01", "TURB-ST-02"]`; `BLR-HP-101` -> `["BLR-HP-102", "BLR-HP-103"]`; `GEN-1` -> `["GEN-2", "GEN-3"]`). `test_57` verifies $RPN_{\text{mitigated}} \le RPN_{\text{initial}}$ when initial RPN is 10 and 0.
   - *Logic*: Regex tag prefix and numerical sequence derivation works dynamically without hardcoding. Clamping via `min(initial_rpn, 16)` guarantees non-negative risk reduction.
   - *Status*: **VERIFIED & FUNCTIONAL**.

4. **Remediation 4: OEM Envelope Lower-Bound Math Protection**:
   - *Observation*: In-memory `analyze_oem_deviations("TURB-ST-04", {"lube_oil_pressure_bar": 0.8})` yields `+46.67%` and `CRITICAL`.
   - *Flaw*: Deserialization of `EightDIncidentReport` resets the nested `OEMDeviation` to `-46.67%` and `LOW`, invalidating the SHA-256 seal.
   - *Causation*: Pydantic v2 compiles validator schemas eagerly. While `OEMDeviation` and `PreventativeControls` were rebuilt, `EightDIncidentReport` retained the pre-patch validator closure in its compiled schema.
   - *Status*: **FAILING UNDER PERSISTENCE / JSON ROUND-TRIP**.

5. **Remediation 5: Semantic Token Citation Grounding & Unsubstantiated Claim Flagging**:
   - *Observation*: `test_56` validates that an unrelated citation in the registry leaves all 5-Why nodes marked `is_unsubstantiated=True`, and registering a matching excerpt substantiates only overlapping nodes.
   - *Logic*: `match_semantic_citations` extracts tokens $\ge 3$ characters, filters administrative stopwords, and counts excerpt matches. Nodes without matching citations have `is_unsubstantiated=True` and `assumed_flag=True`.
   - *Status*: **VERIFIED & FUNCTIONAL**.

---

### 2.2 Adversarial & Integrity Assessment

- **Integrity**: Did the Worker introduce hardcoded test cheats or facade implementations?
  *Finding*: No. The code contains genuine dynamic algorithmic implementations across all 5 remediations. The 4 previously xfailing adversarial tests are now genuinely resolved.
- **Robustness**: Does the solution survive hostile operational conditions?
  *Finding*: No. In any real-world architecture where reports are serialized over HTTP (FastAPI) or saved to a document store, lower-bound parameters will silently corrupt upon reload and fail SHA-256 integrity verification.

---

## 3. Caveats

- **Scope of Invalidation**: The deserialization bug affects only parameters with lower bounds (`nominal_min`) such as `lube_oil_pressure_bar`. Upper-bound parameters (e.g. `vibration_mm_s`, `rpm`, `temperature_c`) are unaffected and serialize cleanly.
- **Fix Complexity**: The required fix is straightforward: adding `EightDIncidentReport.__pydantic_complete__ = False; EightDIncidentReport.model_rebuild(force=True)` at module top-level immediately resolves the issue.

---

## 4. Conclusion

The Milestone 2 remediations represent high-quality work, but a critical defect remains in the persistence/round-trip behavior of lower-bound OEM deviations, breaking canonical SHA-256 seal validation.

**Verdict**: **`REQUEST_CHANGES`**

### Required Action Items for Worker M2:

1. **Rebuild `EightDIncidentReport` in `backend/services/rca_engine.py`**:
   At line 181 of `rca_engine.py`, add:
   ```python
   EightDIncidentReport.__pydantic_complete__ = False
   EightDIncidentReport.model_rebuild(force=True)
   ```

2. **Add General Asset Fallback in `assemble_eight_d_report` & `IshikawaClassifier`**:
   In `assemble_eight_d_report` and `IshikawaClassifier.classify_causes`, ensure that when `family` is `"General Rotating Asset"` (or not a pump), D2, D3, D5, D8, and Ishikawa branches use generic rotating equipment failure text rather than defaulting to ceramic pump mechanical seals.

3. **Add Roundtrip Test in `backend/tests/test_rca_engine.py`**:
   Add a test verifying that an 8D report containing a lower-bound deviation (e.g. `TURB-ST-04` lube pressure 0.8 bar) survives `EightDIncidentReport.model_validate_json(report.model_dump_json())` with:
   - `deviation_percent > 0`
   - `severity_level == SeverityLevel.CRITICAL`
   - `reloaded.verify_checksum() is True`

---

## 5. Verification Method

Once Worker M2 applies the changes, verify independently using:

1. **JSON Deserialization & SHA-256 Seal Invariance for Lower Bounds**:
   ```powershell
   backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from api.rca_schemas import EightDIncidentReport; from services.rca_engine import assemble_eight_d_report; rep = assemble_eight_d_report('TURB-ST-04', ['low lube'], '2024-01-01T00:00:00Z', telemetry_data={'lube_oil_pressure_bar': 0.8}); reloaded = EightDIncidentReport.model_validate_json(rep.model_dump_json()); assert reloaded.verify_checksum() is True, 'SHA-256 seal failed on reload'; assert reloaded.d7_preventative_controls.oem_deviations[0].deviation_percent > 40.0, 'Deviation reverted to negative'; assert reloaded.d7_preventative_controls.oem_deviations[0].severity_level.value == 'CRITICAL', 'Severity dropped to LOW'; print('PASSED: Lower-bound JSON roundtrip & seal invariance verified!')"
   ```

2. **General Asset Pump Narrative Isolation**:
   ```powershell
   backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from services.rca_engine import assemble_eight_d_report; rep = assemble_eight_d_report('GEN-1', ['bearing vibration'], '2024-01-01T00:00:00Z'); assert 'ceramic' not in rep.d2_problem.what.lower(), 'Leaked ceramic seal into GEN-1 D2'; assert 'ceramic' not in rep.d5_permanent_actions[1].action.lower(), 'Leaked ceramic seal into GEN-1 D5'; print('PASSED: General asset isolation verified!')"
   ```

3. **Complete Regression Suite**:
   ```powershell
   backend\venv\Scripts\pytest.exe backend/tests/test_rca_engine.py -v
   backend\venv\Scripts\pytest.exe backend/tests/test_adversarial_m2_stress.py -v
   backend\venv\Scripts\pytest.exe backend/tests/ -q
   ```
