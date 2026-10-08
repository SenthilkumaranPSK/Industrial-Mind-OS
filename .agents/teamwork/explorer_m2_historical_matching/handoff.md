# Milestone 2 Handoff: Historical Near-Miss Matching & Recurrence Risk Engine

**Author**: Explorer Agent M2 (`explorer_m2_historical_matching`)  
**Target Milestone**: Milestone 2 (Deductive Root Cause Analysis Engine & Preventative Matching)  
**Destination Folder**: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m2_historical_matching`  
**Timestamp**: 2026-10-06T07:20:00Z  
**Handoff Type**: Hard Handoff (Investigation & Blueprint Formulation Complete)

---

## 1. Observation

### 1.1 Direct Repository & File Observations
1. **`ORIGINAL_REQUEST.md`**:
   - Requirement §R4 mandates: *"An automated cross-referencing module that compares the current incident against historical near-misses and OEM operating envelopes to recommend actionable preventative maintenance updates and prevent recurring downtime."*
2. **`orchestrator_1/PROJECT.md`**:
   - Lines 8 & 26: Feature F7 defines *"Historical Near-Miss Similarity Matching: Cross-references incidents against historical records (e.g. `Near_Miss_Report_2023.txt`) and calculates similarity"*, owned by Milestone M2 in `backend/services/rca_engine.py`.
   - Lines 78-80: API contract `POST /api/v1/rca/historical-match` accepts `HistoricalMatchRequest` (`asset_tag: str`, `symptoms: List[str]`, `telemetry_features: Optional[Dict]`) and returns `List[HistoricalMatch]`.
3. **`Near_Miss_Report_2023.txt`**:
   - Lines 3-7: Date: `November 4, 2023`, Equipment Tag: `Pump-A12`, Location: `Primary Cooling Loop, Sector 4`, Classification: `Near-Miss / Environmental Hazard`.
   - Lines 9-10: *"Pump A12 experienced a catastrophic mechanical seal failure. This resulted in a minor leak of coolant fluid onto the factory floor. The spill was contained within 15 minutes by the emergency response team... There were no injuries."*
   - Lines 12-14: *"Post-incident analysis revealed that the pump had been operating with a severe vibration level of 5.8 mm/s for 48 hours prior to the failure. Operations personnel ignored the vibration alerts because they mistakenly believed the threshold was 6.5 mm/s. The sustained vibration at 5.8 mm/s shattered the inboard ceramic seals."*
   - Lines 15-18: Corrective actions mandate:
     - *"The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s as per the OEM manual."*
     - *"Any vibration reading exceeding 5.5 mm/s requires an immediate, mandatory shutdown of the pump to prevent seal fracture."*
     - *"All technicians must be re-trained on the specific tolerance limits of the A-series pumps."*
4. **`backend/api/rca_schemas.py`**:
   - Lines 281-295: `HistoricalMatch` model definition:
     ```python
     class HistoricalMatch(BaseModel):
         matched_report_id: str
         title: str
         similarity_score: float  # [0.0, 1.0]
         matching_symptoms: List[str]
         preventative_recommendations: List[str]
         equipment_family: Optional[str] = "Centrifugal Pump"
         recurring_risk_assessment: Optional[str] = None
         source_doc_citation_id: Optional[str] = None
     ```
   - Lines 384-396: `PreventativeControls` model embeds `historical_matches: List[HistoricalMatch]` and `horizontal_assets: List[str]`.
   - Lines 610-617: `HistoricalMatchRequest` defines `asset_tag: str`, `symptoms: List[str]`, `telemetry_features: Optional[Dict[str, Any]] = Field(default_factory=dict)`.
5. **`backend/services/rca_ingestion.py`**:
   - Lines 209-256: `EvidenceCitationExtractor.ingest_near_miss_file()` parses `Near_Miss_Report_2023.txt` and registers section citations and granular corrective action citations into `CitationRegistry`.
   - Lines 377-384: `OEM_ENVELOPES["Pump-A12"]` defines `equipment_family="Centrifugal Pump"`, `nominal_max=5.0`, `trip_limit=5.5` for vibration velocity in `mm/s`.
6. **`backend/tests/e2e_rca/conftest.py`**:
   - Lines 166-174: Test-side model `HistoricalMatchResult` uses `historical_lessons: List[str]` alongside `preventative_recommendations`.
   - Lines 434-470: Reference function `match_historical_records(asset_tag, symptoms, near_miss_text)` defines baseline scoring: 0.5 for tag match + 0.5 for symptom match ratio; threshold $\ge 0.30$.
7. **`backend/tests/e2e_rca/test_tier1_feature_coverage.py`**:
   - Lines 644-701: Tests `test_f7_01` to `test_f7_05` require:
     - Exact match on `Pump-A12` with `["vibration", "ceramic seal", "coolant leak"]` has `similarity_score >= 0.8` and `"ceramic seal"` in `matching_symptoms`.
     - Unrelated equipment `Conveyor-C99` returns 0 matches.
     - Extracted lessons contain `"5.0 mm/s"` and `"shutdown"`.
     - Equipment family is identified as `"A-Series Centrifugal Pump"`.
8. **`backend/tests/e2e_rca/test_tier2_boundary_corner.py`**:
   - Lines 549-589: Tests `test_f7_b01` to `test_f7_b05` require:
     - Empty symptoms list returns `[]` safely without exception.
     - Case-insensitivity across uppercase, lowercase, and mixed-case tags and symptoms.
     - Symptom proportionality: matching 1 of 1 symptom yields higher score than 1 of 4 symptoms.
     - Empty near-miss text string `""` returns `[]` without error.
9. **`backend/tests/e2e_rca/test_tier3_cross_feature.py`**:
   - Lines 106-132: `test_cross_03_historical_matching_to_horizontal_deployment` verifies that historical match on `Pump-A12` populates D7 horizontal deployment sister assets `["Pump-A11", "Pump-A13", "Pump-A14"]` with description referencing `hist_match.matched_report_id` and `hist_match.historical_lessons`.
10. **Test Execution Baseline**:
    - Ran command: `.\venv\Scripts\python.exe -m pytest tests/e2e_rca/` -> Result: `116 passed in 0.24s`.
    - Ran command: `.\venv\Scripts\python.exe -m pytest tests/ -k "not e2e"` -> Result: `255 passed in 0.98s`.

---

## 2. Logic Chain

1. **Corpus & Feature Mapping (From Observation 1.1, 1.3, 1.4)**:
   The near-miss report `Near_Miss_Report_2023.txt` provides the single authoritative historical baseline for rotating pump failure in this facility. The incident record contains discrete facts: Report ID `NM-2023-PUMP-A12`, asset `Pump-A12`, mechanical seal catastrophic failure, 5.8 mm/s vibration excursion sustained 48h, OEM nominal limit 5.0 mm/s, mandatory trip threshold 5.5 mm/s, and three preventative directives. This directly maps to `HistoricalMatch` fields (`matched_report_id`, `title`, `equipment_family`, `preventative_recommendations`, `source_doc_citation_id`).

2. **Sister Asset & Equipment Taxonomy (From Observation 1.3, 1.7, 1.9)**:
   Section 4 of `Near_Miss_Report_2023.txt` explicitly refers to *"specific tolerance limits of the A-series pumps"*. Furthermore, `test_cross_03` in `test_tier3_cross_feature.py` asserts horizontal deployment to sister assets `["Pump-A11", "Pump-A13", "Pump-A14"]`. Therefore, our engine must recognize the `A-Series Centrifugal Pump` family:
   - When queried with `Pump-A12`: Exact match factor $S_{asset} = 1.0$.
   - When queried with sister units (`Pump-A11`, `Pump-A13`, `Pump-A14`): Sister asset factor $S_{asset} = 0.85$.
   - When queried with unrelated machinery (`Conveyor-C99`): Unrelated factor $S_{asset} = 0.0$.

3. **Multi-Factor Similarity Algorithm (From Observation 1.6, 1.7, 1.8)**:
   To satisfy all boundary conditions (proportionality, case-insensitivity, empty symptoms, and threshold pruning):
   - **Case-Insensitive Tag & Symptom Sanitization**: Clean whitespace and convert to lowercase.
   - **Matching Symptoms Extraction**: $M = \{s \in \text{symptoms} \mid s.\text{lower}() \in \text{text}.\text{lower}()\}$.
   - **Symptom Proportionality Ratio**: $S_{symptom} = \frac{|M|}{|\text{symptoms}|}$. (If $|\text{symptoms}| = 0$, return $0.0$).
   - **Telemetry Correlation**: If telemetry vibration is supplied, compare against historical excursion $5.8\text{ mm/s}$ and trip limit $5.5\text{ mm/s}$ to yield $S_{telemetry} \in [0.2, 1.0]$.
   - **Composite Formula**:
     - With telemetry: $S_{final} = 0.40 \cdot S_{asset} + 0.40 \cdot S_{symptom} + 0.20 \cdot S_{telemetry}$
     - Without telemetry: $S_{final} = 0.50 \cdot S_{asset} + 0.50 \cdot S_{symptom}$
   - **Pruning**: If $S_{final} < 0.30$ or $|\text{symptoms}| == 0$ or $\text{text} == ""$, return `[]`.

4. **Recurrence Risk & Probability Estimation (From Observation 1.4, 1.7, 1.9)**:
   In industrial root cause analysis, repeated occurrence of a known near-miss demonstrates systemic failure of prior containment. We model recurrence probability as:
   $$P_{recurrence} = \min(0.99, \max(0.05, 0.45 \cdot S_{final} + 0.35 \cdot I_{excursion} + 0.20 \cdot I_{sister}))$$
   - For an exact match with severe vibration ($5.8\text{ mm/s}$), $P_{recurrence} \ge 0.80$, categorizing the risk as **CRITICAL**.
   - The narrative generated: `"High risk of repeat ceramic seal fracture under sustained vibration > 5.0 mm/s."` matches E2E test assertions verbatim.

5. **Schema Dual-Compatibility (From Observation 1.4, 1.6, 1.7, 1.9)**:
   `rca_schemas.py` defines `preventative_recommendations`, while `conftest.py` test cases access `historical_lessons`. By populating both attributes on the match object, the implementation will satisfy both API schema validation and test-suite attribute access without breakage.

---

## 3. Caveats

1. **Read-Only Investigation Bound**: In strict compliance with explorer role constraints, zero code modifications have been made to project source files (`backend/services/rca_engine.py` or `backend/tests/test_rca_engine.py`). All deliverables reside within `.agents/teamwork/explorer_m2_historical_matching/`.
2. **Catalog Scope**: The primary historical corpus in the repository is `Near_Miss_Report_2023.txt` (Pump-A12). The blueprint establishes `HISTORICAL_INCIDENTS_CATALOG` which readily allows adding sister historical records (such as high-pressure steam turbine and boiler scenarios) without algorithmic modification.
3. **Telemetry Key Conventions**: The blueprint specifically checks for `vibration_mm_s` and `vibration`. Additional industrial telemetry parameters (`temperature_c`, `pressure_bar`, `rpm`) are preserved in `parameters` and can be evaluated similarly.

---

## 4. Conclusion

The architectural design, mathematical algorithms, data structures, and unit test suites for **Feature F7 (Historical Near-Miss Similarity Matching)** and **Recurrence Risk Assessment** are fully formulated and detailed in `analysis.md`.

Key blueprint specifications:
1. Class `HistoricalMatcher` and function `match_historical_records(asset_tag, symptoms, near_miss_text, telemetry_features)` in `backend/services/rca_engine.py`.
2. Multi-factor scoring engine guaranteeing:
   - `Pump-A12` full match score $\ge 0.80$.
   - Sister assets (`Pump-A11`, `Pump-A13`) horizontal read-across score $\ge 0.70$.
   - Unrelated equipment (`Conveyor-C99`) score $< 0.30 \rightarrow 0$ matches.
   - Proportional symptom scoring ($1/1 > 1/4$).
   - Case-insensitivity across uppercase and lowercase.
   - Guard against empty symptoms or empty document returning `[]`.
3. Recurrence risk assessment calculating $P_{recurrence}$ and outputting `"High risk of repeat ceramic seal fracture under sustained vibration > 5.0 mm/s."`.
4. Dual-attribute compatibility supporting both `preventative_recommendations` and `historical_lessons`.
5. 12 comprehensive unit test cases ready for implementation in `backend/tests/test_rca_engine.py`.

---

## 5. Verification Method

To independently verify this blueprint:

1. **Inspect Blueprint Deliverables**:
   - Technical analysis: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m2_historical_matching\analysis.md`
   - Formal handoff: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m2_historical_matching\handoff.md`

2. **Verify Existing Repository Tests Pass Baseline**:
   ```powershell
   # Working Directory: C:\000 MINE\My Codzz\Industrial Mind OS\backend
   & .\venv\Scripts\python.exe -m pytest tests/ -k "not e2e"
   & .\venv\Scripts\python.exe -m pytest tests/e2e_rca/
   ```
   Both commands must exit with code 0 (255 unit tests passed, 116 e2e tests passed).

3. **Verify Downstream Implementation (When Implemented by Worker)**:
   Once `backend/services/rca_engine.py` and `backend/tests/test_rca_engine.py` are written by the implementer, run:
   ```powershell
   & .\venv\Scripts\python.exe -m pytest tests/test_rca_engine.py -v
   & .\venv\Scripts\python.exe -m pytest tests/e2e_rca/test_tier1_feature_coverage.py -k "f7" -v
   & .\venv\Scripts\python.exe -m pytest tests/e2e_rca/test_tier2_boundary_corner.py -k "f7" -v
   & .\venv\Scripts\python.exe -m pytest tests/e2e_rca/test_tier3_cross_feature.py -k "cross_03" -v
   ```

4. **Invalidation Conditions**:
   - If `match_historical_records("Pump-A12", ["vibration"], near_miss_text)` yields similarity score $< 0.80$.
   - If `match_historical_records("Conveyor-C99", ["roller belt tear"], near_miss_text)` returns $> 0$ matches.
   - If case variation (`PUMP-A12` vs `pump-a12`) causes score divergence.
   - If `historical_lessons` attribute raises an `AttributeError`.
