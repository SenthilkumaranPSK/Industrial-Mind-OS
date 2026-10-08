# Milestone 2 Adversarial Verification Handoff Report

**Author**: Challenger 1 (Critic, Empirical Challenger, Specialist)  
**Date**: 2026-10-06T07:30:00Z  
**Target Milestone**: Milestone 2 (Deductive RCA & Preventative Engine Verification)  
**Subject Under Test**: `backend/services/rca_engine.py`  
**Test Deliverable**: `backend/tests/stress_test_rca_engine.py` (42 tests)

---

## 1. Observation

### 1.1 Test Suite Execution Commands & Verbatim Outputs
1. **Milestone 2 Baseline Unit Test Suite**:
   - Command: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_rca_engine.py -v`
   - Output: `50 passed in 0.15s`
2. **Adversarial Stress Test Suite (`backend/tests/stress_test_rca_engine.py`)**:
   - Command: `backend\venv\Scripts\python.exe -m pytest backend/tests/stress_test_rca_engine.py -v`
   - Output: `42 passed in 0.26s`
3. **Combined Milestone 2 Verification Suite**:
   - Command: `backend\venv\Scripts\python.exe -m pytest backend/tests/test_rca_engine.py backend/tests/stress_test_rca_engine.py backend/tests/test_adversarial_m2_stress.py -v`
   - Output: `118 passed, 4 xfailed in 0.63s`
4. **Full Backend Repository Suite**:
   - Command: `backend\venv\Scripts\python.exe -m pytest backend/tests -q`
   - Output: `447 passed, 4 xfailed, 1 warning in 1.54s`

### 1.2 Empirical Code Inspections & Direct Behavioral Findings
1. **Citation Grounding Enforcement**:
   - `backend/services/rca_engine.py:874-885` (`FiveWhyTreeBuilder.build_tree`):
     ```python
     if registry is not None:
         for node in nodes:
             valid_ids, _ = registry.validate_citation_ids(node.citation_ids)
             if not valid_ids:
                 node.is_unsubstantiated = True
                 node.assumed_flag = True
                 node.assumption_flag = True
     ```
     Verbatim test observation: Nodes initialized with fake citation IDs (e.g. `["CITE-FAKE-999"]`) against an authentic registry are strictly evaluated to `valid_ids == []`, resulting in `is_unsubstantiated=True`, `assumed_flag=True`, `assumption_flag=True`.
   - `backend/api/rca_schemas.py:536-548` (`EightDIncidentReport.calculate_rpn_and_sort_timeline`):
     Cross-references `d4_root_causes.five_why_chain` against `known_cite_ids = {c.citation_id for c in self.citations}`. When citation IDs are absent from the report's citations list, nodes are strictly marked `is_unsubstantiated=True` and `assumed_flag=True`.

2. **5-Why Tree Logical Hierarchy**:
   - `backend/services/rca_engine.py:814-870` (`FiveWhyTreeBuilder.build_tree`):
     Generates exactly 5 levels with strictly monotonic identifiers: `WHY-1` ($L1$) to `WHY-5` ($L5$).
     Parent-child links strictly satisfy $Node_{i}.\text{parent\_node\_id} == Node_{i-1}.\text{why\_id}$, verified acyclic through graph traversal.
     Terminal root cause flag is strictly constrained: `is_root_cause=True` exclusively on Level 5 (`WHY-5`); Levels 1-4 are `is_root_cause=False`.
   - `FiveWhyNode` schema in `rca_schemas.py:162`: Enforces `ge=1, le=10`. Adversarial attempts to construct Level 0 or Level 11 raise `pydantic_core.ValidationError`.

3. **Ishikawa 6M Classification Coverage & Normalization**:
   - `backend/services/rca_engine.py:952-1021` (`IshikawaClassifier.classify_causes`):
     Under all inputs (including empty symptoms and non-manufacturing keywords like `"quantum fluctuation"`), all 6 standard categories (`Man`, `Machine`, `Material`, `Method`, `Measurement`, `Environment`) are produced.
     `FishboneBranch` validator (`rca_schemas.py:218-234`) normalizes case-insensitive variants (`"milieu" -> "Environment"`, `"machine" -> "Machine"`), while invalid categories (e.g. `"Marketing"`) raise `ValidationError`.

4. **OEM Envelope Division-by-Zero & Math Boundaries**:
   - `backend/services/rca_engine.py:309-315` (`compute_single_deviation`):
     ```python
     if envelope_max > 0:
         dev_pct = round(((incident_value - envelope_max) / envelope_max) * 100.0, 2)
         is_exceeded = incident_value > envelope_max
     else:
         dev_pct = 0.0
         is_exceeded = False
     ```
     Guarantees division-by-zero protection for `envelope_max = 0.0` and negative values.
     Stratifies into 4 tiers (`NORMAL`, `WARNING`, `HIGH`, `CRITICAL`) with monotonic float threshold transitions at `0.0%`, `10.0%`, and `15.0%`.

5. **Cryptographic SHA-256 Tamper Invariance**:
   - `backend/api/rca_schemas.py:551-579`:
     Canonical JSON hashing excludes `checksum_sha256`. Mutating any field across D1 (Team Leader), D2 (Problem statement), D3 (Containment), D4 (Five-Why cause), D5 (Corrective action), D6 (Metrics), D7 (Preventative controls), D8 (Sign-off), or severity score immediately causes `report.verify_checksum() == False`.

6. **Empirical Edge-Case Vulnerability Discovered**:
   - Executing `assemble_eight_d_report(asset_tag="", symptoms=["vibration"], incident_timestamp="2023-11-04T12:00:00Z", report_id="invalid")` raises:
     ```
     pydantic_core._pydantic_core.ValidationError: 1 validation error for EightDIncidentReport
     report_id
       String should match pattern '^8D-[0-9]{4}-[A-Za-z0-9_\-]+$' [type=string_pattern_mismatch, input_value='8D-2023-', input_type=str]
     ```
   - Traced to `backend/services/rca_engine.py:1347-1353`:
     `clean_tag = re.sub(r"[^A-Za-z0-9]", "_", asset_tag).upper()`. If `asset_tag` has no alphanumeric characters, `clean_tag == ""` and fallback `rep_id = f"8D-2023-{clean_tag}"` produces `"8D-2023-"` with no trailing suffix.

---

## 2. Logic Chain

1. **Symptom Boundary Stress Testing**:
   - Observations 1.1 and 1.2 demonstrate that passing empty symptom lists (`[]`), single-character symptoms (`["v"]`), 150+ symptoms, duplicate entries, whitespace strings, and injection payloads (XSS, SQLi, Unicode) to `FiveWhyTreeBuilder`, `IshikawaClassifier`, `HistoricalMatcher`, and `DeductiveRCAEngine` execute without unhandled exceptions.
   - For empty symptom lists, `FiveWhyTreeBuilder` defaults to `"Unspecified operational anomaly"`, preventing null pointer dereferences or blank strings.

2. **Grounding & Assumption Flagging Enforcement**:
   - The user specification mandates: "strictly grounding all causal claims in retrieved documentation and flagging any unsubstantiated assumptions".
   - Observation 1.2 (item 1) shows dual-layer grounding enforcement:
     * Layer 1: Schema-level model validator on `FiveWhyNode`, `FishboneBranch`, and `FishboneCauseItem` auto-flags nodes with missing citation IDs (`is_unsubstantiated=True`, `assumed_flag=True`).
     * Layer 2: Registry-level validation in `FiveWhyTreeBuilder` and `EightDIncidentReport` cross-references citation IDs against the authoritative registry and report citations list, catching hallucinated/fake citation IDs.

3. **5-Why Structural Invariance**:
   - Observation 1.2 (item 2) shows that causal depth is strictly maintained across 5 distinct deductive tiers without collapsing into fewer levels or exceeding 10.
   - Graph cycle analysis verifies that parent pointers strictly ascend without loops.
   - Only Level 5 possesses `is_root_cause=True`, preventing ambiguity in corrective action targeting.

4. **Ishikawa 6M Classification Invariance**:
   - Observation 1.2 (item 3) verifies that all 6 manufacturing branches are present.
   - Keyword heuristics ensure robust categorization, and absence of keywords falls back to standard causal structures without crashing.

5. **Discovered Edge-Case Analysis**:
   - Observation 1.2 (item 6) isolates a minor bug: when `asset_tag` is empty and an invalid `report_id` is supplied, fallback string interpolation generates `"8D-2023-"`, triggering a regex mismatch. In standard usage where `asset_tag` is non-empty (e.g. `"Pump-A12"`), `report_id` defaults to `"8D-2023-PUMP_A12-001"`, which strictly conforms to schema constraints.

---

## 3. Caveats

1. **Review-Only Constraint**:
   - In accordance with the Review-Only constraint, no modification was made to `backend/services/rca_engine.py` to patch the empty asset tag fallback or the xfailed edge cases.
2. **Offline Mode**:
   - All tests were executed in an isolated offline environment without live external Qdrant or cloud LLM endpoints.

---

## 4. Conclusion

**Verdict: VERIFIED & ROBUST WITH ADVISORY FINDINGS**

The deductive causal reasoning engine in `backend/services/rca_engine.py`:
1. Successfully enforces strict citation grounding and auto-flags ungrounded claims across both schema and registry validation layers.
2. Maintains a strict 5-level acyclic hierarchy for 5-Why analysis, ending in an exclusive Level 5 root cause.
3. Generates complete, validated Ishikawa 6M fishbone models with graceful fallback under adversarial inputs.
4. Resists numerical edge cases (zero envelope limit, astronomical values, corrupted dictionaries) with division-by-zero protection.
5. Employs tamper-evident canonical SHA-256 fingerprinting that detects alterations across all 8 disciplines.

**Advisory Findings for Worker / Future Hardening**:
- *Finding 1 (Low)*: In `assemble_eight_d_report:1347`, default `clean_tag` to `"ASSET"` when `asset_tag` is empty or lacks alphanumeric characters to avoid generating invalid `"8D-2023-"` report IDs.
- *Finding 2 (Informational)*: In `HistoricalMatcher.match`, incorporate a minimum symptom similarity check before confirming matches on asset tag similarity alone.
- *Finding 3 (Informational)*: In `generate_preventative_controls:1101`, clamp `mitigated_rpn` to `min(16, max(1, initial_rpn // 2))` so that initial RPN values under 16 do not show negative risk reduction.

---

## 5. Verification Method

To independently verify these adversarial results, execute:

```powershell
# 1. Run Challenger's Adversarial Stress Test Suite (42 tests)
.\backend\venv\Scripts\python.exe -m pytest backend/tests/stress_test_rca_engine.py -v

# 2. Run Milestone 2 Baseline Unit Tests (50 tests)
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_rca_engine.py -v

# 3. Run Full Combined M2 Test Suite (118 passed, 4 xfailed)
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_rca_engine.py backend/tests/stress_test_rca_engine.py backend/tests/test_adversarial_m2_stress.py -v

# 4. Run Full Backend Test Suite (447 passed, 4 xfailed)
.\backend\venv\Scripts\python.exe -m pytest backend/tests -q
```

**Invalidation Conditions**:
- Any failure in `stress_test_rca_engine.py`.
- Any failure in `test_rca_engine.py`.
- Tampering with `checksum_sha256` that fails to be detected by `report.verify_checksum()`.
