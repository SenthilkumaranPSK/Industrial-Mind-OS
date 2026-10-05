# Automated Root Cause Analysis (RCA) & 8D Incident Report Studio
# E2E Test Infrastructure Specification (TEST_INFRA.md)

**Platform**: Industrial Mind OS  
**Status**: ACTIVE / TEST READY  
**Framework**: `pytest 9.1.1` + `FastAPI TestClient` (`httpx`) + `Pydantic v2`  
**Execution Environment**: 100% Offline (Zero external network, Zero Google Gemini API dependencies, Zero Qdrant file-locking)

---

## 1. Test Architecture Overview

The E2E Test Suite for the Automated Root Cause Analysis (RCA) & 8D Incident Report Studio implements an opaque-box, contract-driven testing harness. The suite validates the entire problem-solving lifecycle according to international quality and automotive engineering standards:
- **AIAG Team-Oriented Problem Solving (TOPS / 8D)**
- **ISO 9001:2015 Clause 10.2** (*Nonconformity and corrective action*)
- **IATF 16949 Section 10.2.3** (*Problem solving*)
- **AIAG-VDA Failure Mode and Effects Analysis (FMEA 1st Ed.)**
- **Kaoru Ishikawa 6M Manufacturing Taxonomy**
- **W3C CSS Paged Media Standard** (`@media print`, `@page`)

### Architectural Invariants:
1. **Opaque-Box Verification**: The test suite operates independently of internal backend implementation nuances, verifying strict adherence to documented domain schemas, mathematical formulas, and REST API interface contracts.
2. **Progressive Testability & Isolation**: Each test case sets up its own state, executes self-contained logic, and requires zero shared state or order-dependent fixtures.
3. **Deterministic & Offline**: All causal reasoning, timeline sorting, OEM envelope calculations, FMEA scoring, and SHA-256 canonical hashing execute locally in pure Python without live API tokens or external vector databases.

---

## 2. Directory Layout & Module Structure

```
backend/
├── tests/
│   ├── e2e_rca/
│   │   ├── conftest.py                       # Core test harness, domain models, pure-Python engines, FastAPI TestClient
│   │   ├── test_tier1_feature_coverage.py    # Tier 1: Feature coverage (≥5 tests per feature F1 through F10)
│   │   ├── test_tier2_boundary_corner.py     # Tier 2: Boundary & corner cases (≥5 tests per feature F1 through F10)
│   │   ├── test_tier3_cross_feature.py       # Tier 3: Cross-feature combinations & pairwise integration
│   │   └── test_tier4_real_world_scenarios.py # Tier 4: Realistic industrial incident scenarios
│   ├── test_ingestion_split.py              # Baseline repository tests
│   ├── test_scoping.py                      # Baseline repository tests
│   ├── test_text_utils.py                   # Baseline repository tests
│   └── test_verification.py                 # Baseline repository tests
TEST_INFRA.md                                # This document (Test Architecture)
TEST_READY.md                                # Test Suite Execution Readiness & Metrics Report
```

---

## 3. Test Runner Commands

### Executing E2E RCA Test Suite:
From directory `C:\000 MINE\My Codzz\Industrial Mind OS\backend`:

```powershell
# Run the entire E2E RCA test suite (116 tests)
& .\venv\Scripts\python.exe -m pytest tests/e2e_rca/ -v

# Run by individual tier:
& .\venv\Scripts\python.exe -m pytest tests/e2e_rca/test_tier1_feature_coverage.py -v
& .\venv\Scripts\python.exe -m pytest tests/e2e_rca/test_tier2_boundary_corner.py -v
& .\venv\Scripts\python.exe -m pytest tests/e2e_rca/test_tier3_cross_feature.py -v
& .\venv\Scripts\python.exe -m pytest tests/e2e_rca/test_tier4_real_world_scenarios.py -v

# Run entire repository test suite (143 tests):
& .\venv\Scripts\python.exe -m pytest -v
```

---

## 4. Test Case Inventory & Coverage Matrix

### Tier 1: Feature Coverage (50 Test Cases)
Verifies happy-path functionality across features F1 through F10 (5 tests per feature):

| Feature ID | Feature Name | Test Cases | Description |
|---|---|---|---|
| **F1** | 8D Pydantic Domain Schemas | `test_f1_01` to `test_f1_05` | Complete 8D report validation, 5W2H problem card, RPN scoring ($S \times O \times D$), action lifecycle, audit metadata. |
| **F2** | Incident Evidence & Citation Registry | `test_f2_01` to `test_f2_05` | Citation ID regex pattern (`CITE-...`), confidence scores, excerpt length, deduplication, local source file linking. |
| **F3** | Chronological Timeline Reconstruction | `test_f3_01` to `test_f3_05` | Out-of-order log sorting, sensor telemetry typing, event taxonomies, citation linking, multi-source log fusion. |
| **F4** | Deductive 5-Why Causal Tree Engine | `test_f4_01` to `test_f4_05` | Linear 5-level why chain, parent-child tree hierarchy, leaf root-cause tagging, bifurcated branching, dual occurrence/escape differentiation. |
| **F5** | Ishikawa 6M Fishbone Classifier | `test_f5_01` to `test_f5_05` | Classification across Man, Machine, Material, Method, Measurement, Environment; normalized impact weights. |
| **F6** | Assumption Flagging & Grounding Verifier | `test_f6_01` to `test_f6_05` | Substantiated vs unsubstantiated claims, automatic `assumed_flag=True`, dangling citation detection, Citation Grounding Ratio (CGR). |
| **F7** | Historical Near-Miss Similarity Matching | `test_f7_01` to `test_f7_05` | Matching `Pump-A12` vibration against `Near_Miss_Report_2023.txt`, zero similarity filtering, symptom extraction, historical lessons retrieval. |
| **F8** | OEM Operating Envelope Deviation Analysis | `test_f8_01` to `test_f8_05` | Standard deviation calculation ($\Delta\%$), nominal operation, warning limits, overspeed excursions, action recommendations. |
| **F9** | RCA REST API Router | `test_f9_01` to `test_f9_05` | Endpoint validation: `/analyze`, `/historical-match`, `/export-evidence` (JSON & HTML), `/reports` summary listings. |
| **F10** | Certified Compliance Audit Package Generator | `test_f10_01` to `test_f10_05` | Canonical JSON serialization, tamper detection on single-bit telemetry alteration, print-ready HTML export, `@media print` rules, bit-exact hashlib verification. |

### Tier 2: Boundary & Corner Cases (50 Test Cases)
Verifies input validation, error handling, and extreme operating parameters (5 tests per feature):

| Feature ID | Feature Name | Test Cases | Boundary Conditions Tested |
|---|---|---|---|
| **F1** | 8D Pydantic Domain Schemas | `test_f1_b01` to `test_f1_b05` | RPN minimum (1) and maximum (1000); out-of-range rejection ($S=0, S=11$); empty list rejections; report ID regex; extreme string lengths (10,000 chars). |
| **F2** | Citation Registry | `test_f2_b01` to `test_f2_b05` | Excerpt shorter than 5 chars rejected; confidence outside $[0.0, 1.0]$ rejected; invalid regex prefix rejected; UTF-8/math symbols ($\Delta, \ge$); empty catalog handling. |
| **F3** | Timeline Reconstruction | `test_f3_b01` to `test_f3_b05` | Identical timestamp collision resolution; reversed input log sorting; empty telemetry dictionary `{}`; cryogenic temperatures ($-196.5^\circ\text{C}$); unquoted citation flagging. |
| **F4** | 5-Why Causal Engine | `test_f4_b01` to `test_f4_b05` | Min/max tree depth (level 1 to 10; rejects 0 and 11); single-node root cause; multiple terminal root causes; cause statement min length; auto-flagging of empty citations. |
| **F5** | Ishikawa Classifier | `test_f5_b01` to `test_f5_b05` | Rejection of non-standard categories; exact contribution weight boundaries $0.0$ and $1.0$; statement min length; single-category dominance; full 6M category coverage. |
| **F6** | Assumption Flagging | `test_f6_b01` to `test_f6_b05` | Report with zero citations ($CGR = 0.0$); 100% grounded report ($CGR = 1.0$); exact $0.85$ audit threshold boundary; dangling foreign key citation references; ungrounded terminal root causes. |
| **F7** | Historical Matching | `test_f7_b01` to `test_f7_b05` | Empty symptoms list safe handling; perfect symptom matching score; uppercase/lowercase/case-insensitive matching; partial proportional scoring; empty near-miss record handling. |
| **F8** | OEM Envelope Analysis | `test_f8_b01` to `test_f8_b05` | Zero-division protection (`envelope_max = 0.0`); exact boundary zero deviation ($0.0\%$); extreme $10\times$ envelope breach ($+900.0\%$); exact $+15.0\%$ threshold boundary; negative sensor readings. |
| **F9** | REST API Router | `test_f9_b01` to `test_f9_b05` | Empty symptoms payload returns 422; missing asset tag returns 422; unsupported export format ("xml") returns 400; empty symptoms query returns 200 `[]`; unknown report ID fallback handling. |
| **F10** | Compliance Audit Package | `test_f10_b01` to `test_f10_b05` | Empty metadata deterministic hash; key ordering and whitespace invariance; HTML tag injection (`<script>`) neutralization; 1-character title mutation avalanche effect; 100-event payload scalability ($<100\text{ms}$). |

### Tier 3: Cross-Feature Combinations & Pairwise Integration (10 Test Cases)
Verifies multi-module interactions across disciplines:

1. `test_cross_01_timeline_to_five_why_deduction`: Reconstructed timeline events supply empirical chronological evidence directly into the 5-Why chain levels.
2. `test_cross_02_oem_deviation_to_preventative_controls`: Computed OEM envelope exceedance ($+16.0\%$, CRITICAL) directly generates D7 SOP updates and PM frequency adjustments.
3. `test_cross_03_historical_matching_to_horizontal_deployment`: Near-miss lessons learned from `Near_Miss_Report_2023.txt` drive horizontal deployment across sister assets (`Pump-A11`, `Pump-A13`, `Pump-A14`).
4. `test_cross_04_citation_registry_shared_across_dual_causal_models`: Shared citation catalog simultaneously validates and computes CGR across 5-Why and Ishikawa models.
5. `test_cross_05_root_cause_to_corrective_action_and_validation`: D4 root cause ID explicitly links to D5 Permanent Corrective Action, and D6 validates quantified baseline vs post-fix KPIs.
6. `test_cross_06_fmea_rpn_scoring_to_action_prioritization`: Initial high RPN (392, CRITICAL) drives emergency action prioritization, and post-fix revised RPN (48, LOW) measures $87.8\%$ risk reduction.
7. `test_cross_07_end_to_end_8d_assembly_to_tamper_evident_export`: End-to-end report generation via REST API through SHA-256 canonical JSON evidence package export.
8. `test_cross_08_full_api_workflow_pipeline`: End-to-end multi-endpoint pipeline: `/analyze` $\rightarrow$ `/historical-match` $\rightarrow$ `/export-evidence` (HTML and JSON).
9. `test_cross_09_dual_vector_causes_coupled_with_ishikawa_and_containment`: Physical occurrence vs escape causes integrated with 6M breakdown and audited 100% containment efficacy.
10. `test_cross_10_regulatory_audit_trail_and_closure_signoff`: Full ISO 9001 / IATF 16949 audit trail with D8 executive sign-off seal, downtime accounting, and digital signature hash.

### Tier 4: Realistic Industrial Incident Scenarios (6 Test Cases)
Deep end-to-end verification of authentic plant failure scenarios:

- **Scenario 1: Pump-A12 Inboard Ceramic Seal Failure** (Grounded in `Near_Miss_Report_2023.txt`):
  * `test_scenario1_pump_a12_ceramic_seal_end_to_end`: 5-event timeline, historical near-miss match against `Near_Miss_Report_2023.txt`, citations linking to historical text, 5-Why chain from coolant leak to DCS alarm threshold, 6M Ishikawa analysis, FMEA RPN drop from 336 to 16, 100% containment in 15 min, and D8 sign-off.
  * `test_scenario1_pump_a12_oem_deviation_and_compliance_package`: Evaluates $+16.0\%$ envelope breach ($5.8\text{ mm/s}$ vs $5.0\text{ mm/s}$), verifies CRITICAL severity, and validates print-ready HTML export with certified audit header.
- **Scenario 2: High-Pressure Steam Turbine Overspeed Trip**:
  * `test_scenario2_steam_turbine_overspeed_and_lube_failure`: Lube oil pressure collapse from 3.2 bar to 0.8 bar ($-60.0\%$, CRITICAL), bearing temperature spike to $118^\circ\text{C}$ ($+24.2\%$, CRITICAL), and emergency overspeed trip at 3,450 RPM ($+4.55\%$, HIGH).
  * `test_scenario2_steam_turbine_pca_validation_and_fmea_reduction`: Evaluates duplex filter auto-switchover and electrostatic cleaner PCA, verifying FMEA RPN reduction from 324 to 18 ($94.4\%$ reduction).
- **Scenario 3: Industrial Boiler Superheater Thermal Runaway**:
  * `test_scenario3_boiler_thermal_runaway_thermocouple_drift`: Superheater tube creep investigation caused by $-42^\circ\text{C}$ thermocouple calibration drift; actual metal temperature $452^\circ\text{C}$ vs $430^\circ\text{C}$ limit ($+5.12\%$, HIGH).
  * `test_scenario3_boiler_voting_logic_pca_and_horizontal_controls`: 2-out-of-3 (2oo3) thermocouple voting logic implementation, 90-day automated pyrometer calibration verification, and horizontal deployment to sister boilers `BLR-HP-102` and `BLR-HP-103`.

---

## 5. Coverage & Verification Summary

- **Total E2E Tests**: **116 Passed, 0 Failed, 0 Skipped** (100% Success Rate)
- **Total Backend Repository Tests**: **143 Passed, 0 Failed, 0 Skipped**
- **Execution Time**: **~0.30 seconds** for E2E suite; **~0.87 seconds** for entire project.
- **Quality Gates**:
  * AIAG 8D Discipline Completeness: 100%
  * Citation Grounding Enforcement: 100%
  * SHA-256 Tamper Protection: 100% Bit-exact verified
  * Offline Execution: 100% verified (Zero network sockets, Zero Gemini API, Zero Qdrant locking)
